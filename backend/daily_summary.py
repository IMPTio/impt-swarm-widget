#!/home/mike/impt-swarm-oss-2026-05-05/backend/.venv/bin/python
"""
IMPT Swarm Widget — daily traffic summary.

Runs at 09:00 UTC daily via cron. Queries the SQLite DB for the prior 24h of
activity, formats a plain-text summary, emails it to mike@impt.io.

If nothing happened (zero events), still sends a quiet "all quiet" line so we
know the cron itself is alive.
"""
import base64
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.utils import formataddr

DB_PATH = os.environ.get("SWARM_WIDGET_DB", "/home/mike/impt-swarm-oss-2026-05-05/backend/swarm_widget.db")
GMAIL_CREDS = os.environ.get("SWARM_WIDGET_GMAIL_CREDS", "/home/mike/impt-management/credentials.json")
SENDER = "cto-office@impt.io"
FROM_NAME = "IMPT Swarm"
TO = "mike@impt.io"


def fetch():
    end = int(time.time())
    start = end - 24 * 3600
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row

    def q(sql, *args):
        return c.execute(sql, args).fetchall()

    new_signups = q(
        "SELECT key, email, status FROM partners WHERE created_at BETWEEN ? AND ? ORDER BY created_at",
        start, end
    )
    verified_today = q(
        "SELECT key, email FROM partners WHERE verified_at BETWEEN ? AND ? ORDER BY verified_at",
        start, end
    )
    events_by_type = q(
        "SELECT evt, COUNT(*) AS n FROM partner_events WHERE ts BETWEEN ? AND ? GROUP BY evt ORDER BY n DESC",
        start, end
    )
    top_dest = q(
        "SELECT dest, COUNT(*) AS n FROM partner_events WHERE ts BETWEEN ? AND ? AND evt='click' AND dest IS NOT NULL GROUP BY dest ORDER BY n DESC LIMIT 5",
        start, end
    )
    top_partners = q(
        """SELECT key, COUNT(*) AS clicks
           FROM partner_events WHERE ts BETWEEN ? AND ? AND evt='click'
           GROUP BY key ORDER BY clicks DESC LIMIT 5""",
        start, end
    )
    new_bookings = q(
        "SELECT partner_key, booking_id, base_value_cents, currency, accrual_eur_cents, status FROM partner_bookings WHERE booked_at BETWEEN ? AND ? ORDER BY booked_at DESC",
        start, end
    )
    accrual_today = q(
        "SELECT COALESCE(SUM(accrual_eur_cents),0) AS s FROM partner_bookings WHERE booked_at BETWEEN ? AND ?",
        start, end
    )[0]["s"]
    rate_limit_429s = q(
        "SELECT COUNT(*) AS n FROM partner_events WHERE ts BETWEEN ? AND ? AND evt='click_inactive'",
        start, end
    )[0]["n"]
    honeypot_trips = q(
        "SELECT COUNT(*) AS n FROM audit_log WHERE ts BETWEEN ? AND ? AND action='signup.honeypot_trip'",
        start, end
    )[0]["n"]
    bad_sigs = q(
        "SELECT COUNT(*) AS n FROM audit_log WHERE ts BETWEEN ? AND ? AND action='webhook.bad_auth'",
        start, end
    )[0]["n"]

    totals = {
        "all_partners": q("SELECT COUNT(*) AS n FROM partners")[0]["n"],
        "active_partners": q("SELECT COUNT(*) AS n FROM partners WHERE status='active'")[0]["n"],
        "all_bookings": q("SELECT COUNT(*) AS n FROM partner_bookings")[0]["n"],
        "all_accrual_eur_cents": q("SELECT COALESCE(SUM(accrual_eur_cents),0) AS s FROM partner_bookings")[0]["s"],
    }

    c.close()
    return {
        "today": today_str, "yday": yday_str,
        "new_signups": [dict(r) for r in new_signups],
        "verified_today": [dict(r) for r in verified_today],
        "events_by_type": [dict(r) for r in events_by_type],
        "top_dest": [dict(r) for r in top_dest],
        "top_partners": [dict(r) for r in top_partners],
        "new_bookings": [dict(r) for r in new_bookings],
        "accrual_today_eur_cents": accrual_today,
        "rate_limit_429s": rate_limit_429s,
        "honeypot_trips": honeypot_trips,
        "bad_sigs": bad_sigs,
        "totals": totals,
    }


