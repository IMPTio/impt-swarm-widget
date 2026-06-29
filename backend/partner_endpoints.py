"""IMPT Regional/Country Partner — instant onboarding + e-signature endpoints.
Mounted into swarm_widget_api (port 2027). Routes:
  POST /api/partner/apply     -> store application + full acceptance/SIGNATURE audit
  POST /api/partner/activate  -> mark paid/active, notify mike+cto-office
DB: same swarm_widget.db, table partner_applications. Web2 (no token).
2026-06-28: added e-signature capture (signer type, typed/drawn signature, signed-at, doc version).
"""
import os, json, time, sqlite3, base64, hashlib
from typing import Dict, Any
from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr

router = APIRouter()
DB_PATH = os.environ.get('SWARM_DB', '/srv/swarm/impt-swarm-oss-2026-05-05/backend/swarm_widget.db')
SIG_DIR = os.environ.get('PARTNER_SIG_DIR', '/srv/swarm/impt-swarm-oss-2026-05-05/backend/partner_signatures')

_BASE_COLS = [
    ("signer_type", "TEXT"), ("signature_name", "TEXT"), ("signed_at", "TEXT"),
    ("doc_version", "TEXT"), ("signature_sha256", "TEXT"), ("signature_path", "TEXT"),
]


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute('''CREATE TABLE IF NOT EXISTS partner_applications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER NOT NULL,
        name TEXT, email TEXT NOT NULL, whatsapp TEXT,
        country TEXT, plan TEXT, fee TEXT, commission TEXT,
        accepted_version TEXT, accepted_at TEXT, acknowledgements TEXT,
        ip TEXT, ua TEXT,
        activated INTEGER DEFAULT 0, activated_ts INTEGER, payment_ref TEXT
    )''')
    # idempotent migration for the e-signature columns
    have = {r[1] for r in c.execute("PRAGMA table_info(partner_applications)").fetchall()}
    for col, typ in _BASE_COLS:
        if col not in have:
            try:
                c.execute(f"ALTER TABLE partner_applications ADD COLUMN {col} {typ}")
            except Exception:
                pass
    c.execute('CREATE INDEX IF NOT EXISTS idx_pa_email ON partner_applications(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_pa_country ON partner_applications(country)')
    c.commit()
    return c


class ApplyIn(BaseModel):
    name: str = ''
    email: EmailStr
    whatsapp: str = ''
    country: str = ''
    plan: str = ''
    fee: str = ''
    commission: str = ''
    acceptedVersion: str = ''
    acceptedAt: str = ''
    acknowledgements: Dict[str, Any] = {}
    # e-signature / consent
    signerType: str = ''        # 'individual' (consumer) | 'business'
    signatureName: str = ''     # typed full legal name
    signatureImage: str = ''    # data URL of the drawn signature (stored to file, not DB)
    signedAt: str = ''
    docVersion: str = ''
    hp: str = ''


class ActivateIn(BaseModel):
    email: EmailStr
    country: str = ''
    plan: str = ''
    paymentRef: str = ''


def _ip(request: Request) -> str:
    return (request.headers.get('cf-connecting-ip')
            or request.headers.get('x-forwarded-for')
            or (request.client.host if request.client else ''))


def _save_signature(app_id: int, data_url: str):
    """Persist the drawn signature image to a file; return (sha256, path) for the audit record."""
    if not data_url:
        return '', ''
    try:
        os.makedirs(SIG_DIR, exist_ok=True)
        raw = data_url
        if ',' in data_url and data_url.strip().lower().startswith('data:'):
            raw = data_url.split(',', 1)[1]
        try:
            blob = base64.b64decode(raw, validate=False)
        except Exception:
            blob = data_url.encode('utf-8', 'ignore')
        sha = hashlib.sha256(blob).hexdigest()
        path = os.path.join(SIG_DIR, f"partner_{app_id}.sig")
        with open(path, 'wb') as f:
            f.write(blob)
        return sha, path
    except Exception:
        return '', ''


