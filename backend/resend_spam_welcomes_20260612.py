#!/usr/bin/env python3
"""Resend widget WELCOME emails that spam-foldered in the June 10-12 window.
Mike-authorised 2026-06-12 ("resend anything that went to spam in last week").
- Cohort: partners created >= 2026-06-10 00:00 UTC.
- Gated by email_suppression (also enforced inside _em_send now).
- Idempotent: logs to widget_welcome_resend; re-run skips already-sent.
- Throttled to protect sender reputation.
"""
import sqlite3, time, sys, os
sys.path.insert(0, "/home/mike/ads-meta-launch")
import email_suppression as supp
os.environ.setdefault("SWARM_WIDGET_DB", "/srv/swarm/impt-swarm-oss-2026-05-05/backend/swarm_widget.db")
import swarm_widget_api as w

DB = os.environ["SWARM_WIDGET_DB"]
con = sqlite3.connect(DB)
con.execute("""CREATE TABLE IF NOT EXISTS widget_welcome_resend(
    partner_id INTEGER PRIMARY KEY, email TEXT, ts INTEGER, result TEXT)""")
con.commit()

rows = con.execute("""SELECT id,email,name,key,api_token FROM partners
    WHERE status='active'
    ORDER BY created_at""").fetchall()

already = {r[0] for r in con.execute("SELECT partner_id FROM widget_welcome_resend").fetchall()}
DRY = "--go" not in sys.argv
sent = skipped = failed = 0
print(f"cohort={len(rows)} already_done={len(already)} mode={'DRY' if DRY else 'SEND'}")
for pid, email, name, key, api_token in rows:
    if pid in already:
        continue
    ok, why = supp.check(con, email)
    if not ok:
        con.execute("INSERT OR REPLACE INTO widget_welcome_resend VALUES (?,?,?,?)",
                    (pid, email, int(time.time()), f"skip-{why}"))
        con.commit(); skipped += 1; continue
    if DRY:
        sent += 1; continue
    try:
        good = w.send_welcome_email(email, name, key, api_token)
        res = "sent" if good else "send-failed"
        con.execute("INSERT OR REPLACE INTO widget_welcome_resend VALUES (?,?,?,?)",
                    (pid, email, int(time.time()), res))
        con.commit()
        if good: sent += 1
        else: failed += 1
        time.sleep(0.6)  # ~1.6/sec throttle
    except Exception as e:
        failed += 1
        con.execute("INSERT OR REPLACE INTO widget_welcome_resend VALUES (?,?,?,?)",
                    (pid, email, int(time.time()), f"error:{str(e)[:60]}"))
        con.commit()
print(f"RESULT sent={sent} skipped(suppressed)={skipped} failed={failed}")
