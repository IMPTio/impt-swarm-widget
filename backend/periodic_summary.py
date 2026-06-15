#!/home/mike/impt-swarm-oss-2026-05-05/backend/.venv/bin/python
"""
IMPT Swarm Widget — 3-hourly summary + risk check.

Cron every 3h. Window = last 3 hours.
- Activity (signups, views, clicks, bookings)
- Risks / anomalies (service health, disk, cert expiry, DB integrity, errors)

If nothing happened AND no risks: sends a one-liner "all quiet" so we know cron's alive.
"""
import base64
import os
import re
import shutil
import sqlite3
import ssl
import socket
import subprocess
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
WINDOW_HRS = 3


def fetch_activity():
    end = int(time.time())
    start = end - WINDOW_HRS * 3600
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row

    def q(sql, *a):
        return c.execute(sql, a).fetchall()

    out = {
        "window_start_iso": datetime.fromtimestamp(start, timezone.utc).isoformat(timespec="minutes"),
        "window_end_iso": datetime.fromtimestamp(end, timezone.utc).isoformat(timespec="minutes"),
        "new_signups": [dict(r) for r in q(
            "SELECT key, email, status FROM partners WHERE created_at BETWEEN ? AND ? ORDER BY created_at",
            start, end)],
        "verified_now": [dict(r) for r in q(
            "SELECT key, email FROM partners WHERE verified_at BETWEEN ? AND ?", start, end)],
        "events_by_type": [dict(r) for r in q(
            "SELECT evt, COUNT(*) AS n FROM partner_events WHERE ts BETWEEN ? AND ? GROUP BY evt ORDER BY n DESC",
            start, end)],
        "top_dest": [dict(r) for r in q(
            "SELECT dest, COUNT(*) AS n FROM partner_events WHERE ts BETWEEN ? AND ? AND evt='click' AND dest IS NOT NULL GROUP BY dest ORDER BY n DESC LIMIT 5",
            start, end)],
        "top_partners": [dict(r) for r in q(
            "SELECT key, COUNT(*) AS clicks FROM partner_events WHERE ts BETWEEN ? AND ? AND evt='click' GROUP BY key ORDER BY clicks DESC LIMIT 5",
            start, end)],
        "new_bookings": [dict(r) for r in q(
            "SELECT partner_key, booking_id, base_value_cents, currency, accrual_eur_cents, status FROM partner_bookings WHERE booked_at BETWEEN ? AND ? ORDER BY booked_at DESC",
            start, end)],
        "accrual_window": q(
            "SELECT COALESCE(SUM(accrual_eur_cents),0) AS s FROM partner_bookings WHERE booked_at BETWEEN ? AND ?",
            start, end)[0]["s"],
        "honeypot_trips": q(
            "SELECT COUNT(*) AS n FROM audit_log WHERE ts BETWEEN ? AND ? AND action='signup.honeypot_trip'",
            start, end)[0]["n"],
        "bad_sigs": q(
            "SELECT COUNT(*) AS n FROM audit_log WHERE ts BETWEEN ? AND ? AND action='webhook.bad_auth'",
            start, end)[0]["n"],
        "click_inactive": q(
            "SELECT COUNT(*) AS n FROM partner_events WHERE ts BETWEEN ? AND ? AND evt='click_inactive'",
            start, end)[0]["n"],
        "totals": {
            "all_partners": q("SELECT COUNT(*) AS n FROM partners")[0]["n"],
            "active_partners": q("SELECT COUNT(*) AS n FROM partners WHERE status='active'")[0]["n"],
            "all_bookings": q("SELECT COUNT(*) AS n FROM partner_bookings")[0]["n"],
            "all_accrual_cents": q("SELECT COALESCE(SUM(accrual_eur_cents),0) AS s FROM partner_bookings")[0]["s"],
            "stuck_pending_signups": q(
                "SELECT COUNT(*) AS n FROM partners WHERE status='pending_email' AND created_at < ?",
                end - 24 * 3600)[0]["n"],
        }
    }
    c.close()
    return out