def format_body(d):
    eur = lambda c: f"€{c/100:.2f}"
    lines = []
    lines.append(f"IMPT Swarm Widget — daily summary")
    lines.append(f"Window: 24h ending {d['today']} 09:00 UTC")
    lines.append("")

    # ── Activity summary
    e_total = sum(e["n"] for e in d["events_by_type"]) if d["events_by_type"] else 0
    lines.append(f"📊 ACTIVITY")
    lines.append(f"  Signups (new keys):   {len(d['new_signups'])}")
    lines.append(f"  Verified (activated): {len(d['verified_today'])}")
    lines.append(f"  Total events:         {e_total}")
    for e in d["events_by_type"]:
        lines.append(f"    · {e['evt']:<16} {e['n']}")
    lines.append(f"  Bookings logged:      {len(d['new_bookings'])}")
    lines.append(f"  Accrual today:        {eur(d['accrual_today_eur_cents'])}")
    lines.append("")

    if d["new_signups"]:
        lines.append("🆕 NEW SIGNUPS")
        for s in d["new_signups"]:
            lines.append(f"  · {s['key']}  {s['email']}  [{s['status']}]")
        lines.append("")

    if d["top_dest"]:
        lines.append("🌍 TOP DESTINATIONS (by clicks)")
        for t in d["top_dest"]:
            lines.append(f"  · {t['dest']:<24} {t['n']} clicks")
        lines.append("")

    if d["top_partners"]:
        lines.append("🥇 TOP PARTNERS (by clicks)")
        for p in d["top_partners"]:
            lines.append(f"  · {p['key']:<20} {p['clicks']} clicks")
        lines.append("")

    if d["new_bookings"]:
        lines.append("💰 NEW BOOKINGS")
        for b in d["new_bookings"]:
            lines.append(f"  · {b['booking_id']}  {b['partner_key']}  base={b['base_value_cents']/100:.2f} {b['currency']}  accrual={eur(b['accrual_eur_cents'])}  [{b['status']}]")
        lines.append("")

    # ── Security
    sec_alarms = d["rate_limit_429s"] + d["honeypot_trips"] + d["bad_sigs"]
    if sec_alarms:
        lines.append("🛡️  SECURITY EVENTS")
        if d["rate_limit_429s"]:
            lines.append(f"  · Inactive-key click attempts: {d['rate_limit_429s']}")
        if d["honeypot_trips"]:
            lines.append(f"  · Honeypot trips:              {d['honeypot_trips']}")
        if d["bad_sigs"]:
            lines.append(f"  · Bad webhook signatures:      {d['bad_sigs']}")
        lines.append("")

    # ── Lifetime totals
    t = d["totals"]
    lines.append("📈 LIFETIME")
    lines.append(f"  Partners total / active: {t['all_partners']} / {t['active_partners']}")
    lines.append(f"  Bookings total:          {t['all_bookings']}")
    lines.append(f"  Accrual total:           {eur(t['all_accrual_eur_cents'])}")
    lines.append("")

    if e_total == 0 and not d["new_signups"] and not d["new_bookings"]:
        lines.append("(quiet day — cron alive, system healthy)")
        lines.append("")

    lines.append("---")
    lines.append("Live demo: https://swarm.impt.io/widget")
    lines.append("Backend:   /home/mike/impt-swarm-oss-2026-05-05/backend/")
    lines.append("Logs:      sudo journalctl -u impt-swarm-widget.service -n 100")
    lines.append("")

    return "\n".join(lines)


def send(body):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        GMAIL_CREDS, scopes=["https://www.googleapis.com/auth/gmail.send"]
    ).with_subject(SENDER)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    msg = MIMEText(body)
    msg["to"] = TO
    msg["from"] = formataddr((FROM_NAME, SENDER))
    msg["subject"] = f"Swarm Widget · daily summary · {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result.get("id")


def main():
    try:
        d = fetch()
        body = format_body(d)
        if "--dry-run" in sys.argv:
            print(body)
            return 0
        msg_id = send(body)
        print(f"sent id={msg_id} to={TO}")
        return 0
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