@router.post('/api/partner/apply')
async def partner_apply(payload: ApplyIn, request: Request):
    if payload.hp:  # honeypot -> silently accept, store nothing
        return {'ok': True, 'id': None}
    ip = _ip(request)
    ua = request.headers.get('user-agent', '')[:500]
    c = _conn(); cur = c.cursor()
    cur.execute('''INSERT INTO partner_applications
        (ts,name,email,whatsapp,country,plan,fee,commission,accepted_version,accepted_at,acknowledgements,ip,ua,
         signer_type,signature_name,signed_at,doc_version)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (int(time.time()), payload.name, payload.email.lower(), payload.whatsapp, payload.country,
         payload.plan, str(payload.fee), str(payload.commission),
         payload.acceptedVersion or payload.docVersion, payload.acceptedAt or payload.signedAt,
         json.dumps(payload.acknowledgements), ip, ua,
         payload.signerType, payload.signatureName, payload.signedAt, payload.docVersion))
    app_id = cur.lastrowid; c.commit()
    sha, path = _save_signature(app_id, payload.signatureImage)
    if sha:
        cur.execute('UPDATE partner_applications SET signature_sha256=?, signature_path=? WHERE id=?', (sha, path, app_id))
        c.commit()
    c.close()
    try:
        _notify(f"NEW partner application (SIGNED): {payload.country or '?'} — {payload.name or payload.email}",
                _fmt(payload, app_id, ip, sha))
    except Exception:
        pass
    return {'ok': True, 'id': app_id, 'signed': bool(sha or payload.signatureName)}


@router.post('/api/partner/activate')
async def partner_activate(payload: ActivateIn, request: Request):
    c = _conn(); cur = c.cursor()
    cur.execute('SELECT id FROM partner_applications WHERE email=? ORDER BY id DESC LIMIT 1', (payload.email.lower(),))
    row = cur.fetchone()
    if row:
        cur.execute('UPDATE partner_applications SET activated=1, activated_ts=?, payment_ref=? WHERE id=?',
                    (int(time.time()), payload.paymentRef, row[0]))
        c.commit()
    app_id = row[0] if row else None
    c.close()
    try:
        _notify(f"✅ partner ACTIVATED (paid): {payload.country or '?'} — {payload.email}",
                f"Partner activated (payment received).\nEmail: {payload.email}\nCountry/Region: {payload.country}\n"
                f"Plan: {payload.plan}\nPayment ref: {payload.paymentRef}\nApplication id: {app_id}\n")
    except Exception:
        pass
    return {'ok': True, 'id': app_id, 'activated': bool(row)}


def _fmt(p: 'ApplyIn', app_id, ip, sha) -> str:
    return (f"New IMPT Regional Partner application (Web2 — licence, not franchise/investment).\n\n"
            f"Name: {p.name}\nEmail: {p.email}\nWhatsApp: {p.whatsapp}\n"
            f"Country/Region: {p.country}\nPlan: {p.plan}\nFee: {p.fee}\nCommission: {p.commission}\n"
            f"Signer type: {p.signerType or '?'}\nSigned by: {p.signatureName or '(no typed name)'} at {p.signedAt or '?'}\n"
            f"Signature on file: {'yes (sha256 ' + sha[:16] + '…)' if sha else 'no image'}\n"
            f"Doc version: {p.docVersion or p.acceptedVersion}\n"
            f"Acknowledgements: {json.dumps(p.acknowledgements)}\nIP: {ip}\nApplication id: {app_id}\n\n"
            f"They have NOT paid yet — activation fires on payment success.\n")


def _notify(subject: str, body_text: str):
    """Best-effort notify mike+cto-office via Gmail service-account send-as partners@."""
    recipients = ['mike@impt.io', 'cto-office@impt.io']
    from email.mime.text import MIMEText
    from email.utils import formataddr
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds_path = os.environ.get('SWARM_WIDGET_GMAIL_CREDS', '/home/mike/impt-management/credentials.json')
    creds = service_account.Credentials.from_service_account_file(
        creds_path, scopes=['https://www.googleapis.com/auth/gmail.send']).with_subject('partners@impt.io')
    svc = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    msg = MIMEText(body_text)
    msg['to'] = ', '.join(recipients)
    msg['from'] = formataddr(('IMPT Partners', 'partners@impt.io'))
    msg['subject'] = subject
    svc.users().messages().send(userId='me', body={'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode()}).execute()
