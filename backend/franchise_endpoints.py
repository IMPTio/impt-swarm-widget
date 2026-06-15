"""Franchise lead-capture + Calendly webhook endpoints.

Mounted into the existing swarm widget FastAPI on :2027.
DB: swarm_widget.db (existing). New table: franchise_leads.
"""
import os, json, sqlite3, time, datetime, hmac, hashlib
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

router = APIRouter()

DB_PATH = os.environ.get('SWARM_DB', '/srv/swarm/impt-swarm-oss-2026-05-05/backend/swarm_widget.db')

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute('''CREATE TABLE IF NOT EXISTS franchise_leads(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER NOT NULL,
        email TEXT NOT NULL,
        country TEXT,
        country_name TEXT,
        region TEXT,
        city TEXT,
        page_type TEXT,
        slug TEXT,
        source_url TEXT,
        ip TEXT,
        ua TEXT,
        booked INTEGER DEFAULT 0,
        booked_ts INTEGER,
        calendly_event_uri TEXT,
        scheduled_time TEXT
    )''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_fl_email ON franchise_leads(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_fl_country ON franchise_leads(country)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_fl_booked ON franchise_leads(booked)')
    return c

class LeadIn(BaseModel):
    email: EmailStr
    country: str = ''
    country_name: str = ''
    page_type: str = ''
    slug: str = ''
    source_url: str = ''

@router.post('/api/franchise-lead')
async def franchise_lead(payload: LeadIn, request: Request):
    ip = request.headers.get('cf-connecting-ip') or request.headers.get('x-forwarded-for') or (request.client.host if request.client else '')
    ua = request.headers.get('user-agent', '')[:500]
    c = _conn()
    cur = c.cursor()
    cur.execute('''INSERT INTO franchise_leads(ts,email,country,country_name,page_type,slug,source_url,ip,ua) VALUES(?,?,?,?,?,?,?,?,?)''',
                (int(time.time()), payload.email.lower(), payload.country.upper(), payload.country_name, payload.page_type, payload.slug, payload.source_url, ip, ua))
    lead_id = cur.lastrowid
    c.commit()
    c.close()
    # Pre-emptive lead-captured email (FYI to mike@) — non-blocking, swallow errors
    try:
        _send_lead_captured(payload, lead_id, ip)
    except Exception:
        pass
    return {'ok': True, 'lead_id': lead_id}

@router.post('/api/franchise-booked')
async def franchise_booked(request: Request):
    """Calendly webhook receiver. Validates signature header per Calendly v2 docs."""
    raw = await request.body()
    sig = request.headers.get('calendly-webhook-signature', '')
    secret = os.environ.get('CALENDLY_WEBHOOK_SIGNING_KEY', '')
    if secret and not _verify_calendly_sig(raw, sig, secret):
        raise HTTPException(status_code=401, detail='bad signature')
    try:
        evt = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail='bad json')
    if evt.get('event') != 'invitee.created':
        return JSONResponse({'ok': True, 'skip': evt.get('event')})
    payload = evt.get('payload') or {}
    name = payload.get('name', '')
    email = (payload.get('email') or '').lower()
    event_uri = payload.get('event', '')
    scheduled_time = payload.get('scheduled_event', {}).get('start_time') or ''
    # Reverse-lookup most recent matching lead by email
    c = _conn()
    cur = c.cursor()
    cur.execute('SELECT id, country, country_name, page_type, slug, source_url FROM franchise_leads WHERE email=? ORDER BY id DESC LIMIT 1', (email,))
    row = cur.fetchone()
    if row:
        lead_id, country, country_name, page_type, slug, source_url = row
        cur.execute('UPDATE franchise_leads SET booked=1, booked_ts=?, calendly_event_uri=?, scheduled_time=? WHERE id=?',
                    (int(time.time()), event_uri, scheduled_time, lead_id))
        c.commit()
    else:
        country = country_name = page_type = slug = source_url = ''
        lead_id = None
    c.close()
    try:
        _send_urgent(name, email, country, country_name, page_type, slug, source_url, scheduled_time, event_uri, lead_id)
    except Exception as e:
        return {'ok': False, 'email_err': str(e)}
    return {'ok': True}

def _verify_calendly_sig(raw_body: bytes, sig_header: str, signing_key: str) -> bool:
    # Calendly format: 't=<ts>,v1=<hmac>'
    if not sig_header:
        return False
    parts = dict(p.split('=',1) for p in sig_header.split(',') if '=' in p)
    ts = parts.get('t', '')
    v1 = parts.get('v1', '')
    if not ts or not v1:
        return False
    msg = ts.encode() + b'.' + raw_body
    mac = hmac.new(signing_key.encode(), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, v1)

def _send_urgent(name, email, country, country_name, page_type, slug, source_url, scheduled_time, event_uri, lead_id):
    """Send urgent franchise-booked email. Tries SendGrid → Gmail SA send-as (same pattern as swarm widget verify) → log fallback.
       2026-05-12: SendGrid keys in vercel-env-backup found dead; Gmail SA via partners@impt.io is primary path."""
    country_disp = country_name or country or 'unknown territory'
    subject = f"URGENT — new franchise lead: {country_disp} — {name or email}"
    body_text = f"""URGENT — new IMPT franchise lead booked a 30-min call.

Name:           {name}
Email:          {email}
Territory:      {country_disp} ({country})
Page type:      {page_type}
Slug:           {slug}
Scheduled:      {scheduled_time}
Source URL:     {source_url}
Calendly event: {event_uri}
Lead ID:        {lead_id}

Action: review, prep, attend the call. Lead is booked into mike@impt.io Calendly.
"""
    recipients = ['mike@impt.io', 'cto-office@impt.io']  # LOCKED mike+cto-office ONLY (Mike 2026-06-12)
    sg_err = None
    SG_KEY = os.environ.get('SENDGRID_API_KEY', '')
    if SG_KEY:
        try:
            import requests
            data = {
                'personalizations': [{'to': [{'email': e} for e in recipients]}],
                'from': {'email': 'partners@impt.io', 'name': 'IMPT Franchise'},
                'subject': subject,
                'content': [{'type': 'text/plain', 'value': body_text}],
            }
            r = requests.post('https://api.sendgrid.com/v3/mail/send',
                              headers={'Authorization': f'Bearer {SG_KEY}', 'Content-Type': 'application/json'},
                              json=data, timeout=10)
            r.raise_for_status()
            return
        except Exception as e:
            sg_err = str(e)
    # Fallback: Gmail send-as via service account + Workspace DWD (matches swarm widget verify-email path)
    gmail_err = None
    try:
        import base64
        from email.mime.text import MIMEText
        from email.utils import formataddr
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        GMAIL_CREDS = os.environ.get('SWARM_WIDGET_GMAIL_CREDS', '/home/mike/impt-management/credentials.json')
        GMAIL_SENDER = 'partners@impt.io'
        creds = service_account.Credentials.from_service_account_file(
            GMAIL_CREDS, scopes=['https://www.googleapis.com/auth/gmail.send']
        ).with_subject(GMAIL_SENDER)
        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        msg = MIMEText(body_text)
        msg['to'] = ', '.join(recipients)
        msg['from'] = formataddr(('IMPT Franchise', GMAIL_SENDER))
        msg['subject'] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return
    except Exception as e:
        gmail_err = str(e)
    # Final fallback: write to log
    try:
        with open('/var/log/franchise-leads.log', 'a') as f:
            f.write(f"{datetime.datetime.utcnow().isoformat()}Z BOOKED name={name} email={email} country={country_name}({country}) time={scheduled_time} src={source_url} sg_err={sg_err} gmail_err={gmail_err}\n")
    except Exception:
        pass

def _send_lead_captured(payload: LeadIn, lead_id: int, ip: str):
    """FYI email to cto-office@ when email captured (before Calendly book)."""
    # Only send to cto-office@ to avoid spamming Mike pre-book — he'll get URGENT only on book
    import requests
    SG_KEY = os.environ.get('SENDGRID_API_KEY', '')
    if not SG_KEY:
        return
    subject = f"[fyi] franchise email captured: {payload.country_name or payload.country} — {payload.email}"
    body = f"Email: {payload.email}\nCountry: {payload.country_name} ({payload.country})\nPage: {payload.page_type} {payload.slug}\nSource: {payload.source_url}\nLead ID: {lead_id}\nIP: {ip}\n\nThey have NOT booked the call yet. URGENT email will fire if they complete Calendly."
    data = {
        'personalizations': [{'to': [{'email': 'cto-office@impt.io'}]}],
        'from': {'email': 'partners@impt.io', 'name': 'IMPT Franchise'},
        'subject': subject,
        'content': [{'type': 'text/plain', 'value': body}],
    }
    requests.post('https://api.sendgrid.com/v3/mail/send', headers={'Authorization': f'Bearer {SG_KEY}', 'Content-Type': 'application/json'}, json=data, timeout=10)