def fetch_risks():
    """Check service health, disk, cert, DB, recent errors. Return list of risk strings."""
    risks = []
    warns = []

    # 1. systemd unit alive
    try:
        r = subprocess.run(["systemctl", "is-active", "impt-swarm-widget.service"],
                           capture_output=True, text=True, timeout=5)
        if r.stdout.strip() != "active":
            risks.append(f"BACKEND DOWN: impt-swarm-widget.service is '{r.stdout.strip()}'")
    except Exception as e:
        risks.append(f"systemd check failed: {e}")

    # 2. nginx alive
    try:
        r = subprocess.run(["systemctl", "is-active", "nginx"],
                           capture_output=True, text=True, timeout=5)
        if r.stdout.strip() != "active":
            risks.append(f"NGINX DOWN: '{r.stdout.strip()}'")
    except Exception as e:
        risks.append(f"nginx check failed: {e}")

    # 3. Public health endpoint OK? (Use Mozilla UA — Python-urllib gets blocked by CF/bot filter)
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://swarm.impt.io/api/widget/health",
            headers={"User-Agent": "Mozilla/5.0 (compatible; ImptSwarmCron/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                risks.append(f"PUBLIC HEALTH NOT 200: {resp.status}")
    except Exception as e:
        risks.append(f"public health check failed: {e}")

    # 4. Disk free
    try:
        usage = shutil.disk_usage("/")
        pct_used = usage.used / usage.total * 100
        free_gb = usage.free / 1e9
        if pct_used > 90:
            risks.append(f"DISK >90%: {pct_used:.1f}% used, {free_gb:.1f} GB free")
        elif pct_used > 80:
            warns.append(f"disk {pct_used:.1f}% used ({free_gb:.1f} GB free)")
    except Exception as e:
        warns.append(f"disk check failed: {e}")

    # 5. SSL cert expiry on swarm.impt.io
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection(("swarm.impt.io", 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname="swarm.impt.io") as ssock:
                cert = ssock.getpeercert()
                exp = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                days_left = (exp - datetime.now(timezone.utc).replace(tzinfo=None)).days
                if days_left < 14:
                    risks.append(f"CERT EXPIRES IN {days_left}d on swarm.impt.io")
                elif days_left < 30:
                    warns.append(f"cert expires in {days_left}d on swarm.impt.io")
    except Exception as e:
        warns.append(f"cert check failed: {e}")

    # 6. DB integrity
    try:
        c = sqlite3.connect(DB_PATH)
        r = c.execute("PRAGMA integrity_check").fetchone()
        if r[0] != "ok":
            risks.append(f"DB INTEGRITY: {r[0]}")
        c.close()
    except Exception as e:
        risks.append(f"DB integrity check failed: {e}")

    # 7. Backend errors in last 30 min only (smaller, fresher window — service restarts
    #    or schema migrations from earlier in the 3h window are not "current risks").
    try:
        r = subprocess.run(
            ["journalctl", "-u", "impt-swarm-widget.service", "--since", "30 min ago", "--no-pager"],
            capture_output=True, text=True, timeout=10
        )
        ignore = re.compile(r"(bad signature|bad_auth|bad_email|honeypot|pending_email|email rejected|too many signups|key collision)", re.I)
        bug_re = re.compile(r"(Traceback|FAILED:|Exception|asyncio\.exceptions|OperationalError)")
        err_count = sum(1 for line in r.stdout.splitlines()
                        if bug_re.search(line) and not ignore.search(line))
        if err_count > 5:
            risks.append(f"BACKEND ERRORS: {err_count} bug-shaped lines in last 30 min")
        elif err_count > 0:
            warns.append(f"backend errors: {err_count} bug-shaped lines in last 30 min")
    except Exception as e:
        warns.append(f"journalctl check failed: {e}")

    # 8. nginx 5xx in last window
    try:
        log = "/var/log/nginx/swarm.impt.io.access.log"
        if os.path.exists(log):
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=WINDOW_HRS)
            count_5xx = 0
            with open(log, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 200_000))
                tail = f.read().decode("utf-8", "ignore")
            for line in tail.splitlines():
                m = re.search(r' "[A-Z]+ [^"]+" (5\d\d) ', line)
                if m:
                    count_5xx += 1
            if count_5xx > 20:
                risks.append(f"NGINX 5xx SPIKE: {count_5xx} in last {WINDOW_HRS}h on swarm.impt.io")
            elif count_5xx > 0:
                warns.append(f"nginx 5xx: {count_5xx} in last {WINDOW_HRS}h on swarm.impt.io")
    except Exception as e:
        warns.append(f"nginx log check failed: {e}")

    # 9. DB rapid growth (proxy for bot signup attempts despite rate-limits)
    try:
        c = sqlite3.connect(DB_PATH)
        recent = c.execute(
            "SELECT COUNT(*) FROM partners WHERE created_at > ?",
            (int(time.time()) - WINDOW_HRS * 3600,)
        ).fetchone()[0]
        c.close()
        if recent > 50:
            risks.append(f"SIGNUP SPIKE: {recent} new signup rows in last {WINDOW_HRS}h (possible bot)")
        elif recent > 20:
            warns.append(f"signup velocity: {recent} in last {WINDOW_HRS}h")
    except Exception as e:
        warns.append(f"signup velocity check failed: {e}")

    return risks, warns


