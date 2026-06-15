#!/usr/bin/env python3
"""
IMPT Swarm Widget — attribution + partner signup backend.

FastAPI service. Runs on :2027 behind nginx at swarm.impt.io/api/widget/*.
SQLite for tonight; migrate to Postgres on day 30.

Security wall (2026-05-05):
  * nginx-side per-IP rate limits + bot-UA filter on /r
  * email verification before key activates (pending_email → active)
  * disposable-email domain block + honeypot field on signup
  * HMAC-signed booking webhook (X-IMPT-Signature: sha256=hex)
  * audit log on every state-change
  * /r refuses to attribute for non-active keys (graceful 302, no cookie/utm)

Endpoints
---------
  GET  /api/widget/health
  POST /api/widget/partners/signup     { email, name, payout_method, payout_target, hp? }
  GET  /api/widget/verify              ?token=  → flips key to active
  GET  /api/widget/r                   ?key=&dest=  302 → lander + cookie (only if active)
  GET  /api/widget/track               ?key=&evt=&dest=&ref=  1x1 GIF + log
  POST /api/widget/booking             X-IMPT-Signature header  → 5% accrual
  GET  /api/widget/partners/me         Bearer auth → balance + history
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

DB_PATH = os.environ.get("SWARM_WIDGET_DB", "/home/mike/impt-swarm-oss-2026-05-05/backend/swarm_widget.db")
LANDER = "https://app.impt.io/find-hotel-input"
# Mike directive 2026-06-12: each widget routes to its vertical's page, not regular search.
# Only used when the guest did NOT type a destination search (dest absent) and no `to` override.
# 2026-06-15: the 7 homepage personas now land on their own LOCAL Lovable-designed
# "IMPT Stays" page (self-hosted static, no Lovable runtime) at swarm.impt.io/stays/<v>/.
# Each is an exciting, per-vertical marketing+capture page (hero/destinations/form) that
# binds bookings to the partner key. scuba/lgbtq/clubs/brands keep /worlds until built.
STAYS_BASE = "https://swarm.impt.io/stays"
STAYS_VERTICALS = {"surf", "walks", "mtb", "ski", "pets", "golf", "yoga"}
VERTICAL_LANDERS = {
    "mtb":    "https://swarm.impt.io/stays/mtb/",
    "surf":   "https://swarm.impt.io/stays/surf/",
    "walks":  "https://swarm.impt.io/stays/walks/",
    "ski":    "https://swarm.impt.io/stays/ski/",
    "pets":   "https://swarm.impt.io/stays/pets/",
    "golf":   "https://swarm.impt.io/stays/golf/",
    "yoga":   "https://swarm.impt.io/stays/yoga/",
    "scuba":  "https://impt.io/worlds",
    "lgbtq":  "https://impt.io/worlds",
    "clubs":  "https://impt.io/worlds",
    "brands": "https://impt.io/worlds",
}
COOKIE_DAYS = 90
COMMISSION_PCT = 0.05
WEBHOOK_SECRET = os.environ.get("SWARM_WIDGET_WEBHOOK_SECRET", "set-me-in-env")
PUBLIC_BASE = os.environ.get("SWARM_WIDGET_PUBLIC_BASE", "https://swarm.impt.io")
CAL_PARTNER = "https://calendly.com/cto-office-impt/15-minute-meeting-impt"  # widget/partner 15-min call (Mike, 2026-06-10)
GMAIL_CREDS = os.environ.get("SWARM_WIDGET_GMAIL_CREDS", "/home/mike/impt-management/credentials.json")
GMAIL_SENDER = os.environ.get("SWARM_WIDGET_GMAIL_SENDER", "cto-office@impt.io")
GMAIL_FROM_NAME = os.environ.get("SWARM_WIDGET_GMAIL_FROM_NAME", "IMPT Swarm")
GMAIL_REPLY_TO = os.environ.get("SWARM_WIDGET_REPLY_TO", "mike@impt.io")
# Mike wants a copy of EVERY localised welcome that goes to a widget holder, so he can audit quality.
# BCC (not visible CC) — the customer never sees this address. Set "" to disable. (Mike 2026-06-15)
WELCOME_AUDIT_BCC = os.environ.get("WIDGET_WELCOME_AUDIT_BCC", "mike@impt.io")

# Meta Conversions API (server-side). Fires partner-signup as CompleteRegistration so Meta can
# attribute + optimise the Widget campaign. Token/pixel in service .env. If META_CAPI_TEST_CODE is
# set, events route to Events-Manager Test Events only (used to verify before go-live).
META_CAPI_PIXEL = os.environ.get("META_CAPI_PIXEL", "1914219372810028")
META_CAPI_TOKEN = os.environ.get("META_CAPI_TOKEN", "")
META_CAPI_API = os.environ.get("META_CAPI_API", "v21.0")
META_CAPI_TEST_CODE = os.environ.get("META_CAPI_TEST_CODE", "")

GIF_1x1 = bytes.fromhex("47494638396101000100800000ffffff00000021f90401000001002c00000000010001000002024401003b")

# Disposable / throwaway email-domain blocklist. Not exhaustive; we add as we see.
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "guerrillamail.net", "10minutemail.com",
    "10minutemail.net", "tempmail.com", "temp-mail.org", "throwawaymail.com",
    "yopmail.com", "trashmail.com", "trashmail.net", "maildrop.cc", "sharklasers.com",
    "getairmail.com", "mailnesia.com", "mintemail.com", "fakeinbox.com",
    "spamgourmet.com", "dispostable.com", "fakemailgenerator.com", "tempinbox.com",
    "emailondeck.com", "mohmal.com", "mytemp.email", "mvrht.net", "tempr.email",
    "burnermail.io", "byom.de", "spambox.us", "moakt.com",
}

app = FastAPI(title="IMPT Swarm Widget API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*", "X-IMPT-Signature"],
    max_age=86400,
)


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with db() as c:
        # Migrate existing schema additively before creating fresh.
        existing = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='partners'").fetchone()
        if existing:
            cols = {r[1] for r in c.execute("PRAGMA table_info(partners)").fetchall()}
            for col, ddl in [
                ("verify_token", "ALTER TABLE partners ADD COLUMN verify_token TEXT"),
                ("verified_at", "ALTER TABLE partners ADD COLUMN verified_at INTEGER"),
                ("signup_ip_hash", "ALTER TABLE partners ADD COLUMN signup_ip_hash TEXT"),
            ]:
                if col not in cols:
                    c.execute(ddl)
        c.executescript("""
        CREATE TABLE IF NOT EXISTS partners (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          key TEXT UNIQUE NOT NULL,
          email TEXT NOT NULL,
          name TEXT,
          payout_method TEXT NOT NULL,
          payout_target TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending_email',
          api_token TEXT UNIQUE NOT NULL,
          verify_token TEXT,
          verified_at INTEGER,
          signup_ip_hash TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_partners_email ON partners(email);
        CREATE INDEX IF NOT EXISTS idx_partners_verify ON partners(verify_token);
        CREATE TABLE IF NOT EXISTS partner_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          key TEXT NOT NULL,
          evt TEXT NOT NULL,
          dest TEXT,
          ref TEXT,
          ip_hash TEXT,
          ua_hash TEXT,
          ts INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_key ON partner_events(key);
        CREATE INDEX IF NOT EXISTS idx_events_ts ON partner_events(ts);
        CREATE TABLE IF NOT EXISTS partner_bookings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          partner_key TEXT NOT NULL,
          booking_id TEXT UNIQUE NOT NULL,
          base_value_cents INTEGER NOT NULL,
          currency TEXT NOT NULL,
          accrual_eur_cents INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          booked_at INTEGER NOT NULL,
          check_in_at INTEGER,
          updated_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_bookings_key ON partner_bookings(partner_key);
        CREATE TABLE IF NOT EXISTS partner_payouts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          partner_key TEXT NOT NULL,
          amount_eur_cents INTEGER NOT NULL,
          period_start INTEGER NOT NULL,
          period_end INTEGER NOT NULL,
          paid_at INTEGER,
          method TEXT,
          ref TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ts INTEGER NOT NULL,
          actor TEXT NOT NULL,
          action TEXT NOT NULL,
          subject TEXT,
          detail TEXT,
          ip_hash TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_audit_subject ON audit_log(subject);
        """)


def hash_ip(ip: str) -> str:
    return hashlib.sha256((ip + "|impt-swarm-2026").encode()).hexdigest()[:16]


def hash_ua(ua: str) -> str:
    return hashlib.sha256((ua or "").encode()).hexdigest()[:16]


def meta_capi_event(event_name: str, email: Optional[str], event_id: str, source_url: str,
                    ip_hash: Optional[str] = None, client_ip: Optional[str] = None,
                    client_ua: Optional[str] = None, custom_data: Optional[dict] = None) -> bool:
    """Fire a Meta Conversions API event. NEVER raises — failures are logged, never block signup.

    Returns True if Meta reports events_received >= 1. event_id is shared with any browser pixel
    event so Meta de-dupes. Email is SHA256-hashed (lowercased+trimmed) per Meta spec; client IP/UA
    are sent raw to lift match quality.
    """
    if not META_CAPI_TOKEN:
        return False
    try:
        import urllib.request
        user_data = {}
        if email:
            user_data["em"] = [hashlib.sha256(email.strip().lower().encode()).hexdigest()]
        if client_ip:
            user_data["client_ip_address"] = client_ip
        if client_ua:
            user_data["client_user_agent"] = client_ua
        evt = {
            "event_name": event_name,
            "event_time": int(time.time()),
            "action_source": "website",
            "event_source_url": source_url,
            "event_id": event_id,
            "user_data": user_data,
        }
        if custom_data:
            evt["custom_data"] = custom_data
        payload = {"data": [evt], "access_token": META_CAPI_TOKEN}
        if META_CAPI_TEST_CODE:
            payload["test_event_code"] = META_CAPI_TEST_CODE
        url = f"https://graph.facebook.com/{META_CAPI_API}/{META_CAPI_PIXEL}/events"
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=4) as r:
            resp = json.loads(r.read().decode())
        ok = int(resp.get("events_received", 0)) >= 1
        audit("capi.sent" if ok else "capi.fail", subject=event_id,
              detail={"event": event_name, "resp": resp}, ip_hash=ip_hash)
        return ok
    except Exception as e:  # noqa: BLE001 — must never break the signup path
        try:
            audit("capi.error", subject=event_id,
                  detail={"event": event_name, "err": str(e)[:300]}, ip_hash=ip_hash)
        except Exception:
            pass
        return False


def to_eur_cents(amount: float, currency: str) -> int:
    rates = {"EUR": 1.0, "USD": 0.92, "GBP": 1.18, "JPY": 0.0061, "AUD": 0.61, "CAD": 0.68,
             "CHF": 1.05, "SGD": 0.69, "AED": 0.25, "THB": 0.027}
    return int(amount * rates.get(currency.upper(), 1.0) * 100)


def audit(action: str, subject: Optional[str], detail: Optional[dict], ip_hash: Optional[str] = None,
          actor: str = "system") -> None:
    with db() as c:
        c.execute(
            "INSERT INTO audit_log(ts,actor,action,subject,detail,ip_hash) VALUES (?,?,?,?,?,?)",
            (int(time.time()), actor, action, subject,
             json.dumps(detail) if detail else None, ip_hash)
        )


def is_valid_email(email: str) -> bool:
    if not email or "@" not in email or len(email) > 200:
        return False
    domain = email.rsplit("@", 1)[-1].strip().lower()
    if domain in DISPOSABLE_DOMAINS:
        return False
    if not re.match(r"^[a-z0-9.\-]+\.[a-z]{2,}$", domain):
        return False
    return True


# ── partner emails (premium HTML, 2026-06-09) ───────────────────────
# verify  = first touch on signup (one job: get the activate click)
# welcome = sent on activation (install-assurance: white-glove + paste + no-site path)
EMAIL_CREAM="#F7F4EC"; EMAIL_INK="#13231B"; EMAIL_GREEN="#1E8E5A"; EMAIL_DEEP="#0E2C25"
EMAIL_LIME="#C8FF7E"; EMAIL_MUTE="#7a857f"; EMAIL_SOFT="#5a655e"; EMAIL_CARD="#FBF9F3"; EMAIL_CARDB="#ECE6D7"
EMAIL_PARTNERS="430+"

def _em_shell(title, preheader, body_html):
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>{title}</title>
<style>@media (max-width:600px){{.container{{width:100%!important}}.pad{{padding-left:22px!important;padding-right:22px!important}}.btn a{{display:block!important;text-align:center!important}}.h1{{font-size:26px!important}}}}</style>
</head><body style="margin:0;padding:0;background:{EMAIL_CREAM};">
<span style="display:none!important;visibility:hidden;opacity:0;height:0;width:0;overflow:hidden;mso-hide:all">{preheader}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{EMAIL_CREAM};">
<tr><td align="center" style="padding:30px 12px;">
  <table role="presentation" class="container" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:600px;">
    <tr><td class="pad" style="padding:0 34px 14px;">
      <span style="font-family:Inter,Arial,sans-serif;font-weight:800;font-size:21px;color:{EMAIL_GREEN};letter-spacing:-.01em;">impt</span>
      <span style="font-family:Inter,Arial,sans-serif;font-size:11px;color:{EMAIL_MUTE};letter-spacing:.16em;text-transform:uppercase;float:right;padding-top:8px">Swarm Widget</span>
    </td></tr>
    <tr><td style="background:#FFFFFF;border-radius:18px;box-shadow:0 18px 48px -22px rgba(8,42,58,.30);overflow:hidden;">{body_html}</td></tr>
    <tr><td class="pad" style="padding:18px 34px 6px;font-family:Inter,Arial,sans-serif;font-size:12px;line-height:1.6;color:{EMAIL_MUTE};">
      IMPT — hotels at normal prices that pay you back &amp; offset carbon.<br>
      {EMAIL_PARTNERS} partners already onboard · open-source (MIT) · just reply, a real person reads every email.
    </td></tr>
  </table>
</td></tr></table></body></html>"""

def _em_btn(href, label):
    return (f'<table role="presentation" class="btn" cellpadding="0" cellspacing="0" style="margin:6px 0;"><tr>'
            f'<td align="center" style="background:{EMAIL_GREEN};border-radius:12px;">'
            f'<a href="{href}" style="display:inline-block;padding:15px 30px;font-family:Inter,Arial,sans-serif;'
            f'font-size:16px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:12px;">{label}</a>'
            f'</td></tr></table>')

def _em_btn2(href, label):
    return (f'<a href="{href}" style="display:inline-block;padding:12px 22px;font-family:Inter,Arial,sans-serif;'
            f'font-size:15px;font-weight:700;color:{EMAIL_GREEN};text-decoration:none;border:1.5px solid {EMAIL_GREEN};'
            f'border-radius:12px;margin:6px 10px 6px 0;">{label}</a>')

def _em_brow(emoji, strong, rest):
    return (f'<tr><td style="padding:7px 0;font-family:Inter,Arial,sans-serif;font-size:15px;color:{EMAIL_INK};line-height:1.5;vertical-align:top;">'
            f'<span style="font-size:18px;">{emoji}</span>&nbsp;&nbsp;<b>{strong}</b> {rest}</td></tr>')

def _em_first(name):
    return (name or "").split()[0] if name else "there"

# Vertical personalisation (2026-06-12): the widget a partner downloaded shapes every
# email + page they see. Keys match leads.purpose / partners.vertical.
VERTICALS = {
    "mtb":   {"emoji": "🚵", "label": "MTB Widget",   "line": "the hotel-booking widget built for mountain bikers — 117 bike-resort guides, hotels by the trails",
              "showcase": "https://impt.io/mountain-bike-trails/", "showcase_label": "See it live on IMPT Mountain Bike Trails"},
    "surf":  {"emoji": "🏄", "label": "Surf Widget",  "line": "the hotel-booking widget built for surfers — stays right by the breaks",
              "showcase": "https://impt.io/surf-hotels/", "showcase_label": "See it live on IMPT Surf Hotels"},
    "golf":  {"emoji": "⛳", "label": "Golf Widget",  "line": "the hotel-booking widget built for golfers — stays right by the fairway, first tee in minutes",
              "showcase": "https://impt.io/golf-hotels/", "showcase_label": "See it live on IMPT Golf Hotels"},
    "lgbtq": {"emoji": "🏳️‍🌈", "label": "Pride Widget", "line": "the hotel-booking widget built for your community — welcoming stays in 195 countries",
              "showcase": "https://impt.io/worlds", "showcase_label": "See the worlds it powers"},
    "walks": {"emoji": "🥾", "label": "Walks Widget", "line": "the hotel-booking widget built for walkers — hotels along the world's great trails",
              "showcase": "https://impt.io/walks", "showcase_label": "See it live on IMPT Walks"},
    "scuba": {"emoji": "🤿", "label": "Scuba Widget", "line": "the hotel-booking widget built for divers — stays by the world's best dive sites",
              "showcase": "https://impt.io/worlds", "showcase_label": "See the worlds it powers"},
}
def _vert(vertical):
    return VERTICALS.get((vertical or "").strip().lower())

def _em_verify(name, key, verify_token, vertical=None):
    n=_em_first(name); url=f"{PUBLIC_BASE}/api/widget/verify?token={verify_token}"
    v=_vert(vertical)
    wname = f"IMPT {v['label']}" if v else "IMPT Swarm Widget"
    wline = v["line"] if v else "the open hotel-booking widget that pays you <b style=\"color:"+EMAIL_INK+"\">5%</b> on every stay"
    benefits=("<table role='presentation' cellpadding='0' cellspacing='0' width='100%'>"
        + _em_brow("💸","5% on every booking","— always paid <b>gross</b>, monthly, no minimums once you pass €50.")
        + _em_brow("⏳","90-day cookie","— they click today, book within 90 days, you still earn.")
        + _em_brow("🌍","Every stay offsets 1 tonne of CO₂","— your audience travels and does good.")
        + "</table>")
    body=f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="height:6px;background:linear-gradient(90deg,{EMAIL_GREEN},{EMAIL_LIME});"></td></tr>
      <tr><td class="pad" style="padding:34px 34px 8px;font-family:Inter,Arial,sans-serif;">
        <div class="h1" style="font-family:Fraunces,Georgia,serif;font-size:30px;line-height:1.18;color:{EMAIL_INK};font-weight:600;margin:0 0 12px;">You're one click from earning, {n}.</div>
        <p style="font-size:16px;color:{EMAIL_SOFT};line-height:1.6;margin:0 0 20px;">Welcome to the <b style="color:{EMAIL_INK}">{wname}</b> — {wline}, paying you <b style="color:{EMAIL_INK}">5%</b> on every stay. Confirm your email to switch your partner key on:</p>
        {_em_btn(url,"Activate my widget →")}
        <p style="font-size:13px;color:{EMAIL_MUTE};margin:14px 0 24px;">Takes two seconds. The button does it all.</p>
        <div style="border-top:1px solid #eee;padding-top:18px;">{benefits}</div>
        <p style="font-size:15px;color:{EMAIL_SOFT};line-height:1.6;margin:20px 0 6px;">The moment you activate, going live takes one copy-paste — and if you'd rather not, <b style="color:{EMAIL_INK}">just reply and we'll install it for you, free</b> — or <a href="{CAL_PARTNER}" style="color:{EMAIL_GREEN};font-weight:700;">book a 15-min call</a> and we'll do it together.</p>
      </td></tr>
      <tr><td class="pad" style="padding:6px 34px 30px;font-family:Inter,Arial,sans-serif;">
        <p style="font-size:12px;color:{EMAIL_MUTE};line-height:1.6;margin:14px 0 0;border-top:1px solid #f0f0f0;padding-top:14px;">Button not working? Paste this into your browser:<br><a href="{url}" style="color:{EMAIL_GREEN};word-break:break-all;">{url}</a><br><br>Didn't sign up? Ignore this — the key <b>{key}</b> stays inactive and expires on its own.</p>
      </td></tr>
    </table>"""
    text=(f"You're one click from earning, {n}.\n\nWelcome to the {wname} — it pays you 5% on every stay.\n\n"
          f"Activate your partner key:\n{url}\n\n- 5% on every booking, always gross, paid monthly\n- 90-day cookie\n- every stay offsets 1 tonne of CO2\n\n"
          f"Once active, install is one copy-paste — or just reply and we'll install it for you, free.\nPrefer a call? Book 15 min: {CAL_PARTNER}\n\nDidn't sign up? Ignore this; key {key} stays inactive.\n\n— IMPT Swarm · swarm.impt.io/widget")
    subj = (f"One click to activate your {wname} {v['emoji']} — 5% on every booking" if v
            else "One click to activate your IMPT widget — 5% on every booking")
    return (subj,
            _em_shell(f"Activate your {wname}","Confirm your email and your widget starts earning you 5% on every hotel booking.",body), text)

def _em_welcome(name, key, api_token, vertical=None):
    n=_em_first(name)
    v=_vert(vertical)
    wname = f"IMPT {v['label']}" if v else "IMPT widget"
    guide=f"{PUBLIC_BASE}/widget-install?" + ((f"v={(vertical or '').strip().lower()}&" if v else "")) + f"k={key}"
    showcase_html=(f'<p style="font-size:14px;color:{EMAIL_SOFT};margin:10px 0 0;">See yours working in the wild: '
                   f'<a href="{v["showcase"]}" style="color:{EMAIL_GREEN};font-weight:700;">{v["showcase_label"]} &rarr;</a></p>') if v else ""
    dash=f"{PUBLIC_BASE}/dashboard?k={key}&t={api_token}"; page=f"{PUBLIC_BASE}/go?k={key}"; qr=f"{PUBLIC_BASE}/api/widget/qr/{key}.png"
    snippet=(f'&lt;script src="{PUBLIC_BASE}/widget.js" data-key="{key}" async&gt;&lt;/script&gt;\n&lt;div id="impt-swarm"&gt;&lt;/div&gt;')
    caption=(f"Planning a trip? Book hotels through my link — same prices you'd pay anywhere, and every stay offsets 1 tonne of CO₂ 🌍  {page}")
    glove=(f'<div style="background:#EAF3EC;border:1px solid #CFE6D6;border-radius:14px;padding:18px 20px;margin:18px 0;font-family:Inter,Arial,sans-serif;font-size:15px;color:{EMAIL_INK};line-height:1.55;">'
           f'<b>💬 Fastest way to go live — message us on WhatsApp.</b> We&rsquo;ll set up your widget with you in about 5 minutes (or do it for you): '
           f'<a href="https://wa.me/353874456007" style="color:{EMAIL_GREEN};font-weight:700;">chat on WhatsApp &rarr;</a><br><br>'
           f'Prefer email? Reply with your website address (and your WordPress/Shopify login if you have one) and we&rsquo;ll install it for you today, free. Or grab 15 minutes with us: <a href="{CAL_PARTNER}" style="color:{EMAIL_GREEN};font-weight:700;">book a quick call &rarr;</a></div>')
    codebox=(f'<div style="background:{EMAIL_DEEP};color:#EAF4EC;padding:14px 16px;border-radius:10px;font-family:Menlo,Consolas,monospace;font-size:13px;line-height:1.5;white-space:pre-wrap;word-break:break-all;margin:10px 0;">{snippet}</div>')
    body=f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="height:6px;background:linear-gradient(90deg,{EMAIL_GREEN},{EMAIL_LIME});"></td></tr>
      <tr><td class="pad" style="padding:34px 34px 6px;font-family:Inter,Arial,sans-serif;">
        <div class="h1" style="font-family:Fraunces,Georgia,serif;font-size:30px;line-height:1.18;color:{EMAIL_INK};font-weight:600;margin:0 0 12px;">Your {wname} is live, {n} {v['emoji'] if v else '🌍'}</div>
        <p style="font-size:16px;color:{EMAIL_SOFT};line-height:1.6;margin:0 0 18px;">Your partner key is active. Let's get it earning — pick the path that fits you, it takes about two minutes. (No website? Skip to Option B — you're set without building anything.)</p>
        {showcase_html}
        {glove}
        <p style="font-size:13px;color:{EMAIL_MUTE};text-transform:uppercase;letter-spacing:.12em;margin:26px 0 6px;">Option A — you have a website</p>
        <p style="font-size:15px;color:{EMAIL_INK};line-height:1.6;margin:0 0 4px;">Paste this once, anywhere before <span style="font-family:monospace">&lt;/body&gt;</span>. Your key is already in it:</p>
        {codebox}
        <p style="font-size:14px;color:{EMAIL_SOFT};line-height:1.6;margin:6px 0 4px;">• <b>WordPress:</b> add it with the free “WPCode / Insert Headers &amp; Footers” plugin → Footer.<br>• <b>Shopify:</b> Online Store → Themes → Edit code → <span style="font-family:monospace">theme.liquid</span>, before <span style="font-family:monospace">&lt;/body&gt;</span>.<br>• <b>Wix / Squarespace:</b> add a “Custom Code / Embed” block in the site footer.</p>
        <p style="font-size:14px;color:{EMAIL_SOFT};margin:8px 0 0;">{_em_btn2(guide,"Full step-by-step guide →")}</p>
        <p style="font-size:13px;color:{EMAIL_MUTE};text-transform:uppercase;letter-spacing:.12em;margin:30px 0 6px;">Option B — no website? You still earn</p>
        <p style="font-size:15px;color:{EMAIL_INK};line-height:1.6;margin:0 0 8px;">Your own hotel page is already live — share it anywhere (bio, WhatsApp, a group, a story):</p>
        <div style="background:{EMAIL_CARD};border:1px solid {EMAIL_CARDB};border-radius:12px;padding:13px 15px;margin:6px 0;"><div style="font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:{EMAIL_MUTE};margin-bottom:4px;">Your hotel page</div><a href="{page}" style="font-size:15px;color:{EMAIL_GREEN};font-weight:600;word-break:break-all;text-decoration:none;">{page}</a></div>
        <p style="margin:8px 0 2px;">{_em_btn2(page,"Open my page →")}{_em_btn2(qr,"Get my QR code →")}</p>
        <p style="font-size:14px;color:{EMAIL_INK};margin:14px 0 4px;">Ready-to-post caption — copy &amp; paste:</p>
        <div style="background:{EMAIL_CARD};border:1px solid {EMAIL_CARDB};border-radius:12px;padding:13px 15px;margin:4px 0;font-size:14px;color:{EMAIL_SOFT};line-height:1.5;">{caption}</div>
        <p style="font-size:13px;color:{EMAIL_MUTE};text-transform:uppercase;letter-spacing:.12em;margin:30px 0 6px;">Check it's working</p>
        <p style="font-size:15px;color:{EMAIL_SOFT};line-height:1.6;margin:0 0 10px;">Once it's on your page, your dashboard shows your clicks, bookings and balance — and you'll see the first booking land here.</p>
        {_em_btn(dash,"Open my dashboard →")}
        <div style="background:{EMAIL_CARD};border:1px solid {EMAIL_CARDB};border-radius:12px;padding:14px 16px;margin:22px 0 4px;"><div style="font-size:12px;color:{EMAIL_MUTE};margin-bottom:6px;">Keep these safe</div><div style="font-size:14px;color:{EMAIL_INK};line-height:1.7;">Partner key: <b>{key}</b><br>Dashboard token: <span style="font-family:monospace;word-break:break-all;">{api_token}</span></div></div>
        <p style="font-size:15px;color:{EMAIL_SOFT};line-height:1.6;margin:20px 0 2px;">Any question at all, just reply — I read every one myself.</p>
        <p style="font-size:15px;color:{EMAIL_INK};margin:2px 0 30px;">Laura<br><span style="color:{EMAIL_MUTE};font-size:14px;">IMPT Partnerships</span></p>
      </td></tr>
    </table>"""
    text=(f"You're live, {n}.\n\nYour partner key is active. Two ways to go live:\n\nWANT US TO DO IT? Reply with your website (and WordPress/Shopify login) and we'll install it free today.\nOr book a 15-min setup call: {CAL_PARTNER}\n\n"
          f"OPTION A — website: paste before </body>:\n<script src=\"{PUBLIC_BASE}/widget.js\" data-key=\"{key}\" async></script>\n<div id=\"impt-swarm\"></div>\n"
          f"WordPress: WPCode/Insert Headers & Footers → Footer. Shopify: theme.liquid. Wix/Squarespace: footer embed.\nGuide: {guide}\n\n"
          f"OPTION B — no website: share your page {page}  ·  QR {qr}\nCaption: {caption}\n\n"
          f"Dashboard (clicks + earnings): {dash}\nPartner key: {key}  ·  Dashboard token: {api_token}\n\nReply any time — a real person answers.\n— Laura, IMPT Partnerships")
    subj = (f"Your {wname} is live — let's get it earning {v['emoji']}" if v
            else "Your IMPT widget is live — let's get it earning 🌍")
    return (subj,
            _em_shell(f"Your {wname} is live","Your key's active. Go live in 2 minutes — or reply and we'll install it for you.",body), text)

def _em_send(to, subject, html, text, bcc="") -> bool:
    # deliverability gate — skip suppressed / bad-syntax / no-MX (Mike 2026-06-12).
    # Fail-open: a checker error must never block legitimate sends.
    try:
        import sys as _sys, sqlite3 as _sq
        if "/home/mike/ads-meta-launch" not in _sys.path:
            _sys.path.insert(0, "/home/mike/ads-meta-launch")
        import email_suppression as _supp
        _c = _sq.connect(_supp.DB)
        _ok, _why = _supp.check(_c, to)
        _c.close()
        if not _ok:
            print(f"[swarm-widget] email SUPPRESSED to={to}: {_why}", flush=True)
            return False
    except Exception as _e:
        print(f"[swarm-widget] suppression check error (allowing send) to={to}: {_e}", flush=True)
    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.utils import formataddr
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_file(
            GMAIL_CREDS, scopes=["https://www.googleapis.com/auth/gmail.send"]).with_subject(GMAIL_SENDER)
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        msg = MIMEMultipart("alternative")
        msg["to"] = to; msg["from"] = formataddr((GMAIL_FROM_NAME, GMAIL_SENDER))
        msg["reply-to"] = GMAIL_REPLY_TO; msg["subject"] = subject
        if bcc: msg["bcc"] = bcc   # audit copy (Gmail delivers to bcc, strips header — customer never sees it)
        msg.attach(MIMEText(text, "plain")); msg.attach(MIMEText(html, "html"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print(f"[swarm-widget] email sent: id={result.get('id')} to={to} subj={subject!r}", flush=True)
        return True
    except Exception as e:
        print(f"[swarm-widget] email send FAILED to={to}: {e}", flush=True)
        return False

def send_verify_email(email: str, name: Optional[str], partner_key: str, verify_token: str, vertical: Optional[str] = None) -> bool:
    subject, html, text = _em_verify(name, partner_key, verify_token, vertical=vertical)
    return _em_send(email, subject, html, text)

def send_welcome_email(email: str, name: Optional[str], partner_key: str, api_token: str, vertical: Optional[str] = None) -> bool:
    # New designed welcome (hosted hero + live HTML). Falls back to legacy on any error — zero regression.
    try:
        import os as _os, sys as _sys
        _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
        from designed_welcome import build_welcome
        subject, html, text = build_welcome(name, partner_key, vertical)
    except Exception:
        subject, html, text = _em_welcome(name, partner_key, api_token, vertical=vertical)
    return _em_send(email, subject, html, text, bcc=WELCOME_AUDIT_BCC)


# ── models ──────────────────────────────────────────────────────────

class SignupReq(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(None, max_length=120)
    payout_method: str = Field(..., pattern="^(bank-transfer|paypal|stripe|revolut)$")
    payout_target: str = Field(..., min_length=2, max_length=200)
    hp: Optional[str] = Field(None, max_length=200)  # honeypot — must be empty/None
    vertical: Optional[str] = Field(None, pattern="^(widget|mtb|surf|golf|lgbtq|walks|scuba|clubs|brands|yoga|ski|pets)$")  # which widget they're downloading (2026-06-12; golf 2026-06-13; yoga/ski/pets 2026-06-14)


class BookingHookBody(BaseModel):
    booking_id: str = Field(..., min_length=2, max_length=120)
    partner_key: str = Field(..., min_length=4, max_length=64)
    base_value: float = Field(..., ge=0, le=1_000_000)
    currency: str = Field(..., min_length=3, max_length=3)
    booked_at: Optional[int] = None
    check_in_at: Optional[int] = None
    secret: Optional[str] = None  # legacy fallback (deprecated, ok for 7 days)


# ── team notification (partner signup / activation) ─────────────────
TEAM_NOTIFY = ["mike@impt.io", "cto-office@impt.io", "info@impt.io"]  # LOCKED mike+cto-office+info ONLY (Mike 2026-06-12)

def _send_team_gmail(subject: str, body: str):
    from email.mime.text import MIMEText
    from email.utils import formataddr
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        GMAIL_CREDS, scopes=["https://www.googleapis.com/auth/gmail.send"]
    ).with_subject(GMAIL_SENDER)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    msg = MIMEText(body)
    msg["to"] = ", ".join(TEAM_NOTIFY)
    msg["from"] = formataddr((GMAIL_FROM_NAME, GMAIL_SENDER))
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()

def notify_team(event: str, info: dict):
    """Email the IMPT team on partner signup/activation. Fire-and-forget; never breaks the request."""
    def _run():
        try:
            if event == "signup":
                subject = f"🔔 New IMPT Swarm widget signup — {info.get('email')}"
                body = (
                    "Someone just grabbed the IMPT Swarm partner widget.\n\n"
                    f"Email: {info.get('email')}\n"
                    f"Name: {info.get('name') or '—'}\n"
                    f"Payout: {info.get('payout_method')} → {info.get('payout_target')}\n"
                    f"Partner key: {info.get('key')}\n"
                    "Status: pending email verification (will activate once they confirm).\n\n"
                    "— IMPT Swarm widget · swarm.impt.io/widget"
                )
            else:  # verified / activated
                subject = f"✅ IMPT Swarm partner ACTIVATED — {info.get('email')}"
                body = (
                    "A partner just verified their email — their IMPT Swarm widget key is now LIVE.\n\n"
                    f"Email: {info.get('email')}\n"
                    f"Partner key: {info.get('key')}\n"
                    "Status: ACTIVE — they can embed the widget and earn 5%.\n\n"
                    "— IMPT Swarm widget · swarm.impt.io/widget"
                )
            res = _send_team_gmail(subject, body)
            print(f"[swarm-widget] team notified ({event}): id={res.get('id')}", flush=True)
        except Exception as e:
            print(f"[swarm-widget] notify_team FAILED ({event}): {e}", flush=True)
    try:
        import threading
        threading.Thread(target=_run, daemon=True).start()
    except Exception as e:
        print(f"[swarm-widget] notify_team thread FAILED ({event}): {e}", flush=True)


# ── routes ──────────────────────────────────────────────────────────

@app.get("/api/widget/health")
def health():
    return {"ok": True, "ts": int(time.time()), "version": "0.1.0"}


@app.post("/api/widget/partners/signup")
def signup(body: SignupReq, request: Request):
    ip_h = hash_ip(request.client.host if request.client else "")

    # Honeypot check (silent reject — return fake success to avoid signalling).
    if body.hp:
        audit("signup.honeypot_trip", subject=body.email, detail={"hp_len": len(body.hp)}, ip_hash=ip_h)
        return {"key": "p_pending", "ok": True}

    if not is_valid_email(body.email):
        audit("signup.bad_email", subject=body.email, detail=None, ip_hash=ip_h)
        raise HTTPException(400, "email rejected (disposable or malformed)")

    # Per-email burst control: max 2 pending signups in last 24h per email.
    with db() as c:
        recent = c.execute(
            "SELECT COUNT(*) AS n FROM partners WHERE email=? AND created_at > ?",
            (body.email, int(time.time()) - 86400)
        ).fetchone()["n"]
    if recent >= 2:
        audit("signup.email_burst", subject=body.email, detail={"recent_24h": recent}, ip_hash=ip_h)
        raise HTTPException(429, "too many signups for this email recently")

    key = "p_" + secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:12].lower()
    api_token = secrets.token_urlsafe(32)
    verify_token = secrets.token_urlsafe(24)
    with db() as c:
        try:
            c.execute(
                "INSERT INTO partners(key,email,name,payout_method,payout_target,created_at,status,api_token,verify_token,signup_ip_hash,vertical) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (key, body.email, body.name, body.payout_method, body.payout_target,
                 int(time.time()), "pending_email", api_token, verify_token, ip_h, body.vertical or "widget")
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "key collision, retry")

    sent = send_verify_email(body.email, body.name, key, verify_token, vertical=body.vertical)
    audit("signup.created", subject=key, detail={"email": body.email, "verify_sent": sent}, ip_hash=ip_h)
    notify_team("signup", {"email": body.email, "name": body.name, "payout_method": body.payout_method, "payout_target": body.payout_target, "key": key})
    # Meta Conversions API — report the partner signup so the Widget campaign can attribute + optimise.
    # Non-blocking: failures are logged inside meta_capi_event and never affect the signup response.
    meta_capi_event(
        "CompleteRegistration", body.email, key, f"{PUBLIC_BASE}/widget",
        ip_hash=ip_h,
        client_ip=(request.client.host if request.client else None),
        client_ua=request.headers.get("user-agent"),
        custom_data={"content_name": "IMPT Partner Widget Signup", "status": "pending_email"},
    )

    return {
        "key": key,
        "status": "pending_email",
        "verify_email_sent": sent,
        "message": "Check your email and click the verification link to activate your key.",
        "embed_preview": f'<script src="https://swarm.impt.io/widget.js" data-key="{key}" async></script>\n<div id="impt-swarm"></div>',
    }


@app.get("/api/widget/verify")
def verify(token: str = Query(..., min_length=10, max_length=100), request: Request = None):
    ip_h = hash_ip(request.client.host if (request and request.client) else "")
    with db() as c:
        row = c.execute("SELECT key, status, email, api_token, name, vertical FROM partners WHERE verify_token=?", (token,)).fetchone()
        if not row:
            raise HTTPException(404, "invalid or expired token")
        if row["status"] == "active":
            html_body = f"<p>Already verified.</p>"
            return HTMLResponse(content=verify_page("Already verified", html_body))
        c.execute(
            "UPDATE partners SET status='active', verified_at=?, verify_token=NULL WHERE verify_token=?",
            (int(time.time()), token)
        )
    audit("signup.verified", subject=row["key"], detail={"email": row["email"]}, ip_hash=ip_h)
    notify_team("verified", {"email": row["email"], "key": row["key"]})
    # Welcome / install email (fire-and-forget — never blocks the verify page).
    try:
        import threading
        threading.Thread(target=send_welcome_email,
                         args=(row["email"], row["name"], row["key"], row["api_token"]),
                         kwargs={"vertical": row["vertical"]},
                         daemon=True).start()
    except Exception as e:
        print(f"[swarm-widget] welcome-email thread FAILED: {e}", flush=True)
    snippet = f'&lt;script src="{PUBLIC_BASE}/widget.js" data-key="{row["key"]}" async&gt;&lt;/script&gt;\n&lt;div id="impt-swarm"&gt;&lt;/div&gt;'
    dash_url = f"{PUBLIC_BASE}/dashboard?k={row['key']}&t={row['api_token']}"
    body_html = f"""
    <p>Your partner key is <strong>active</strong>. We've just emailed you the full install guide too.</p>
    <p>Embed it on any page:</p>
    <pre>{snippet}</pre>
    <p>API token (keep this private — you'll use it for the dashboard):</p>
    <pre>{row['api_token']}</pre>
    <p>Earnings dashboard: <a href="{dash_url}">open your dashboard</a></p>
    """
    return HTMLResponse(content=verify_page("Verified ✓", body_html))


def verify_page(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title} — IMPT Swarm</title>
<style>body{{font-family:Inter,system-ui,sans-serif;max-width:560px;margin:80px auto;padding:0 24px;color:#08423a;background:#FAF7F0}}
h1{{font-family:Fraunces,Georgia,serif;font-weight:600}} pre{{background:#08423a;color:#FAF7F0;padding:18px;border-radius:12px;overflow-x:auto;font-size:13px}}
a{{color:#08423a}}</style></head><body>
<h1>{title}</h1>{body_html}
<p style="margin-top:40px;color:#3a6b62;font-size:13px">— IMPT Swarm · <a href="/widget">back to demo</a></p>
</body></html>"""


# ── One-click "get the widget & go" (2026-06-14) ───────────────────────────
# Mint an ACTIVE key in ONE click — no email/payout gate. Earnings accrue from
# click one; email + payout are collected later (optional capture on the result
# page / at withdrawal). Legacy /partners/signup + /verify are untouched.
VALID_VERTICALS = {"widget", "mtb", "surf", "golf", "lgbtq", "walks", "scuba", "clubs", "brands", "yoga", "ski", "pets"}


def _mint_active_key(vertical: str, ip_h: str, source: str = "oneclick"):
    vertical = (vertical or "widget").strip().lower()
    if vertical not in VALID_VERTICALS:
        vertical = "widget"
    for _ in range(4):
        key = "p_" + secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:12].lower()
        api_token = secrets.token_urlsafe(32)
        try:
            with db() as c:
                c.execute(
                    "INSERT INTO partners(key,email,name,payout_method,payout_target,created_at,status,api_token,verify_token,verified_at,signup_ip_hash,vertical,source) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (key, "", None, "pending", "", int(time.time()), "active", api_token, None, None, ip_h, vertical, source),
                )
            return key, api_token, vertical
        except sqlite3.IntegrityError:
            continue
    raise HTTPException(500, "could not mint key, retry")


def _quick_rate_ok(ip_h: str) -> bool:
    # Generous per-IP cap so a real person never hits it; blocks bulk minting.
    with db() as c:
        n = c.execute(
            "SELECT COUNT(*) AS n FROM partners WHERE signup_ip_hash=? AND created_at > ?",
            (ip_h, int(time.time()) - 3600),
        ).fetchone()["n"]
    return n < 20


def _capi_quick(key, ip_h, request):
    try:
        meta_capi_event(
            "CompleteRegistration", None, key, f"{PUBLIC_BASE}/widget",
            ip_hash=ip_h, client_ip=(request.client.host if request.client else None),
            client_ua=request.headers.get("user-agent"),
            custom_data={"content_name": "IMPT Widget One-Click", "status": "active"},
        )
    except Exception:
        pass


class QuickStartReq(BaseModel):
    vertical: Optional[str] = Field(None, max_length=20)
    hp: Optional[str] = Field(None, max_length=200)  # honeypot — must be empty


@app.post("/api/widget/quickstart")
def quickstart(body: QuickStartReq, request: Request):
    ip_h = hash_ip(request.client.host if request.client else "")
    if body.hp:
        return {"key": "p_pending", "ok": True}  # honeypot: fake success, mint nothing
    if not _quick_rate_ok(ip_h):
        raise HTTPException(429, "too many keys from this network recently")
    key, api_token, vertical = _mint_active_key(body.vertical, ip_h, source="oneclick_quickstart")
    audit("quickstart.minted", subject=key, detail={"vertical": vertical}, ip_hash=ip_h)
    notify_team("quickstart", {"key": key, "vertical": vertical})
    _capi_quick(key, ip_h, request)
    return {
        "key": key, "api_token": api_token, "vertical": vertical, "status": "active",
        "link": f"{PUBLIC_BASE}/api/widget/r?key={key}",
        "qr": f"{PUBLIC_BASE}/api/widget/qr/{key}.png",
        "embed": f'<script src="{PUBLIC_BASE}/widget.js" data-key="{key}" async></script>\n<div id="impt-swarm"></div>',
        "dashboard": f"{PUBLIC_BASE}/dashboard?k={key}&t={api_token}",
    }


class AttachEmailReq(BaseModel):
    key: str = Field(..., min_length=4, max_length=64)
    email: EmailStr


@app.post("/api/widget/attach-email")
def attach_email(body: AttachEmailReq, request: Request):
    ip_h = hash_ip(request.client.host if request.client else "")
    if not is_valid_email(body.email):
        raise HTTPException(400, "email rejected")
    with db() as c:
        row = c.execute("SELECT key,name,api_token,vertical FROM partners WHERE key=?", (body.key,)).fetchone()
        if not row:
            raise HTTPException(404, "unknown key")
        c.execute("UPDATE partners SET email=? WHERE key=?", (body.email, body.key))
        # Enroll this one-click recipient into the EXISTING email workflow (Mike 2026-06-14).
        # Create a leads row keyed to this partner so widget_nurture (+8h earnings / +24h
        # install-nudge) picks them up. purpose='widget' is what widget_nurture.due() reads;
        # the welcome itself is the per-vertical send_welcome_email below (uses partners.vertical).
        # Pre-mark lead_autoresponse so lead_autoresponder does NOT send a 2nd welcome.
        already = c.execute("SELECT id FROM leads WHERE partner_key=? LIMIT 1", (body.key,)).fetchone()
        if not already:
            cur = c.execute(
                "INSERT INTO leads(purpose,email,name,partner_key,ip_hash,is_test,created_at) "
                "VALUES ('widget',?,?,?,?,0,?)",
                (body.email, row["name"], body.key, ip_h, int(time.time())),
            )
            lead_id = cur.lastrowid
            c.execute(
                "INSERT OR IGNORE INTO lead_autoresponse(lead_id,purpose,sent_at,message_id) "
                "VALUES (?,?,?,?)",
                (lead_id, "widget", int(time.time()), "attach-email-welcome"),
            )
    audit("quickstart.email_attached", subject=body.key, detail={"email": body.email}, ip_hash=ip_h)
    try:
        import threading
        threading.Thread(
            target=send_welcome_email,
            args=(body.email, row["name"], body.key, row["api_token"]),
            kwargs={"vertical": row["vertical"]}, daemon=True,
        ).start()
    except Exception as e:
        print(f"[swarm-widget] attach-email welcome thread failed: {e}", flush=True)
    return {"ok": True}


@app.get("/api/widget/go")
def widget_go(request: Request, v: Optional[str] = None):
    ip_h = hash_ip(request.client.host if request.client else "")
    vertical = (v or "widget").strip().lower()
    if vertical not in VALID_VERTICALS:
        vertical = "widget"
    # Reuse this browser's existing active key (cookie) so refresh/return doesn't
    # mint duplicates; otherwise mint one now.
    key = api_token = None
    ck = request.cookies.get("impt_pkey")
    if ck:
        with db() as c:
            row = c.execute("SELECT key,api_token,status,vertical FROM partners WHERE key=?", (ck,)).fetchone()
        if row and row["status"] == "active":
            key, api_token, vertical = row["key"], row["api_token"], (row["vertical"] or vertical)
    minted = False
    if not key:
        if not _quick_rate_ok(ip_h):
            raise HTTPException(429, "too many keys from this network recently")
        key, api_token, vertical = _mint_active_key(vertical, ip_h, source="oneclick_go")
        minted = True
        audit("quickstart.minted", subject=key, detail={"vertical": vertical, "via": "go"}, ip_hash=ip_h)
        notify_team("quickstart", {"key": key, "vertical": vertical})
        _capi_quick(key, ip_h, request)
    # 2026-06-15: land the new partner on their EXCITING local vertical page (with the
    # "you're live" bar + their widget bound), not the bare receipt. Falls back to the
    # receipt for any vertical without a Stays page (generic / scuba / lgbtq / clubs / brands).
    if vertical in STAYS_VERTICALS:
        from urllib.parse import quote
        target = f"{STAYS_BASE}/{vertical}/?impt_live={quote(key)}&t={quote(api_token)}"
        resp = RedirectResponse(url=target, status_code=302)
    else:
        resp = HTMLResponse(content=_go_page(key, api_token, vertical))
    resp.set_cookie("impt_pkey", key, max_age=365 * 86400, path="/", secure=True, httponly=False, samesite="lax")
    return resp


# Per-discipline label + emoji for the one-click result page. Visual theming
# (palette, hero gradient/image, fonts) comes from the shared design system at
# /assets/impt-widget-ds.css via <body data-v="..."> — same as dashboard.html.
_GO_VLABELS = {
    "widget": ("Global", "🌍"), "mtb": ("Mountain Biking", "🚵"), "surf": ("Surf", "🏄"),
    "golf": ("Golf", "⛳"), "lgbtq": ("Pride", "🏳️‍🌈"), "walks": ("Walks & Hiking", "🥾"),
    "scuba": ("Scuba", "🤿"), "clubs": ("Clubs", "🎟️"), "brands": ("Brands", "✨"),
    "yoga": ("Yoga & Wellness", "🧘"), "ski": ("Ski & Snow", "🎿"), "pets": ("Pet-Friendly", "🐾"),
}

def _go_page(key: str, api_token: str, vertical: str) -> str:
    v = (vertical or "widget").lower()
    if v not in _GO_VLABELS:
        v = "widget"
    vlabel, vemoji = _GO_VLABELS[v]
    link = f"{PUBLIC_BASE}/api/widget/r?key={key}"
    qr = f"{PUBLIC_BASE}/api/widget/qr/{key}.png"
    dash = f"{PUBLIC_BASE}/dashboard?k={key}&t={api_token}"
    snippet = f'<script src="{PUBLIC_BASE}/widget.js" data-key="{key}" async></script>\n<div id="impt-swarm"></div>'
    snippet_esc = snippet.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    body = f"""<div class="wrap">
  <header class="top fade">
    <div class="brandrow"><span class="brand">impt</span>
      <span class="pill"><span class="dot"><i class="ping"></i><i></i></span>Your {vlabel} widget · Live</span></div>
  </header>
  <section class="hero fade d1">
    <div class="img"></div><div class="shade"></div>
    <div class="in">
      <div class="cap">You're live {vemoji}</div>
      <div class="big" style="font-size:42px">Off you go.</div>
      <div class="sub">Share your link and earn <strong>5% on every booking</strong> — paid in full. Nothing else to set up.</div>
    </div>
  </section>
  <section class="card pad mt fade d2">
    <div class="lbl">Your personal link — share it anywhere</div>
    <div class="row" style="margin-top:12px"><input class="field" id="lnk" value="{link}" readonly><button class="btn" onclick="cp()">Copy</button><button class="btn ghost" id="sh">Share</button></div>
    <div class="ok" id="lok">Copied ✓</div>
  </section>
  <section class="card pad mt fade d3">
    <div class="lbl">Put it on your phone / posters</div>
    <div class="share-grid" style="margin-top:14px">
      <div class="muted" style="font-size:14px">Scan to open your booking link on a phone. Save the image for a story, a flyer, anywhere your people are.</div>
      <div class="qrbox"><div class="b"><img src="{qr}" alt="Your widget QR code"></div><div class="c">Scan to share</div></div>
    </div>
  </section>
  <section class="card pad mt fade d4">
    <div class="lbl">Have a website? Paste this once</div>
    <pre class="snip" id="snip" style="margin-top:12px">{snippet_esc}</pre>
    <div class="row" style="margin-top:12px"><button class="btn ghost" onclick="cpPre(this)">Copy code</button></div>
  </section>
  <section class="card pad mt fade d5">
    <div class="lbl">Want your dashboard + link emailed? (optional)</div>
    <div class="row" style="margin-top:12px"><input class="field" id="em" type="email" placeholder="you@email.com"><button class="btn" onclick="claim(this)">Email it to me</button></div>
    <div class="ok" id="eok">Sent ✓ check your inbox</div>
    <div class="note">Payout details are only needed when you withdraw earnings — not now.</div>
  </section>
  <p style="margin-top:20px"><a class="siglink" href="{dash}">Open my earnings dashboard →</a></p>
  <div class="foot">IMPT — hotels that pay you back &amp; offset carbon. <span style="opacity:.75">8M+ hotels worldwide · every stay offsets 1 tonne of CO₂.</span></div>
</div>"""
    JS = (
        "function cp(b){var i=document.getElementById('lnk');i.select();navigator.clipboard.writeText(i.value).then(function(){document.getElementById('lok').style.display='block';});}"
        "function cpPre(b){var t=document.getElementById('snip').textContent;navigator.clipboard.writeText(t).then(function(){b.textContent='Copied \\u2713';});}"
        "document.getElementById('sh').onclick=function(){var u=document.getElementById('lnk').value;if(navigator.share){navigator.share({title:'Book hotels with IMPT',url:u});}else{cp();}};"
        "function claim(b){var e=document.getElementById('em').value;if(!e||e.indexOf('@')<1){return;}b.disabled=true;b.textContent='Sending\\u2026';"
        "fetch('__BASE__/api/widget/attach-email',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:'__KEY__',email:e})})"
        ".then(function(r){if(r.ok){document.getElementById('eok').style.display='block';b.textContent='Sent \\u2713';}else{b.disabled=false;b.textContent='Try again';}})"
        ".catch(function(){b.disabled=false;b.textContent='Try again';});}"
    ).replace("__BASE__", PUBLIC_BASE).replace("__KEY__", key)
    return ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Your IMPT widget is live</title>"
            "<link rel='preconnect' href='https://fonts.googleapis.com'><link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
            "<link rel='stylesheet' href='/assets/impt-widget-ds.css?v=20260614d'></head>"
            f"<body data-v='{v}'>" + body + "<script>" + JS + "</script></body></html>")


# IMPT-owned destinations the redirect may send to (open-redirect guard).
ALLOWED_REDIRECT_HOSTS = {"app.impt.io", "impt.io", "www.impt.io", "shop.impt.io"}

@app.get("/api/widget/r")
def redirect(request: Request, key: str = Query(..., min_length=4, max_length=64),
             dest: Optional[str] = None, checkIn: Optional[str] = None, checkOut: Optional[str] = None,
             adults: Optional[str] = None, rooms: Optional[str] = None,
             to: Optional[str] = None, med: Optional[str] = None):
    from urllib.parse import quote, urlparse
    ip_h = hash_ip(request.client.host if request.client else "")
    with db() as c:
        partner = c.execute("SELECT status, vertical FROM partners WHERE key=?", (key,)).fetchone()
        # Always log the click attempt for audit.
        c.execute(
            "INSERT INTO partner_events(key,evt,dest,ref,ip_hash,ua_hash,ts) VALUES (?,?,?,?,?,?,?)",
            (key, "click" if (partner and partner["status"] == "active") else "click_inactive",
             dest, request.headers.get("referer", ""), ip_h,
             hash_ua(request.headers.get("user-agent", "")), int(time.time()))
        )

    # Destination: default hotel search, or an allowlisted IMPT URL (MTB site, shop) via `to`.
    base = LANDER
    # Vertical-bound widgets (Mike 2026-06-13): a vertical widget ALWAYS operates with the pages
    # we set up — it must NEVER fall back to the main hotel search. So a vertical partner lands on
    # its own vertical page in every case (typed search included); the typed query rides along so
    # the vertical page can use it. Only generic ("widget") partners use the main search lander.
    if not to and partner:
        base = VERTICAL_LANDERS.get((partner["vertical"] or "").strip().lower(), LANDER)
    if to:
        try:
            u = urlparse(to)
            if u.scheme == "https" and u.netloc.lower() in ALLOWED_REDIRECT_HOSTS:
                base = to
        except Exception:
            base = LANDER

    qs = []
    set_cookie = False
    if partner and partner["status"] == "active":
        medium = "".join(ch for ch in (med or "widget") if ch.isalnum() or ch == "-")[:32] or "widget"
        qs = [f"utm_source=swarm-{quote(key)}", f"utm_medium={medium}", "utm_campaign=oss"]
        set_cookie = True
    # If key inactive/unknown: redirect anyway (graceful UX) but no commission attribution.
    if dest:
        qs.append("destination=" + quote(dest))
        qs.append("locationName=" + quote(dest))
    # Forward the search the guest actually made (dates/guests) so they land on results.
    for pname, pval in (("checkIn", checkIn), ("checkOut", checkOut), ("adults", adults), ("rooms", rooms)):
        if pval:
            qs.append(f"{pname}=" + quote(str(pval)))
    sep = "&" if "?" in base else "?"
    target = base + (sep + "&".join(qs) if qs else "")
    resp = RedirectResponse(url=target, status_code=302)
    if set_cookie:
        resp.set_cookie(
            key="impt_partner",
            value=key,
            max_age=COOKIE_DAYS * 86400,
            domain=".impt.io",
            path="/",
            secure=True,
            httponly=False,
            samesite="lax",
        )
    return resp


@app.get("/api/widget/track")
def track(request: Request, key: str = Query(..., max_length=64), evt: str = Query(..., max_length=20),
          dest: Optional[str] = None, ref: Optional[str] = None):
    if evt not in ("view", "click", "impression", "ref",
                   "wl_open", "wl_play", "wl_book", "wl_share",  # wavelength channel (2026-06-12)
                   "share", "share_click"):  # share-hub activation channel (lane A, 2026-06-12)
        evt = "view"
    with db() as c:
        c.execute(
            "INSERT INTO partner_events(key,evt,dest,ref,ip_hash,ua_hash,ts) VALUES (?,?,?,?,?,?,?)",
            (key, evt, dest, ref or request.headers.get("referer", ""),
             hash_ip(request.client.host if request.client else ""),
             hash_ua(request.headers.get("user-agent", "")), int(time.time()))
        )
    return Response(content=GIF_1x1, media_type="image/gif",
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/api/widget/brand")
def brand(key: str = Query(..., max_length=64)):
    """Public: partner display name (+ logo/color if set) for personalising the widget."""
    name = ""; logo = ""; color = ""
    with db() as c:
        try:
            r = c.execute("SELECT name FROM partners WHERE key=?", (key,)).fetchone()
            if r and r[0]:
                name = r[0]
        except Exception:
            pass
        try:
            b = c.execute("SELECT name,logo_url,color FROM partner_brand WHERE key=?", (key,)).fetchone()
            if b:
                name = b[0] or name; logo = b[1] or ""; color = b[2] or ""
        except Exception:
            pass
    return JSONResponse({"name": name, "logo": logo, "color": color},
                        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=300"})


class _SetName(BaseModel):
    key: str = Field(..., max_length=64)
    token: str = Field(..., max_length=128)
    name: str = Field("", max_length=60)


@app.post("/api/widget/setname")
def set_name(p: _SetName):
    """Partner sets the display name shown on their widget (auth via their api_token)."""
    nm = (p.name or "").strip()[:40]
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS partner_brand(key TEXT PRIMARY KEY, name TEXT, "
                  "logo_url TEXT, color TEXT, updated_at INTEGER)")
        r = c.execute("SELECT api_token FROM partners WHERE key=?", (p.key,)).fetchone()
        if not r or r[0] != p.token:
            raise HTTPException(403, "bad key/token")
        c.execute("INSERT INTO partner_brand(key,name,updated_at) VALUES(?,?,?) "
                  "ON CONFLICT(key) DO UPDATE SET name=excluded.name, updated_at=excluded.updated_at",
                  (p.key, nm, int(time.time())))
    return JSONResponse({"ok": True, "name": nm}, headers={"Access-Control-Allow-Origin": "*"})


@app.post("/api/widget/booking")
async def booking(request: Request,
                  x_impt_signature: Optional[str] = Header(None, alias="X-IMPT-Signature")):
    """
    HMAC-signed webhook. Verify with:
        sig = "sha256=" + hmac.new(secret, raw_body, sha256).hexdigest()

    Legacy: also accept body.secret for the first 7 days post-launch.
    """
    raw = await request.body()
    if len(raw) > 8192:
        raise HTTPException(413, "body too large")

    auth_ok = False
    if x_impt_signature:
        try:
            algo, hexsig = x_impt_signature.split("=", 1)
        except ValueError:
            raise HTTPException(400, "bad signature header")
        if algo.lower() != "sha256":
            raise HTTPException(400, "unsupported sig algo")
        expected = hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, hexsig.lower()):
            auth_ok = True

    try:
        payload = json.loads(raw)
        body = BookingHookBody(**payload)
    except Exception:
        raise HTTPException(400, "bad json body")

    if not auth_ok:
        # Legacy fallback for first 7 days.
        if body.secret and hmac.compare_digest(body.secret, WEBHOOK_SECRET):
            auth_ok = True
        else:
            audit("webhook.bad_auth", subject=body.booking_id, detail=None,
                  ip_hash=hash_ip(request.client.host if request.client else ""))
            raise HTTPException(401, "bad signature")

    eur_cents = to_eur_cents(body.base_value, body.currency)
    accrual = int(eur_cents * COMMISSION_PCT)
    with db() as c:
        partner = c.execute("SELECT status FROM partners WHERE key=?", (body.partner_key,)).fetchone()
        if not partner:
            raise HTTPException(404, "unknown partner_key")
        if partner["status"] != "active":
            raise HTTPException(403, f"partner key not active (status={partner['status']})")
        try:
            c.execute(
                "INSERT INTO partner_bookings(partner_key,booking_id,base_value_cents,currency,accrual_eur_cents,status,booked_at,check_in_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (body.partner_key, body.booking_id, int(body.base_value * 100), body.currency.upper(),
                 accrual, "pending", body.booked_at or int(time.time()),
                 body.check_in_at, int(time.time()))
            )
        except sqlite3.IntegrityError:
            return {"ok": True, "duplicate": True}
    audit("booking.recorded", subject=body.booking_id,
          detail={"partner_key": body.partner_key, "accrual_eur_cents": accrual})
    return {"ok": True, "accrual_eur_cents": accrual, "commission_pct": COMMISSION_PCT}


@app.get("/api/widget/partners/me")
def me(authorization: str = Header(...)):
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer")
    token = authorization.split(" ", 1)[1].strip()
    with db() as c:
        partner = c.execute("SELECT key,email,name,payout_method,created_at,status,vertical FROM partners WHERE api_token=?", (token,)).fetchone()
        if not partner:
            raise HTTPException(401, "bad token")
        bookings = c.execute(
            "SELECT booking_id,base_value_cents,currency,accrual_eur_cents,status,booked_at,check_in_at FROM partner_bookings WHERE partner_key=? ORDER BY booked_at DESC LIMIT 100",
            (partner["key"],)
        ).fetchall()
        balance = c.execute(
            "SELECT COALESCE(SUM(accrual_eur_cents),0) AS bal FROM partner_bookings WHERE partner_key=? AND status IN ('pending','checked_in','payable')",
            (partner["key"],)
        ).fetchone()["bal"]
        clicks_30d = c.execute(
            "SELECT COUNT(*) AS n FROM partner_events WHERE key=? AND evt='click' AND ts > ?",
            (partner["key"], int(time.time()) - 30 * 86400)
        ).fetchone()["n"]
    return {
        "partner": dict(partner),
        "balance_eur_cents": balance,
        "clicks_30d": clicks_30d,
        "bookings": [dict(b) for b in bookings],
    }


# ── omnichannel additions (intents + hotels proxy + TG/WA/FB bots) ───
# Added 2026-05-09 by Claude end-to-end build.
import os as _os
import urllib.parse as _urlparse
import urllib.request as _urlreq
import urllib.error as _urlerr
from fastapi import Body
from fastapi.responses import PlainTextResponse

CITIES = [
    {"name":"Dublin","country":"IE","lat":53.3498,"lon":-6.2603,"currency":"EUR"},
    {"name":"Cork","country":"IE","lat":51.8985,"lon":-8.4756,"currency":"EUR"},
    {"name":"Galway","country":"IE","lat":53.2707,"lon":-9.0568,"currency":"EUR"},
    {"name":"Limerick","country":"IE","lat":52.6638,"lon":-8.6267,"currency":"EUR"},
    {"name":"Belfast","country":"GB","lat":54.5973,"lon":-5.9301,"currency":"GBP"},
    {"name":"London","country":"GB","lat":51.5074,"lon":-0.1278,"currency":"GBP"},
    {"name":"Edinburgh","country":"GB","lat":55.9533,"lon":-3.1883,"currency":"GBP"},
    {"name":"Manchester","country":"GB","lat":53.4808,"lon":-2.2426,"currency":"GBP"},
    {"name":"Paris","country":"FR","lat":48.8566,"lon":2.3522,"currency":"EUR"},
    {"name":"Barcelona","country":"ES","lat":41.3851,"lon":2.1734,"currency":"EUR"},
    {"name":"Madrid","country":"ES","lat":40.4168,"lon":-3.7038,"currency":"EUR"},
    {"name":"Rome","country":"IT","lat":41.9028,"lon":12.4964,"currency":"EUR"},
    {"name":"Milan","country":"IT","lat":45.4642,"lon":9.19,"currency":"EUR"},
    {"name":"Amsterdam","country":"NL","lat":52.3676,"lon":4.9041,"currency":"EUR"},
    {"name":"Berlin","country":"DE","lat":52.52,"lon":13.405,"currency":"EUR"},
    {"name":"Lisbon","country":"PT","lat":38.7223,"lon":-9.1393,"currency":"EUR"},
    {"name":"New York","country":"US","lat":40.7128,"lon":-74.006,"currency":"USD"},
    {"name":"Los Angeles","country":"US","lat":34.0522,"lon":-118.2437,"currency":"USD"},
    {"name":"Miami","country":"US","lat":25.7617,"lon":-80.1918,"currency":"USD"},
    {"name":"Tokyo","country":"JP","lat":35.6762,"lon":139.6503,"currency":"JPY"},
    {"name":"Singapore","country":"SG","lat":1.3521,"lon":103.8198,"currency":"SGD"},
    {"name":"Dubai","country":"AE","lat":25.2048,"lon":55.2708,"currency":"AED"},
    {"name":"Sydney","country":"AU","lat":-33.8688,"lon":151.2093,"currency":"AUD"},
    {"name":"Bangkok","country":"TH","lat":13.7563,"lon":100.5018,"currency":"THB"},
]
_CITY_BY_NAME = {c["name"].lower(): c for c in CITIES}

TG_BOT_TOKEN = _os.environ.get("TG_BOT_TOKEN", "")
TG_WEBHOOK_SECRET = _os.environ.get("TG_WEBHOOK_SECRET", "")
# Rambo is Mike's PRIVATE control interface (2026-05-10 pivot).
# TG_WHITELIST = comma-separated chat_ids granted Mike-tier control.
# Until Mike registers his chat_id via `/whitelist <secret>`, this is empty
# and every incoming message is silently logged.
TG_WHITELIST = {x.strip() for x in _os.environ.get("TG_WHITELIST", "").split(",") if x.strip()}
TG_WHITELIST_SECRET = _os.environ.get("TG_WHITELIST_SECRET", "")
TG_WHITELIST_FILE = _os.environ.get("TG_WHITELIST_FILE", "/srv/swarm/impt-swarm-oss-2026-05-05/backend/.tg_whitelist")
# Hydrate from on-disk store too (so `/whitelist` writes persist across restarts).
try:
    if _os.path.exists(TG_WHITELIST_FILE):
        with open(TG_WHITELIST_FILE) as _fh:
            for _ln in _fh.read().splitlines():
                _ln = _ln.strip()
                if _ln:
                    TG_WHITELIST.add(_ln)
except Exception:
    pass


def _persist_whitelist_chatid(chat_id: str):
    """Append a chat_id to the on-disk whitelist so it survives restart."""
    try:
        existing = set()
        if _os.path.exists(TG_WHITELIST_FILE):
            with open(TG_WHITELIST_FILE) as fh:
                for ln in fh.read().splitlines():
                    ln = ln.strip()
                    if ln:
                        existing.add(ln)
        if chat_id not in existing:
            existing.add(chat_id)
            with open(TG_WHITELIST_FILE, "w") as fh:
                for x in sorted(existing):
                    fh.write(x + "\n")
        TG_WHITELIST.add(chat_id)
    except Exception as e:
        print(f"[tg_whitelist] persist failed: {e}", flush=True)


WA_PHONE_NUMBER_ID = _os.environ.get("WA_PHONE_NUMBER_ID", "")
WA_TOKEN = _os.environ.get("WA_TOKEN", "")
WA_VERIFY_TOKEN = _os.environ.get("WA_VERIFY_TOKEN", "")
FB_PAGE_ACCESS_TOKEN = _os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
FB_VERIFY_TOKEN = _os.environ.get("FB_VERIFY_TOKEN", "")


def find_city(name):
    if not name:
        return None
    return _CITY_BY_NAME.get(name.strip().lower())


def init_omnichannel_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS intents (
          iid TEXT PRIMARY KEY,
          key TEXT NOT NULL,
          channel TEXT NOT NULL,
          destination TEXT NOT NULL,
          campaign TEXT,
          creator TEXT,
          click_id TEXT,
          status TEXT NOT NULL DEFAULT 'created',
          ts INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_intents_key ON intents(key);
        CREATE INDEX IF NOT EXISTS idx_intents_ts ON intents(ts);
        CREATE TABLE IF NOT EXISTS bot_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          channel TEXT NOT NULL,
          chat_id TEXT,
          intent_iid TEXT,
          payload TEXT,
          ts INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_bot_events_ts ON bot_events(ts);
        CREATE INDEX IF NOT EXISTS idx_bot_events_channel ON bot_events(channel);
        """)


def new_iid():
    return "iid_" + secrets.token_urlsafe(9).replace("-", "X").replace("_", "Y")[:12]


def build_deeplink(iid, dest, key, channel, *, campaign="bot", creator=None, click_id=None):
    p = {}
    hit = find_city(dest)
    if hit:
        p["destination"] = hit["name"]
        p["locationName"] = hit["name"]
        p["tl"] = hit["country"].lower()
        p["gl"] = hit["country"].lower()
    elif dest:
        p["destination"] = dest
    # Idempotent prefix — accept "public" or "swarm-public", emit "swarm-public" once.
    norm_key = key[len("swarm-"):] if key.startswith("swarm-") else key
    p["utm_source"] = f"swarm-{norm_key}"
    p["utm_medium"] = channel
    p["utm_campaign"] = campaign
    p["utm_content"] = creator or "cream"
    p["iid"] = iid
    if click_id:
        p["click_id"] = click_id
    return f"{LANDER}?{_urlparse.urlencode(p)}"


def _persist_intent(iid, key, channel, dest, *, campaign="bot", creator=None, click_id=None):
    hit = find_city(dest)
    nice = hit["name"] if hit else dest
    with db() as c:
        c.execute(
            "INSERT OR REPLACE INTO intents(iid,key,channel,destination,campaign,creator,click_id,status,ts) VALUES (?,?,?,?,?,?,?,?,?)",
            (iid, key, channel, nice, campaign, creator, click_id, "created", int(time.time()))
        )
    return nice


# ── /api/widget/intent — JSON intent creation for adapters ──────────
@app.post("/api/widget/intent")
def widget_intent(payload: dict = Body(...)):
    dest = (payload.get("destination") or "").strip()
    if not dest:
        return JSONResponse({"error": "destination_required", "hint": "Pass a CITY (never country)."}, status_code=400)
    partner = payload.get("partner") or {}
    key = (partner.get("key") or "swarm-public")[:64]
    channel = (partner.get("channel") or "widget")[:32]
    campaign = (partner.get("campaign") or "oss")[:64]
    creator = (partner.get("creator") or None)
    click_id = (partner.get("click_id") or None)
    iid = new_iid()
    nice = _persist_intent(iid, key, channel, dest, campaign=campaign, creator=creator, click_id=click_id)
    deeplink = build_deeplink(iid, nice, key, channel, campaign=campaign, creator=creator, click_id=click_id)
    track_url = (
        f"{PUBLIC_BASE}/api/widget/track?key={_urlparse.quote(key)}"
        f"&evt=intent_created&channel={_urlparse.quote(channel)}"
        f"&dest={_urlparse.quote(nice)}&iid={iid}&ts={int(time.time()*1000)}"
    )
    embed = (
        f'<script src="https://swarm.impt.io/widget.js" data-key="{key}" data-dest="{nice}" async></script>'
        f'<div id="impt-swarm"></div>'
    )
    qr = f"{PUBLIC_BASE}/api/widget/qr/{_urlparse.quote(key)}.svg?dest={_urlparse.quote(nice)}&iid={iid}"
    return {"intent_id": iid, "deeplink": deeplink, "track": track_url, "embed": embed, "qr": qr}


# ── /api/widget/quote/{iid} — read intent ──────────────────────────
@app.get("/api/widget/quote/{iid}")
def widget_quote(iid: str):
    if not iid.startswith("iid_"):
        return JSONResponse({"error": "invalid_iid"}, status_code=400)
    with db() as c:
        row = c.execute("SELECT * FROM intents WHERE iid=?", (iid,)).fetchone()
    if not row:
        return JSONResponse({"error": "intent_not_found"}, status_code=404)
    rec = dict(row)
    hit = find_city(rec["destination"])
    deeplink = build_deeplink(rec["iid"], rec["destination"], rec["key"], rec["channel"],
                              campaign=rec.get("campaign") or "oss", creator=rec.get("creator"))
    return {
        "intent_id": rec["iid"],
        "status": rec["status"],
        "destination": rec["destination"],
        "currency": (hit or {}).get("currency", "USD"),
        "deeplink": deeplink,
        "ts": rec["ts"],
    }


# ── /api/widget/hotels — JSON hotel search proxy ───────────────────
@app.get("/api/widget/hotels")
def widget_hotels(city: str, key: str = "swarm-public", channel: str = "widget",
                  adults: int = 2, rooms: int = 1, limit: int = 10,
                  checkIn: Optional[str] = None, checkOut: Optional[str] = None,
                  currency: Optional[str] = None):
    hit = find_city(city)
    if not hit:
        return JSONResponse({"error": "unknown_city", "hint": "Add to CITIES list."}, status_code=400)
    from datetime import datetime, timedelta, timezone
    if not checkIn:
        checkIn = (datetime.now(timezone.utc) + timedelta(days=14)).date().isoformat()
    if not checkOut:
        checkOut = (datetime.now(timezone.utc) + timedelta(days=16)).date().isoformat()
    if not currency:
        currency = hit["currency"]
    adults = max(1, min(8, adults))
    rooms = max(1, min(4, rooms))
    limit = max(1, min(30, limit))
    upstream = (
        f"https://platform.impt.io/api/hotels?lat={hit['lat']}&lng={hit['lon']}"
        f"&checkIn={checkIn}&checkOut={checkOut}&adults={adults}&rooms={rooms}"
        f"&currency={_urlparse.quote(currency)}&page=1"
    )
    try:
        req = _urlreq.Request(upstream, headers={
            "accept": "application/json",
            "x-swarm-key": key,
            "x-swarm-channel": channel,
            "user-agent": "swarm-widget-proxy/0.2",
        })
        with _urlreq.urlopen(req, timeout=15) as r:
            raw = r.read()
            data = json.loads(raw)
    except _urlerr.HTTPError as e:
        return JSONResponse({"error": "upstream_error", "upstream_status": e.code}, status_code=502)
    except Exception as e:
        return JSONResponse({"error": "upstream_unreachable", "detail": str(e)[:200]}, status_code=502)
    # platform.impt.io shape: { data: { sessionId, filter, hotels: [...], meta } }
    payload = data.get("data") if isinstance(data, dict) else None
    if isinstance(payload, dict):
        arr = payload.get("hotels") or []
        session_id = payload.get("sessionId")
    elif isinstance(payload, list):
        arr = payload
        session_id = None
    else:
        arr = []
        session_id = None
    return {"city": hit["name"], "count": min(len(arr), limit), "hotels": arr[:limit],
            "cached": False, "session_id": session_id}


# ── /api/widget/qr — real QR generator (segno) ─────────────────────
def _make_qr(target: str, fmt: str) -> tuple[bytes, str]:
    """Generate a real QR encoding `target` in cream/ink/lime palette."""
    import segno
    import io
    qr = segno.make(target, error="m")
    buf = io.BytesIO()
    if fmt == "svg":
        qr.save(buf, kind="svg", scale=8, dark="#08423a", light="#FAF7F0",
                border=2, finder_dark="#08423a", quiet_zone="#FAF7F0",
                xmldecl=True, svgns=True)
        return buf.getvalue(), "image/svg+xml"
    else:  # png
        qr.save(buf, kind="png", scale=10, dark="#08423a", light="#FAF7F0", border=2)
        return buf.getvalue(), "image/png"


def _qr_target(key: str, dest: Optional[str], iid: Optional[str]) -> str:
    """The URL a scanned widget QR resolves to.

    Default (no explicit dest): encode the partner's own vertical-aware redirect
    /api/widget/r?key=...&med=qr — so a scan lands on the SAME local vertical page
    as the Copy/Share link (golf→/worlds, surf→/surf-hotels/, etc.) and sets the
    attribution cookie. Only the ads/intent path passes an explicit dest, which
    legitimately wants a city deeplink via build_deeplink.  (2026-06-14 QR fix)
    """
    if dest is None:
        from urllib.parse import quote as _q
        return f"{PUBLIC_BASE}/api/widget/r?key={_q(key)}&med=qr"
    return build_deeplink(iid or new_iid(), dest, key, "qr", campaign="qr")


@app.get("/api/widget/qr/{key}.svg")
def widget_qr_svg(key: str, dest: Optional[str] = None, iid: Optional[str] = None):
    target = _qr_target(key, dest, iid)
    body, ct = _make_qr(target, "svg")
    return Response(body, media_type=ct, headers={
        "X-Target-URL": target,
        "Cache-Control": "public, max-age=300",
        "Content-Disposition": f'inline; filename="impt-{key}.svg"',
    })


@app.get("/api/widget/qr/{key}.png")
def widget_qr_png(key: str, dest: Optional[str] = None, iid: Optional[str] = None):
    target = _qr_target(key, dest, iid)
    body, ct = _make_qr(target, "png")
    return Response(body, media_type=ct, headers={
        "X-Target-URL": target,
        "Cache-Control": "public, max-age=300",
        "Content-Disposition": f'inline; filename="impt-{key}.png"',
    })


# ── /api/email/sig/{key} — Gmail/Outlook-pasteable signature snippet ──
@app.get("/api/email/sig/{key}")
def email_signature(key: str, dest: str = "Dublin", style: str = "cream"):
    """Returns an HTML snippet partners paste into their email signature settings."""
    iid = new_iid()
    nice = _persist_intent(iid, key, "email", dest, campaign="signature")
    url = build_deeplink(iid, nice, key, "email", campaign="signature")
    # Outlook-safe inline HTML (no shadow-dom, no external CSS, no SVG positioning tricks).
    html = (
        f'<p style="margin:0;padding:8px 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#08423a">'
        f'<span style="display:inline-block;background:#C8FF7E;color:#08423a;padding:3px 10px;border-radius:12px;'
        f'font-weight:bold;font-size:12px;margin-right:8px">🌱 IMPT</span>'
        f'<a href="{url}" target="_blank" style="color:#08423a;text-decoration:none">'
        f'Book green hotels in {nice}</a> — '
        f'<span style="color:#3a6b62">€5 free + 5% Goodness back · 1 tonne CO₂ offset per booking</span>'
        f'</p>'
    )
    text_fallback = f"Book green hotels — €5 free + 5% back: {url}"
    return {
        "html": html,
        "text": text_fallback,
        "url": url,
        "intent_id": iid,
        "instructions": {
            "gmail": "Settings → Signature → Insert and paste the HTML.",
            "outlook": "File → Options → Mail → Signatures → paste in the editor.",
            "apple_mail": "Mail → Settings → Signatures → drag-drop the HTML.",
        }
    }


# ── /api/gpt/openapi.json — ChatGPT Custom GPT Action manifest ─────
@app.get("/api/gpt/openapi.json")
def gpt_openapi():
    """OpenAPI 3.1 spec scoped for ChatGPT Custom GPT Action use.
    Single server, no auth, simple ops — ChatGPT renders it cleanly."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "IMPT — book green hotels",
            "description": "Search hotels and produce booking deeplinks via IMPT. Every booking offsets 1 tonne of CO₂ and gives the guest €5 free + 5% Goodness back. Adapter for ChatGPT Custom GPTs.",
            "version": "1.0.0",
        },
        "servers": [{"url": "https://swarm.impt.io"}],
        "paths": {
            "/api/widget/hotels": {
                "get": {
                    "operationId": "searchHotels",
                    "summary": "Search hotels in a city",
                    "parameters": [
                        {"name": "city", "in": "query", "required": True,
                         "schema": {"type": "string"},
                         "description": "City name (never country). Examples: Dublin, Paris, Tokyo."},
                        {"name": "adults", "in": "query", "schema": {"type": "integer", "default": 2}},
                        {"name": "rooms", "in": "query", "schema": {"type": "integer", "default": 1}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 5}},
                        {"name": "key", "in": "query", "schema": {"type": "string", "default": "swarm-gpt"}},
                        {"name": "channel", "in": "query", "schema": {"type": "string", "default": "gpt"}},
                    ],
                    "responses": {"200": {"description": "List of hotels"}},
                }
            },
            "/api/widget/intent": {
                "post": {
                    "operationId": "createBookingDeeplink",
                    "summary": "Create a booking intent + canonical deeplink",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {
                            "type": "object",
                            "required": ["destination", "partner"],
                            "properties": {
                                "destination": {"type": "string", "description": "City name"},
                                "partner": {"type": "object", "properties": {
                                    "key": {"type": "string", "default": "swarm-gpt"},
                                    "channel": {"type": "string", "default": "gpt"},
                                }},
                            }
                        }}}
                    },
                    "responses": {"200": {"description": "Returns deeplink + intent_id"}},
                }
            },
            "/api/widget/quote/{iid}": {
                "get": {
                    "operationId": "getQuote",
                    "summary": "Look up a previously-created intent by iid",
                    "parameters": [{"name": "iid", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Intent record + deeplink"}},
                }
            },
        },
    }


# ── /api/mcp — Model Context Protocol HTTP transport (Claude/ChatGPT/etc.) ──
# Minimal MCP HTTP transport. Single POST endpoint accepts JSON-RPC 2.0 requests
# for: initialize, tools/list, tools/call. Bidirectional SSE not implemented —
# stateless request/response is sufficient for our four hotel-booking tools.
MCP_TOOLS = [
    {
        "name": "impt_search_hotels",
        "description": "Search IMPT hotels in a city. Returns up to 10 hotels with prices, photos, room types. Books with €5 free + 5% Goodness back + 1 tonne CO₂ offset per booking.",
        "inputSchema": {
            "type": "object",
            "required": ["city"],
            "properties": {
                "city": {"type": "string", "description": "City name (Dublin, Paris, Tokyo, etc). Never use a country."},
                "adults": {"type": "integer", "default": 2, "minimum": 1, "maximum": 8},
                "rooms": {"type": "integer", "default": 1, "minimum": 1, "maximum": 4},
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 30},
            },
        },
    },
    {
        "name": "impt_create_intent",
        "description": "Create a booking intent and return a canonical deeplink the user can open to complete payment on app.impt.io. Use this when the user has settled on a city.",
        "inputSchema": {
            "type": "object",
            "required": ["destination"],
            "properties": {
                "destination": {"type": "string", "description": "City name"},
                "partner_key": {"type": "string", "default": "swarm-mcp"},
            },
        },
    },
    {
        "name": "impt_get_quote",
        "description": "Look up a previously-created intent by intent_id (iid_*) — returns the destination + deeplink + status.",
        "inputSchema": {
            "type": "object",
            "required": ["intent_id"],
            "properties": {"intent_id": {"type": "string", "description": "iid_* identifier returned by impt_create_intent"}},
        },
    },
    {
        "name": "impt_get_deeplink",
        "description": "Synthesize a find-hotel-input deeplink without persisting an intent. Useful for previews or when the user just wants a URL to share.",
        "inputSchema": {
            "type": "object",
            "required": ["destination"],
            "properties": {
                "destination": {"type": "string"},
                "partner_key": {"type": "string", "default": "swarm-mcp"},
            },
        },
    },
]


def _mcp_tool_call(name: str, args: dict):
    """Run a tool synchronously and return MCP content array."""
    try:
        if name == "impt_search_hotels":
            city = args.get("city", "")
            hit = find_city(city)
            if not hit:
                return [{"type": "text", "text": f"City '{city}' not in supported list. Try Dublin, Paris, Tokyo, etc."}]
            from datetime import datetime, timedelta, timezone
            ci = (datetime.now(timezone.utc) + timedelta(days=14)).date().isoformat()
            co = (datetime.now(timezone.utc) + timedelta(days=16)).date().isoformat()
            url = (f"https://platform.impt.io/api/hotels?lat={hit['lat']}&lng={hit['lon']}"
                   f"&checkIn={ci}&checkOut={co}&adults={int(args.get('adults', 2))}"
                   f"&rooms={int(args.get('rooms', 1))}&currency={hit['currency']}&page=1")
            try:
                with _urlreq.urlopen(url, timeout=15) as r:
                    data = json.loads(r.read())
            except Exception as e:
                return [{"type": "text", "text": f"Hotel search failed: {e}"}]
            payload = data.get("data") if isinstance(data, dict) else None
            arr = payload.get("hotels") if isinstance(payload, dict) else (
                payload if isinstance(payload, list) else []
            )
            arr = arr if isinstance(arr, list) else []
            limit = max(1, min(30, int(args.get("limit", 10))))
            arr = arr[:limit]
            summary = f"Found {len(arr)} hotels in {hit['name']} ({ci} → {co}, {hit['currency']}):"
            lines = [summary]
            for h in arr[:10]:
                if not isinstance(h, dict):
                    continue
                name = h.get("name") or h.get("hotelName") or "Hotel"
                stars = h.get("starRating") or h.get("stars") or "?"
                # Pricing in platform shape lives under packages/lowestPrice/totalPrice
                price = h.get("lowestPrice") or h.get("totalPrice") or h.get("price")
                if isinstance(h.get("packages"), list) and h["packages"]:
                    p0 = h["packages"][0]
                    if isinstance(p0, dict):
                        price = price or p0.get("totalPrice") or p0.get("price")
                lines.append(f"• {name} — {stars}★" + (f" — {hit['currency']} {price}" if price else ""))
            iid = new_iid()
            _persist_intent(iid, args.get("partner_key") or "mcp", "mcp", hit["name"], campaign="search")
            deeplink = build_deeplink(iid, hit["name"], args.get("partner_key") or "mcp", "mcp", campaign="search")
            lines.append("")
            lines.append(f"To book: {deeplink}")
            return [{"type": "text", "text": "\n".join(lines)}]
        if name == "impt_create_intent":
            dest = args.get("destination", "")
            key = args.get("partner_key") or "swarm-mcp"
            iid = new_iid()
            nice = _persist_intent(iid, key, "mcp", dest, campaign="mcp")
            url = build_deeplink(iid, nice, key, "mcp", campaign="mcp")
            return [{"type": "text",
                     "text": f"Intent created.\nIntent ID: {iid}\nDestination: {nice}\nDeeplink: {url}\n\nThe user opens this URL to book. €5 free + 5% Goodness back + 1 tonne CO₂ offset."}]
        if name == "impt_get_quote":
            iid = args.get("intent_id", "")
            if not iid.startswith("iid_"):
                return [{"type": "text", "text": "Invalid intent_id (expected iid_*)."}]
            with db() as c:
                row = c.execute("SELECT * FROM intents WHERE iid=?", (iid,)).fetchone()
            if not row:
                return [{"type": "text", "text": f"Intent {iid} not found."}]
            rec = dict(row)
            url = build_deeplink(iid, rec["destination"], rec["key"], rec["channel"],
                                 campaign=rec.get("campaign") or "oss")
            return [{"type": "text", "text":
                     f"Intent {iid}\nDestination: {rec['destination']}\nStatus: {rec['status']}\nChannel: {rec['channel']}\nDeeplink: {url}"}]
        if name == "impt_get_deeplink":
            dest = args.get("destination", "")
            key = args.get("partner_key") or "swarm-mcp"
            url = build_deeplink(new_iid(), dest, key, "mcp", campaign="mcp")
            return [{"type": "text", "text": f"Deeplink: {url}"}]
        return [{"type": "text", "text": f"Unknown tool: {name}"}]
    except Exception as e:
        return [{"type": "text", "text": f"Tool error: {e}"}]


@app.post("/api/mcp/http")
async def mcp_http(request: Request):
    """MCP Streamable HTTP transport (single endpoint, JSON-RPC 2.0)."""
    try:
        msg = await request.json()
    except Exception:
        return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32700, "message": "parse error"}, "id": None}, status_code=400)
    method = msg.get("method", "")
    rpc_id = msg.get("id")
    params = msg.get("params") or {}
    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": rpc_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "impt-swarm-widget", "version": "0.2.0"},
                "instructions": "IMPT booking adapter. Use impt_search_hotels then impt_create_intent. Always pass a CITY (never a country). Currency is destination-driven.",
            }
        }
    if method == "notifications/initialized":
        return Response(status_code=204)
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": MCP_TOOLS}}
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}
        content = _mcp_tool_call(name, args)
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"content": content, "isError": False}}
    return {"jsonrpc": "2.0", "id": rpc_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}}


@app.get("/api/mcp/info")
def mcp_info():
    """Human-readable MCP server info — pasteable into Claude Desktop config."""
    return {
        "name": "impt-swarm-widget",
        "version": "0.2.0",
        "transport": "http",
        "endpoint": f"{PUBLIC_BASE}/api/mcp/http",
        "tools": [t["name"] for t in MCP_TOOLS],
        "claude_desktop_config": {
            "mcpServers": {
                "impt": {"url": f"{PUBLIC_BASE}/api/mcp/http"}
            }
        },
        "claude_code_install": f"claude mcp add impt --transport http --url {PUBLIC_BASE}/api/mcp/http",
    }


# ── Telegram bot webhook ────────────────────────────────────────────
def tg_send(method: str, payload: dict):
    if not TG_BOT_TOKEN:
        return None
    try:
        req = _urlreq.Request(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/{method}",
            data=json.dumps(payload).encode(),
            headers={"content-type": "application/json"},
        )
        with _urlreq.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[tg_send] {method} failed: {e}", flush=True)
        return None


def tg_reply_city_picker(chat_id: int, greet: bool = True):
    top = CITIES[:12]
    rows = []
    for i in range(0, len(top), 3):
        rows.append([{"text": c["name"], "callback_data": f"c:{c['name']}"} for c in top[i:i + 3]])
    text = (
        "🌱 *IMPT — book hotels with conscience*\n\n"
        "€5 free credit · 5% Goodness back · 1 tonne CO₂ offset per booking.\n\n"
        "Pick a city or type one:"
    ) if greet else "Pick a city or type one:"
    tg_send("sendMessage", {
        "chat_id": chat_id, "text": text, "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": rows}
    })


# TG-BOT-AGENT 2026-05-13: Mike's verified IMPT Swarm partner key. Any booking
# originating from Telegram (Rambo_Marc2_bot) attributes commission to Mike.
# Override via env: TG_BOT_DEFAULT_PARTNER_KEY=p_otherkey.
TG_BOT_DEFAULT_PARTNER_KEY = _os.environ.get("TG_BOT_DEFAULT_PARTNER_KEY", "p_xhmn1nryyku")


def tg_reply_book_cta(chat_id: int, city: str, key: str = None):
    # TG-BOT-AGENT 2026-05-13: default to Mike's IMPT Swarm partner key.
    if not key or key == "swarm-public":
        key = TG_BOT_DEFAULT_PARTNER_KEY
    iid = new_iid()
    nice = _persist_intent(iid, key, "tg", city, campaign="swarm-tg")
    # TG-BOT-AGENT 2026-05-13: build the TG-channel deeplink directly so the
    # URL includes BOTH partner_key=<key> (for Henry's booking-page attribution
    # when wired) AND the swarm-tg UTM chain the brief asked for. Shared
    # build_deeplink() is left untouched (other channels still use it).
    hit = find_city(nice)
    p = {}
    if hit:
        p["destination"] = hit["name"]
        p["locationName"] = hit["name"]
        p["tl"] = hit["country"].lower()
        p["gl"] = hit["country"].lower()
    elif nice:
        p["destination"] = nice
        p["locationName"] = nice
    p["partner_key"] = key
    p["utm_source"] = "telegram"
    p["utm_medium"] = "bot"
    p["utm_campaign"] = "swarm-tg"
    p["utm_content"] = nice or city
    p["iid"] = iid
    url = f"{LANDER}?{_urlparse.urlencode(p)}"
    hit = find_city(nice)
    ccy = (hit or {}).get("currency", "USD")
    tg_send("sendMessage", {
        "chat_id": chat_id,
        "text": f"*{nice}* — {ccy} prices, free cancellation on most hotels, 1 tonne CO₂ offset per booking (we pay).\n\nTap to see hotels and reserve. €5 free credit applied at checkout.",
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "reply_markup": {"inline_keyboard": [
            [{"text": f"🔎 Find hotels in {nice} →", "url": url}],
            [{"text": "↩ Pick another city", "callback_data": "restart"}],
        ]},
    })


def tg_reply_help(chat_id: int):
    """Mike-only help. Lists every control command."""
    tg_send("sendMessage", {
        "chat_id": chat_id,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "text": (
            "*Rambo — Mike's IMPT control interface*\n"
            "Routes commands through Laura. You are whitelisted.\n\n"
            "*Status*\n"
            "/status — brain LIVE-STATE summary\n"
            "/digest — fire Laura's digest email now (don't wait for 07:00 UTC)\n\n"
            "*Pipeline*\n"
            "/bookings — today's bookings (Stripe + Mongo)\n"
            "/leads — last 24h leads (swarm_widget.db.leads)\n\n"
            "*Doorways*\n"
            "/eco <country> — URL of /eco-hotels/<country>/ if shipped\n\n"
            "*Laura control*\n"
            "/pause — pause Laura's autonomous shipping\n"
            "/resume — resume Laura's autonomous shipping\n"
            "/decision <letter> <GO|HOLD> — answer a queued Mike-decision\n\n"
            "Free-text → routed to Laura (Anthropic) for thoughtful reply.\n"
            "_Public users see nothing. Only whitelisted chat_ids get a response._"
        )
    })


# ── Rambo Mike-control command handlers ─────────────────────────────
LAURA_PAUSE_FLAG = _os.environ.get("LAURA_PAUSE_FLAG", "/home/mike/impt-chief-of-staff/state/laura_paused.flag")
LAURA_DECISIONS_FILE = _os.environ.get("LAURA_DECISIONS_FILE", "/home/mike/OPEN_DECISIONS.md")
ECO_HOTELS_BASE = "https://impthotels.com/eco-hotels"


def _safe_tail(path: str, n: int = 30) -> str:
    try:
        with open(path) as fh:
            lines = fh.read().splitlines()
        return "\n".join(lines[-n:])
    except Exception as e:
        return f"(error reading {path}: {e})"


def _rambo_cmd_status(chat_id: int):
    bits = []
    try:
        home = "/home/mike/operational-brain/00-INDEX/HOME.md"
        if _os.path.exists(home):
            with open(home) as fh:
                txt = fh.read()
            today_block = []
            in_today = False
            for ln in txt.splitlines():
                if ln.strip().startswith("## Today"):
                    in_today = True
                    continue
                if in_today and ln.strip().startswith("## "):
                    break
                if in_today and ln.strip().startswith("- "):
                    today_block.append(ln.strip()[:160])
            if today_block:
                bits.append("*Today (from brain):*\n" + "\n".join(today_block[:8]))
    except Exception as e:
        bits.append(f"(brain HOME read failed: {e})")
    try:
        paused = _os.path.exists(LAURA_PAUSE_FLAG)
        bits.append(f"\n*Laura shipping:* {'PAUSED' if paused else 'RUNNING'}")
    except Exception:
        pass
    tg_send("sendMessage", {
        "chat_id": chat_id, "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "text": ("\n".join(bits) or "No status available.")[:3800],
    })


def _rambo_cmd_bookings(chat_id: int):
    """Show today's bookings from the conversion watcher state."""
    try:
        state_path = "/home/mike/impt-chief-of-staff/state/conversion_watcher.json"
        if not _os.path.exists(state_path):
            tg_send("sendMessage", {"chat_id": chat_id, "text": "Conversion watcher state not found."})
            return
        with open(state_path) as fh:
            state = json.load(fh)
        seen = state.get("seen_ids", {}) if isinstance(state, dict) else {}
        last_run = state.get("last_run_iso", "(unknown)")
        counts = {k: len(v) if isinstance(v, list) else 0 for k, v in seen.items()}
        text = "*Bookings — conversion watcher state*\n\n"
        text += f"Last run: `{last_run}`\n\n"
        text += "Tracked-event counts per source (rolling window):\n"
        for src, n in counts.items():
            text += f"  • `{src}`: {n}\n"
        log_path = "/home/mike/impt-chief-of-staff/logs/conversion_watcher.log"
        if _os.path.exists(log_path):
            tail = _safe_tail(log_path, 15)
            text += f"\n*Recent log tail:*\n```\n{tail[-1500:]}\n```"
        tg_send("sendMessage", {"chat_id": chat_id, "parse_mode": "Markdown", "text": text[:3800]})
    except Exception as e:
        tg_send("sendMessage", {"chat_id": chat_id, "text": f"bookings error: {e}"})


def _rambo_cmd_leads(chat_id: int):
    try:
        cutoff = int(time.time()) - 86400
        rows = []
        with db() as c:
            cur = c.execute(
                "SELECT purpose,email,country,created_at FROM leads "
                "WHERE created_at >= ? AND is_test=0 ORDER BY created_at DESC LIMIT 30",
                (cutoff,),
            )
            for r in cur.fetchall():
                rows.append(r)
        if not rows:
            tg_send("sendMessage", {"chat_id": chat_id, "text": "No leads in last 24h."})
            return
        text = f"*Leads — last 24h* ({len(rows)})\n\n"
        for r in rows:
            try:
                purpose = r["purpose"]; email = r["email"]; country = r["country"] or "?"
                created = r["created_at"]
            except Exception:
                purpose, email, country, created = r[0], r[1], r[2] or "?", r[3]
            text += f"• `{purpose}` · {email} · {country} · {int((time.time()-created)/60)}m ago\n"
        tg_send("sendMessage", {"chat_id": chat_id, "parse_mode": "Markdown", "text": text[:3800]})
    except Exception as e:
        tg_send("sendMessage", {"chat_id": chat_id, "text": f"leads error: {e}"})


def _rambo_cmd_eco(chat_id: int, country_arg: str):
    if not country_arg:
        tg_send("sendMessage", {"chat_id": chat_id, "text": "Usage: /eco <country>"})
        return
    slug = re.sub(r"[^a-z0-9]+", "-", country_arg.strip().lower()).strip("-")
    candidates = [
        f"/var/www/impthotels.com/eco-hotels/{slug}/index.html",
        f"/home/mike/sites/impthotels-com/eco-hotels/{slug}/index.html",
    ]
    found = None
    for p in candidates:
        if _os.path.exists(p):
            found = p
            break
    if found:
        tg_send("sendMessage", {
            "chat_id": chat_id, "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "text": f"*{country_arg.title()}* — eco-hotels page LIVE\n{ECO_HOTELS_BASE}/{slug}/\n_(source: `{found}`)_",
        })
    else:
        tg_send("sendMessage", {
            "chat_id": chat_id, "text": f"{country_arg}: /eco-hotels/{slug}/ not yet built.",
        })


def _rambo_cmd_pause(chat_id: int):
    try:
        _os.makedirs(_os.path.dirname(LAURA_PAUSE_FLAG), exist_ok=True)
        with open(LAURA_PAUSE_FLAG, "w") as fh:
            fh.write(f"paused by rambo (chat_id={chat_id}) at {int(time.time())}\n")
        tg_send("sendMessage", {"chat_id": chat_id, "text": "Laura PAUSED. /resume to restart."})
    except Exception as e:
        tg_send("sendMessage", {"chat_id": chat_id, "text": f"pause error: {e}"})


def _rambo_cmd_resume(chat_id: int):
    try:
        if _os.path.exists(LAURA_PAUSE_FLAG):
            _os.remove(LAURA_PAUSE_FLAG)
        tg_send("sendMessage", {"chat_id": chat_id, "text": "Laura RESUMED."})
    except Exception as e:
        tg_send("sendMessage", {"chat_id": chat_id, "text": f"resume error: {e}"})


def _rambo_cmd_decision(chat_id: int, args: str):
    if not args:
        tg_send("sendMessage", {"chat_id": chat_id, "text": "Usage: /decision <letter> <GO|HOLD>"})
        return
    try:
        _os.makedirs("/home/mike/impt-chief-of-staff/state", exist_ok=True)
        with open("/home/mike/impt-chief-of-staff/state/mike_decisions.log", "a") as fh:
            fh.write(f"{int(time.time())}\t{chat_id}\t{args}\n")
        tg_send("sendMessage", {
            "chat_id": chat_id, "parse_mode": "Markdown",
            "text": f"Decision logged: `{args}`\nLaura will pick this up on next cron tick.",
        })
    except Exception as e:
        tg_send("sendMessage", {"chat_id": chat_id, "text": f"decision error: {e}"})


def _rambo_cmd_digest(chat_id: int):
    try:
        _os.makedirs("/home/mike/impt-chief-of-staff/state", exist_ok=True)
        with open("/home/mike/impt-chief-of-staff/state/digest_request.flag", "w") as fh:
            fh.write(f"{int(time.time())}\trequested by chat_id={chat_id}\n")
        tg_send("sendMessage", {"chat_id": chat_id, "text": "Digest requested — Laura will fire on next tick."})
    except Exception as e:
        tg_send("sendMessage", {"chat_id": chat_id, "text": f"digest error: {e}"})


def _rambo_freetext_anthropic(chat_id: int, text: str):
    """Whitelisted free-text → Anthropic (Laura system prompt). Best-effort."""
    api_key = _os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        tg_send("sendMessage", {
            "chat_id": chat_id,
            "text": "(free-text reply unavailable — ANTHROPIC_API_KEY not set in bot env)",
        })
        return
    try:
        body = {
            "model": "claude-opus-4-7",
            "max_tokens": 600,
            "system": (
                "You are Laura, Mike English's chief of staff at IMPT.io. "
                "You are talking to Mike directly via his private Telegram interface (Rambo). "
                "Be terse, factual, action-oriented. No hedging. "
                "If Mike asks for a status, give him numbers. If he gives a directive, confirm it "
                "and note that the actual execution happens via Laura's cron / dispatch pipeline, "
                "not via this chat."
            ),
            "messages": [{"role": "user", "content": text}],
        }
        req = _urlreq.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode(),
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with _urlreq.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
        reply = ""
        for blk in resp.get("content", []):
            if blk.get("type") == "text":
                reply += blk.get("text", "")
        reply = (reply or "(empty reply)").strip()[:3800]
        tg_send("sendMessage", {"chat_id": chat_id, "text": reply})
    except Exception as e:
        tg_send("sendMessage", {"chat_id": chat_id, "text": f"(anthropic error: {e})"})


@app.post("/api/tg/webhook")
async def tg_webhook(request: Request):
    """Rambo — Mike's PRIVATE control interface.

    Default for ANY non-whitelisted sender = SILENT (just log to bot_events).
    No "this bot is for X", no AI reply, no city-picker. The bot is internal.
    Pivot 2026-05-10: Mike's correction "rambo should not respond unless mike
    asks him and you control him based on that".

    The ONLY exception is `/whitelist <secret>` which any sender can use to
    register their chat_id as the bot owner (one-time, requires TG_WHITELIST_SECRET).
    """
    if TG_WEBHOOK_SECRET:
        got = request.headers.get("x-telegram-bot-api-secret-token", "")
        if got != TG_WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="forbidden")
    if not TG_BOT_TOKEN:
        return JSONResponse({"error": "tg_bot_token_unset"}, status_code=503)
    try:
        update = await request.json()
    except Exception:
        return Response("ok")

    # Always log every incoming update (even silent ones) so we can audit
    # public traffic without responding.
    _from = (update.get("message") or update.get("callback_query") or {}).get("from", {}) or {}
    _chat = (update.get("message") or update.get("callback_query", {}).get("message") or {}).get("chat", {}) or {}
    raw_chat_id = _chat.get("id") or _from.get("id")
    chat_id_str = str(raw_chat_id) if raw_chat_id is not None else ""
    with db() as c:
        c.execute(
            "INSERT INTO bot_events(channel,chat_id,intent_iid,payload,ts) VALUES (?,?,?,?,?)",
            ("tg", chat_id_str, None, json.dumps(update)[:4000], int(time.time()))
        )

    msg = update.get("message")
    cq = update.get("callback_query")

    # Callback queries (button taps) — only whitelisted users get a response.
    if cq:
        if chat_id_str not in TG_WHITELIST:
            try:
                tg_send("answerCallbackQuery", {"callback_query_id": cq["id"]})
            except Exception:
                pass
            return Response("ok")
        tg_send("answerCallbackQuery", {"callback_query_id": cq["id"]})
        # Mike-only callbacks: currently none wired. Reserved for future.
        return Response("ok")

    if not msg:
        return Response("ok")
    text = (msg.get("text") or "").strip()

    # ── /whitelist <secret> — open to anyone (one-time self-register) ───
    if text.startswith("/whitelist") or text.startswith("/whitelist@"):
        head = text.split(None, 1)
        secret = head[1].strip() if len(head) > 1 else ""
        if not TG_WHITELIST_SECRET:
            # Don't leak that the secret is unset — silent.
            return Response("ok")
        if secret and secret == TG_WHITELIST_SECRET and chat_id_str:
            _persist_whitelist_chatid(chat_id_str)
            tg_send("sendMessage", {
                "chat_id": raw_chat_id,
                "parse_mode": "Markdown",
                "text": (
                    "✅ Whitelisted. You are now Rambo's owner.\n\n"
                    f"chat_id: `{chat_id_str}`\n"
                    "Type /help for the command list."
                ),
            })
        # Wrong secret or missing → silent.
        return Response("ok")

    # ── Whitelist gate ─────────────────────────────────────────────────
    if chat_id_str not in TG_WHITELIST:
        # Mike's directive: default = SILENT. Logged above for audit.
        # Optional one-line polite redirect — disabled by default (truly silent).
        # To enable, set TG_PUBLIC_REDIRECT=1 in .env.
        if _os.environ.get("TG_PUBLIC_REDIRECT", "0") == "1":
            tg_send("sendMessage", {
                "chat_id": raw_chat_id,
                "text": "This bot is internal to IMPT — please email laura@impt.io.",
            })
        return Response("ok")

    # ── Whitelisted: Mike's control surface ────────────────────────────
    chat_id = raw_chat_id
    if text.startswith("/"):
        head = text.split(" ", 1)
        cmd = head[0][1:].split("@")[0].lower()
        args = head[1].strip() if len(head) > 1 else ""
        # TG-BOT-AGENT 2026-05-13: parse Telegram /start <payload>. Payload format
        # from the swarm.impt.io/tg deep-link is "<city>-<partner_key>" (e.g.
        # "Dublin-p_xhmn1nryyku"). If a partner_key prefix (p_…) is present, use
        # it for the booking deeplink so attribution sticks. Otherwise fall
        # back to TG_BOT_DEFAULT_PARTNER_KEY.
        if cmd == "start" and args:
            city = args
            partner_key = TG_BOT_DEFAULT_PARTNER_KEY
            if "-p_" in args:
                city, _, tail = args.rpartition("-p_")
                partner_key = "p_" + tail
            city = (city or "Dublin").strip() or "Dublin"
            tg_reply_book_cta(chat_id, city, key=partner_key)
            return Response("ok")
        if cmd in ("start", "help"):
            tg_reply_help(chat_id)
        elif cmd == "status":
            _rambo_cmd_status(chat_id)
        elif cmd == "bookings":
            _rambo_cmd_bookings(chat_id)
        elif cmd == "leads":
            _rambo_cmd_leads(chat_id)
        elif cmd == "eco":
            _rambo_cmd_eco(chat_id, args)
        elif cmd == "pause":
            _rambo_cmd_pause(chat_id)
        elif cmd == "resume":
            _rambo_cmd_resume(chat_id)
        elif cmd == "decision":
            _rambo_cmd_decision(chat_id, args)
        elif cmd == "digest":
            _rambo_cmd_digest(chat_id)
        else:
            tg_reply_help(chat_id)
        return Response("ok")
    if text:
        # Free-text from Mike → Anthropic (Laura system prompt).
        _rambo_freetext_anthropic(chat_id, text)
    return Response("ok")


# ── WhatsApp Cloud API webhook ──────────────────────────────────────
GRAPH = "https://graph.facebook.com/v19.0"


def wa_post(path: str, body: dict):
    if not WA_TOKEN or not WA_PHONE_NUMBER_ID:
        return None
    try:
        req = _urlreq.Request(
            f"{GRAPH}/{path}",
            data=json.dumps(body).encode(),
            headers={"authorization": f"Bearer {WA_TOKEN}", "content-type": "application/json"},
        )
        with _urlreq.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[wa] post failed: {e}", flush=True)
        return None


@app.get("/api/whatsapp/webhook")
def wa_verify(request: Request):
    qs = dict(request.query_params)
    if (qs.get("hub.mode") == "subscribe"
        and WA_VERIFY_TOKEN
        and qs.get("hub.verify_token") == WA_VERIFY_TOKEN
        and qs.get("hub.challenge")):
        return PlainTextResponse(qs["hub.challenge"])
    raise HTTPException(status_code=403, detail="forbidden")


@app.post("/api/whatsapp/webhook")
async def wa_webhook(request: Request):
    if not WA_TOKEN or not WA_PHONE_NUMBER_ID:
        return {"ok": True, "note": "wa_not_provisioned"}
    try:
        body = await request.json()
    except Exception:
        return Response("ok")
    with db() as c:
        c.execute(
            "INSERT INTO bot_events(channel,chat_id,intent_iid,payload,ts) VALUES (?,?,?,?,?)",
            ("wa", "", None, json.dumps(body)[:4000], int(time.time()))
        )
    entries = body.get("entry") or []
    for ent in entries:
        for change in (ent.get("changes") or []):
            v = (change or {}).get("value") or {}
            for m in (v.get("messages") or []):
                frm = m.get("from")
                txt = ""
                if m.get("type") == "text":
                    txt = (m.get("text") or {}).get("body", "").strip()
                elif m.get("type") == "interactive":
                    inter = m.get("interactive") or {}
                    txt = (inter.get("button_reply") or inter.get("list_reply") or {}).get("title", "").strip()
                if not txt:
                    wa_post(f"{WA_PHONE_NUMBER_ID}/messages", {
                        "messaging_product": "whatsapp", "to": frm, "type": "text",
                        "text": {"body": "Hi 👋 — type a city (e.g. \"Dublin\") and I'll send you a one-tap booking link. €5 free + 5% Goodness back."}
                    })
                    continue
                cleaned = re.sub(r"^(book|find|hotel|hotels|stay)\s+", "", txt, flags=re.IGNORECASE).strip() or txt
                iid = new_iid()
                nice = _persist_intent(iid, "swarm-public", "wa", cleaned, campaign="bot")
                url = build_deeplink(iid, nice, "swarm-public", "wa", campaign="bot")
                hit = find_city(nice)
                ccy = (hit or {}).get("currency", "USD")
                wa_post(f"{WA_PHONE_NUMBER_ID}/messages", {
                    "messaging_product": "whatsapp", "to": frm, "type": "interactive",
                    "interactive": {
                        "type": "cta_url",
                        "body": {"text": f"*{nice}* — book a hotel in {ccy}.\n€5 free + 5% Goodness back · 1 tonne CO₂ offset per booking (we pay)."},
                        "action": {"name": "cta_url", "parameters": {"display_text": f"Find hotels in {nice}", "url": url}},
                    }
                })
    return Response("ok")


# ── Facebook Messenger Platform webhook ─────────────────────────────
def fb_send(recipient_id: str, payload: dict):
    if not FB_PAGE_ACCESS_TOKEN:
        return None
    try:
        req = _urlreq.Request(
            f"{GRAPH}/me/messages?access_token={_urlparse.quote(FB_PAGE_ACCESS_TOKEN)}",
            data=json.dumps({"recipient": {"id": recipient_id}, "messaging_type": "RESPONSE", **payload}).encode(),
            headers={"content-type": "application/json"},
        )
        with _urlreq.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[fb] send failed: {e}", flush=True)
        return None


def fb_quick_reply_picker(to: str):
    cities = ["Dublin", "London", "Paris", "Barcelona", "Rome", "New York", "Tokyo", "Dubai"]
    fb_send(to, {"message": {
        "text": "Pick a city — or type one:",
        "quick_replies": [{"content_type": "text", "title": c, "payload": f"CITY:{c}"} for c in cities]
    }})


def fb_card_for_city(to: str, city: str, key: str = "swarm-public"):
    iid = new_iid()
    nice = _persist_intent(iid, key, "fb", city, campaign="messenger")
    url = build_deeplink(iid, nice, key, "fb", campaign="messenger")
    fb_send(to, {"message": {"attachment": {
        "type": "template",
        "payload": {"template_type": "generic", "elements": [{
            "title": f"{nice} — find a green hotel",
            "subtitle": "€5 free credit · 5% Goodness back · 1 tonne CO₂ offset per booking (we pay).",
            "buttons": [
                {"type": "web_url", "url": url, "title": f"Find hotels in {nice} →"},
                {"type": "postback", "title": "Pick another city", "payload": "RESTART"},
            ]
        }]}
    }}})


@app.get("/api/fb/webhook")
def fb_verify(request: Request):
    qs = dict(request.query_params)
    if (qs.get("hub.mode") == "subscribe"
        and FB_VERIFY_TOKEN
        and qs.get("hub.verify_token") == FB_VERIFY_TOKEN
        and qs.get("hub.challenge")):
        return PlainTextResponse(qs["hub.challenge"])
    raise HTTPException(status_code=403, detail="forbidden")


@app.post("/api/fb/webhook")
async def fb_webhook(request: Request):
    if not FB_PAGE_ACCESS_TOKEN:
        return {"ok": True, "note": "fb_not_provisioned"}
    try:
        body = await request.json()
    except Exception:
        return Response("ok")
    with db() as c:
        c.execute(
            "INSERT INTO bot_events(channel,chat_id,intent_iid,payload,ts) VALUES (?,?,?,?,?)",
            ("fb", "", None, json.dumps(body)[:4000], int(time.time()))
        )
    for ent in (body.get("entry") or []):
        for ev in (ent.get("messaging") or []):
            sender = (ev.get("sender") or {}).get("id")
            if not sender:
                continue
            if ev.get("postback"):
                p = ev["postback"].get("payload", "")
                if p == "RESTART":
                    fb_quick_reply_picker(sender)
                elif p.startswith("CITY:"):
                    fb_card_for_city(sender, p[5:])
                continue
            qr = (ev.get("message") or {}).get("quick_reply", {}).get("payload", "")
            if qr.startswith("CITY:"):
                fb_card_for_city(sender, qr[5:])
                continue
            txt = ((ev.get("message") or {}).get("text") or "").strip()
            if not txt:
                fb_quick_reply_picker(sender)
                continue
            cleaned = re.sub(r"^(book|find|hotel|hotels|stay)\s+", "", txt, flags=re.IGNORECASE).strip() or txt
            fb_card_for_city(sender, cleaned)
    return Response("ok")


# ── /api/lead/capture — universal IMPT lead-capture form (2026-05-10) ──
# Mike binding: every customer-engagement surface MUST have a working capture
# form. Calendly mike-impt is broken; this is the fix. 6 purposes share one
# mechanic: franchise / partner / b2b / voucher / ai / goodness / general.

LEAD_PURPOSES = {"franchise", "partner", "b2b", "country", "voucher", "ai", "goodness", "general",
                 "mtb", "surf", "walks", "golf", "yoga", "ski", "pets"}  # widget vertical landing-page leads (2026-06-14)
LEAD_TO_RECIPIENTS = ["mike@impt.io", "cto-office@impt.io", "info@impt.io"]  # LOCKED mike+cto-office+info ONLY (Mike 2026-06-12)
LEAD_FROM_ADDRESS = "laura@impt.io"
LEAD_TEST_PATTERNS = [
    "@example.com", "@example.org", "@test.com",
    "+test@", "+qa@", "+probe@", "+scan@",
    "qa@", "scan@", "probe@",
    "e2e-test", "e2e+", "qa-test", "qa-",
    "sweep-", "chief-of-staff-probe",
]


def init_leads_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          purpose TEXT NOT NULL,
          email TEXT NOT NULL,
          name TEXT,
          country TEXT,
          message TEXT,
          create_account INTEGER NOT NULL DEFAULT 0,
          partner_key TEXT,
          source_url TEXT,
          utm_source TEXT,
          utm_medium TEXT,
          utm_campaign TEXT,
          utm_content TEXT,
          ip_hash TEXT,
          ua_hash TEXT,
          is_test INTEGER NOT NULL DEFAULT 0,
          notified_at INTEGER,
          created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
        CREATE INDEX IF NOT EXISTS idx_leads_purpose ON leads(purpose);
        CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);
        """)


def is_test_lead_email(email: str) -> bool:
    e = (email or "").lower()
    return any(m in e for m in LEAD_TEST_PATTERNS)


def lead_rate_limit_ok(ip_hash: str) -> bool:
    # 10 submits / IP / hour
    cutoff = int(time.time()) - 3600
    with db() as c:
        n = c.execute(
            "SELECT COUNT(*) AS n FROM leads WHERE ip_hash=? AND created_at > ?",
            (ip_hash, cutoff)
        ).fetchone()["n"]
    return n < 10


def send_lead_email(lead_row: dict) -> bool:
    """Email mike+julia from laura@ immediately on lead capture."""
    purpose = lead_row.get("purpose", "general")
    email = lead_row.get("email", "")
    country = lead_row.get("country", "") or "no-country"
    name = lead_row.get("name", "") or ""
    message = lead_row.get("message", "") or ""
    create_account = bool(lead_row.get("create_account"))
    partner_key = lead_row.get("partner_key", "") or ""
    source_url = lead_row.get("source_url", "") or ""
    utm_source = lead_row.get("utm_source", "") or ""
    utm_medium = lead_row.get("utm_medium", "") or ""
    utm_campaign = lead_row.get("utm_campaign", "") or ""

    purpose_emoji = {
        "franchise": "🏷️", "partner": "💼", "b2b": "🏢", "country": "🌍",
        "voucher": "🎁", "ai": "🤖", "goodness": "🌱", "general": "📥",
    }.get(purpose, "📥")
    subject = f"[IMPT 📥] Lead · {purpose} · {email} · {country}"

    body_lines = [
        f"A new lead just landed via swarm.impt.io/connect/{purpose}.",
        "",
        f"Purpose:    {purpose} {purpose_emoji}",
        f"Email:      {email}",
        f"Name:       {name}",
        f"Country:    {country}",
        f"Source URL: {source_url}",
        f"UTM:        source={utm_source}, medium={utm_medium}, campaign={utm_campaign}",
        f"Account:    {'YES — partner key issued: ' + partner_key if create_account and partner_key else 'no'}",
        "",
        "Message:",
        message or "(none)",
        "",
        "Action: reply within 1 hour. Customer expects same-day touch.",
        "",
        "— Laura",
    ]
    body = "\n".join(body_lines)

    try:
        from email.mime.text import MIMEText
        from email.utils import formataddr
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_file(
            GMAIL_CREDS, scopes=["https://www.googleapis.com/auth/gmail.send"]
        ).with_subject(LEAD_FROM_ADDRESS)
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        msg = MIMEText(body)
        recips = list(LEAD_TO_RECIPIENTS)
        if purpose in ("country", "franchise", "b2b"):
            recips = sorted(set(recips + TEAM_NOTIFY))  # whole team on country-ownership signups
        msg["to"] = ", ".join(recips)
        msg["from"] = formataddr(("Laura @ IMPT", LEAD_FROM_ADDRESS))
        msg["reply-to"] = email
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print(f"[lead-capture] email sent: id={result.get('id')} purpose={purpose} email={email}", flush=True)
        return True
    except Exception as e:
        print(f"[lead-capture] send_lead_email FAILED: {e}", flush=True)
        return False


class LeadReq(BaseModel):
    email: EmailStr
    purpose: str = Field("general", max_length=20)
    name: Optional[str] = Field(None, max_length=120)
    country: Optional[str] = Field(None, max_length=80)
    message: Optional[str] = Field(None, max_length=2000)
    create_account: Optional[bool] = False
    source_url: Optional[str] = Field(None, max_length=500)
    utm_source: Optional[str] = Field(None, max_length=120)
    utm_medium: Optional[str] = Field(None, max_length=120)
    utm_campaign: Optional[str] = Field(None, max_length=120)
    utm_content: Optional[str] = Field(None, max_length=120)
    hp: Optional[str] = Field(None, max_length=200)  # honeypot — must be empty


# ── /api/lead/capture-form — urlencoded variant for STATIC (zero-JS) pages ──
# Tie-down frozen pages (impt.io/country-owner etc.) submit native HTML forms.
# Reuses lead_capture() verbatim, then 303-redirects back to the page (#thanks /
# #subscribed CSS :target banner). Redirect allowlist = impt.io only.
from fastapi import Form
from fastapi.responses import RedirectResponse

@app.post("/api/lead/capture-form")
def lead_capture_form(
    request: Request,
    email: str = Form(...),
    purpose: str = Form("general"),
    name: str = Form(None),
    country: str = Form(None),
    message: str = Form(None),
    hp: str = Form(None),
    redirect: str = Form("https://impt.io/"),
):
    if not (redirect.startswith("https://impt.io/") or redirect.startswith("https://www.impt.io/")):
        redirect = "https://impt.io/"
    try:
        body = LeadReq(email=email, purpose=purpose, name=name, country=country,
                       message=message, hp=hp, source_url=request.headers.get("referer"))
    except Exception:
        # invalid email etc. — bounce back without the success fragment
        return RedirectResponse(redirect.split("#")[0] + "#form-error", status_code=303)
    try:
        lead_capture(body, request)
    except HTTPException:
        return RedirectResponse(redirect.split("#")[0] + "#form-error", status_code=303)
    return RedirectResponse(redirect, status_code=303)


@app.post("/api/lead/capture")
def lead_capture(body: LeadReq, request: Request):
    ip = request.client.host if request.client else ""
    ip_h = hash_ip(ip)
    ua = request.headers.get("user-agent", "")
    ua_h = hash_ua(ua)

    purpose = (body.purpose or "general").lower().strip()
    if purpose not in LEAD_PURPOSES:
        purpose = "general"

    # Honeypot — silent reject (return fake success).
    if body.hp:
        audit("lead.honeypot_trip", subject=body.email, detail={"purpose": purpose}, ip_hash=ip_h)
        return {"ok": True, "id": 0, "message": "thanks"}

    # Email validity (also blocks disposable).
    if not is_valid_email(body.email):
        audit("lead.bad_email", subject=body.email, detail={"purpose": purpose}, ip_hash=ip_h)
        raise HTTPException(400, "email rejected (disposable or malformed)")

    # Rate limit per IP — 10/hr.
    if not lead_rate_limit_ok(ip_h):
        audit("lead.rate_limited", subject=body.email, detail={"purpose": purpose}, ip_hash=ip_h)
        raise HTTPException(429, "too many submissions, please try again later")

    is_test = is_test_lead_email(body.email)

    # Optional: create partner key (re-uses signup mechanic, no email-verify gate).
    partner_key = None
    if body.create_account and not is_test:
        try:
            partner_key = "p_" + secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:12].lower()
            api_token = secrets.token_urlsafe(32)
            verify_token = secrets.token_urlsafe(24)
            with db() as c:
                # Default to wise + email as payout target — they can update later via /partners/me.
                c.execute(
                    "INSERT INTO partners(key,email,name,payout_method,payout_target,created_at,status,api_token,verify_token,signup_ip_hash) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (partner_key, body.email, body.name or "", "wise", body.email,
                     int(time.time()), "pending_email", api_token, verify_token, ip_h)
                )
            audit("lead.partner_created", subject=partner_key, detail={"email": body.email, "purpose": purpose}, ip_hash=ip_h)
        except sqlite3.IntegrityError:
            # collision or duplicate email — non-fatal for the lead capture
            partner_key = None
        except Exception as e:
            print(f"[lead-capture] partner-create failed (non-fatal): {e}", flush=True)
            partner_key = None

    now = int(time.time())
    with db() as c:
        cur = c.execute(
            """INSERT INTO leads
               (purpose,email,name,country,message,create_account,partner_key,
                source_url,utm_source,utm_medium,utm_campaign,utm_content,
                ip_hash,ua_hash,is_test,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (purpose, body.email, body.name, body.country, body.message,
             1 if body.create_account else 0, partner_key,
             body.source_url, body.utm_source, body.utm_medium, body.utm_campaign, body.utm_content,
             ip_h, ua_h, 1 if is_test else 0, now)
        )
        lead_id = cur.lastrowid

    audit("lead.captured", subject=body.email,
          detail={"id": lead_id, "purpose": purpose, "is_test": is_test, "partner_key": partner_key},
          ip_hash=ip_h)

    # Email immediately (Mike binding R-HARD-14) — but suppress for test emails.
    notified = False
    if not is_test:
        notified = send_lead_email({
            "purpose": purpose, "email": body.email, "name": body.name,
            "country": body.country, "message": body.message,
            "create_account": body.create_account, "partner_key": partner_key,
            "source_url": body.source_url,
            "utm_source": body.utm_source, "utm_medium": body.utm_medium,
            "utm_campaign": body.utm_campaign,
        })
        if notified:
            with db() as c:
                c.execute("UPDATE leads SET notified_at=? WHERE id=?", (int(time.time()), lead_id))

    return {
        "ok": True,
        "id": lead_id,
        "purpose": purpose,
        "partner_key": partner_key,
        "message": "We've got it — Mike will get back to you within a few hours.",
    }


# ───────────────────────────────────────────────────────────────────────────
# Laura inbox real-time push (Option A, Mike binding 2026-05-10 R-HARD-21).
#
# Pub/Sub topic `projects/new-impt/topics/gmail-laura-watch` publishes when
# new mail lands in laura@impt.io. Pub/Sub push subscription POSTs here.
# We fetch new INBOX message IDs via history.list and forward to mike+julia
# within seconds. Cron-poll fallback at /5 still runs as belt-and-braces.
# ───────────────────────────────────────────────────────────────────────────
import sys as _sys
_sys.path.insert(0, "/home/mike/impt-chief-of-staff/bin")
try:
    import laura_inbox_core as _laura_core  # noqa: E402
except Exception as _e:
    _laura_core = None
    print(f"[laura-push] core import failed: {_e}", flush=True)

LAURA_PUSH_TOKEN = os.environ.get("LAURA_PUSH_TOKEN", "")  # optional shared-secret


@app.post("/api/laura/gmail-push")
async def laura_gmail_push(request: Request, token: Optional[str] = Query(None)):
    """Pub/Sub push endpoint. Pub/Sub will POST a JSON envelope:
       {message: {data: base64(json), messageId, publishTime}, subscription: "..."}.
    The data payload from Gmail is: {emailAddress, historyId}.
    """
    # Optional shared-secret in query string (matches Pub/Sub subscription URL).
    if LAURA_PUSH_TOKEN and token != LAURA_PUSH_TOKEN:
        raise HTTPException(401, "bad token")

    if _laura_core is None:
        raise HTTPException(503, "core not loaded")

    try:
        envelope = await request.json()
    except Exception:
        raise HTTPException(400, "bad json")

    data_b64 = ((envelope or {}).get("message") or {}).get("data") or ""
    if not data_b64:
        # Pub/Sub may send empty test messages — ack so it doesn't retry.
        return {"ok": True, "note": "empty envelope"}

    try:
        decoded = base64.urlsafe_b64decode(data_b64 + "==").decode("utf-8", errors="replace")
        payload = json.loads(decoded)
    except Exception as e:
        # Don't NACK on parse error — Pub/Sub would retry forever.
        print(f"[laura-push] decode failed: {e}", flush=True)
        return {"ok": False, "error": "decode"}

    history_id = str(payload.get("historyId") or "")
    if not history_id:
        return {"ok": False, "error": "no historyId"}

    # Use the stored historyId (from last watch.register or last push) as the
    # starting point — Gmail returns everything since that ID. If we don't have
    # one, the just-received historyId becomes the baseline (first event seen).
    ws = _laura_core.load_watch_state()
    start_history = str(ws.get("historyId") or history_id)

    try:
        result = _laura_core.process_history_since(start_history)
    except Exception as e:
        print(f"[laura-push] process failed: {e}", flush=True)
        result = {"ok": False, "error": str(e)}

    # Always 200 to ack the Pub/Sub message — otherwise it will redeliver and storm us.
    return {"ok": True, "history_received": history_id, "started_from": start_history, "result": result}


@app.get("/api/laura/health")
def laura_health():
    """Quick health check for the real-time pipeline."""
    if _laura_core is None:
        return {"ok": False, "core": False}
    ws = _laura_core.load_watch_state()
    st = _laura_core.load_state()
    expiry_ms = int(ws.get("expiration_ms") or 0)
    days_left = (expiry_ms/1000 - time.time()) / 86400 if expiry_ms else None
    return {
        "ok": True,
        "core": True,
        "watch_history_id": ws.get("historyId"),
        "watch_expires_ms": expiry_ms,
        "watch_days_left": round(days_left, 2) if days_left is not None else None,
        "last_push_unix": ws.get("last_push_unix"),
        "last_poll_unix": st.get("last_poll_unix"),
        "inbox_since_unix": st.get("since_unix"),
    }


init_db()
init_omnichannel_db()
init_leads_db()

# ── franchiseimpt.io lead-capture endpoints (R-HARD-18 dispatch 2026-05-12) ──
# Mounts /api/franchise-lead + /api/franchise-booked. DB: same swarm_widget.db,
# new table franchise_leads created on first import.
try:
    from franchise_endpoints import router as _franchise_router  # noqa: E402
    app.include_router(_franchise_router)
except Exception as _e:
    import sys as _sys
    print(f"[franchise] router mount FAILED: {_e}", file=_sys.stderr)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=2027)