def format_body(activity, risks, warns):
    eur = lambda c: f"€{c/100:.2f}"
    lines = []

    has_activity = (activity["new_signups"] or activity["verified_now"]
                    or activity["events_by_type"] or activity["new_bookings"])

    if not has_activity and not risks and not warns:
        # quiet
        t = activity["totals"]
        return (f"IMPT Swarm — {WINDOW_HRS}h tick · all quiet · {t['active_partners']} active partners · "
                f"€{t['all_accrual_cents']/100:.2f} lifetime accrual · system healthy")

    lines.append(f"IMPT Swarm Widget — {WINDOW_HRS}h update")
    lines.append(f"Window: {activity['window_start_iso']} → {activity['window_end_iso']}")
    lines.append("")

    # ── Risks first
    if risks:
        lines.append(f"🚨 RISKS ({len(risks)})")
        for r in risks:
            lines.append(f"  · {r}")
        lines.append("")

    if warns:
        lines.append(f"⚠️  WARNINGS ({len(warns)})")
        for w in warns:
            lines.append(f"  · {w}")
        lines.append("")

    # ── Activity
    e_total = sum(e["n"] for e in activity["events_by_type"])
    lines.append("📊 ACTIVITY")
    lines.append(f"  Signups:        {len(activity['new_signups'])}")
    lines.append(f"  Verified:       {len(activity['verified_now'])}")
    lines.append(f"  Total events:   {e_total}")
    for e in activity["events_by_type"]:
        lines.append(f"    · {e['evt']:<16} {e['n']}")
    lines.append(f"  Bookings:       {len(activity['new_bookings'])}")
    lines.append(f"  Accrual window: {eur(activity['accrual_window'])}")
    lines.append("")

    if activity["new_signups"]:
        lines.append("🆕 NEW SIGNUPS")
        for s in activity["new_signups"]:
            lines.append(f"  · {s['key']}  {s['email']}  [{s['status']}]")
        lines.append("")

    if activity["top_dest"]:
        lines.append("🌍 TOP DESTINATIONS")
        for t in activity["top_dest"]:
            lines.append(f"  · {t['dest']:<24} {t['n']}")
        lines.append("")

    if activity["top_partners"]:
        lines.append("🥇 TOP PARTNERS (clicks)")
        for p in activity["top_partners"]:
            lines.append(f"  · {p['key']:<22} {p['clicks']}")
        lines.append("")

    if activity["new_bookings"]:
        lines.append("💰 NEW BOOKINGS")
        for b in activity["new_bookings"]:
            lines.append(f"  · {b['booking_id']}  {b['partner_key']}  base={b['base_value_cents']/100:.2f} {b['currency']}  accrual={eur(b['accrual_eur_cents'])}  [{b['status']}]")
        lines.append("")

    sec = activity["honeypot_trips"] + activity["bad_sigs"] + activity["click_inactive"]
    if sec:
        lines.append("🛡️  SECURITY")
        if activity["click_inactive"]:
            lines.append(f"  · Inactive-key clicks:    {activity['click_inactive']}")
        if activity["honeypot_trips"]:
            lines.append(f"  · Honeypot trips:         {activity['honeypot_trips']}")
        if activity["bad_sigs"]:
            lines.append(f"  · Bad webhook sigs:       {activity['bad_sigs']}")
        lines.append("")

    # ── Lifetime
    t = activity["totals"]
    lines.append("📈 LIFETIME")
    lines.append(f"  Partners total/active:  {t['all_partners']} / {t['active_partners']}")
    lines.append(f"  Bookings total:         {t['all_bookings']}")
    lines.append(f"  Accrual total:          {eur(t['all_accrual_cents'])}")
    if t["stuck_pending_signups"] > 0:
        lines.append(f"  Stuck unverified > 24h: {t['stuck_pending_signups']}")
    lines.append("")

    lines.append("---")
    lines.append("Demo: https://swarm.impt.io/widget")
    lines.append("Logs: sudo journalctl -u impt-swarm-widget.service -n 100")
    lines.append("")
    return "\n".join(lines)


def send(body, has_alarms):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        GMAIL_CREDS, scopes=["https://www.googleapis.com/auth/gmail.send"]
    ).with_subject(SENDER)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    msg = MIMEText(body)
    msg["to"] = TO
    msg["from"] = formataddr((FROM_NAME, SENDER))
    prefix = "🚨 " if has_alarms else "· "
    msg["subject"] = f"{prefix}Swarm tick · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result.get("id")


def main():
    try:
        activity = fetch_activity()
        risks, warns = fetch_risks()
        body = format_body(activity, risks, warns)
        if "--dry-run" in sys.argv:
            print(body)
            return 0
        msg_id = send(body, has_alarms=bool(risks))
        print(f"sent id={msg_id} risks={len(risks)} warns={len(warns)}")
        return 0
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
