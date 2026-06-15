# IMPT Swarm Widget — Launch checklist

**Status as of 2026-05-05 evening:** ready to push. Awaiting Mike's eyes-on green light.

## What's live tonight

| Surface | URL | Status |
|---|---|---|
| Widget bundle (CDN) | https://swarm.impt.io/widget.js | ✅ 200, 8.7KB gzipped, CORS:* |
| Demo + signup page | https://swarm.impt.io/widget | ✅ 200 |
| Health check | https://swarm.impt.io/api/widget/health | ✅ 200 |
| Partner signup API | POST https://swarm.impt.io/api/widget/partners/signup | ✅ |
| Click redirect | GET https://swarm.impt.io/api/widget/r?key=&dest= | ✅ 302 → app.impt.io with utm + cookie |
| Track pixel | GET https://swarm.impt.io/api/widget/track | ✅ 1×1 GIF |
| Booking webhook | POST https://swarm.impt.io/api/widget/booking | ✅ (5% accrual) |
| Partner dashboard API | GET /api/widget/partners/me | ✅ Bearer auth |
| Systemd unit | `impt-swarm-widget.service` | ✅ active, enabled |

## What's NOT pushed yet (waiting for Mike)

1. **GitHub public repo** — local `git init` done at `/home/mike/impt-swarm-oss-2026-05-05/repo/` with commit `0a8e922`. Public push is held per memory rule.
2. **app.impt.io booking webhook integration** — Henry's 5-line patch to fire the webhook on confirmation. Mongo-tail mock can run in the meantime.
3. **DNS** — `partners.impt.io/widget` (the dashboard route) does not yet have a frontend. Phase-2.
4. **Announcement** — no tweet, IG, LI, FB, email blast yet.

## To push the public repo (Mike runs after eyeballing)

```bash
cd /home/mike/impt-swarm-oss-2026-05-05/repo
gh repo create impt/swarm-widget \
    --public \
    --source=. \
    --description="The open-source hotel-search widget that pays you 5%. By IMPT." \
    --homepage="https://swarm.impt.io/widget" \
    --remote=origin \
    --push
```

## To roll back if anything goes wrong

```bash
sudo systemctl stop impt-swarm-widget.service
sudo systemctl disable impt-swarm-widget.service
sudo cp /etc/nginx/sites-enabled/swarm.impt.io.bak.* /etc/nginx/sites-enabled/swarm.impt.io
sudo nginx -t && sudo systemctl reload nginx
# repo: gh repo delete impt/swarm-widget --yes  (only if pushed)
```

## To start the Mongo-tail mock webhook (until Henry's patch lands)

Not built yet — placeholder. Build cmd:
```bash
# /home/mike/impt-swarm-oss-2026-05-05/backend/mongo_tail_webhook.py
# Watches Mongo `bookings` collection. On insert with utm_source starting "swarm-",
# POSTs to localhost:2027/api/widget/booking with the secret.
# Run as systemd unit impt-swarm-widget-tail.service.
```

## Numbers from tonight's smoke

- Widget JS: 8,761 bytes (under 12KB budget ✓)
- Backend `/health`: ok ✓
- Signup → redirect → booking webhook → /me round-trip: ok ✓
- 5% on €600 booking = €30 accrual ✓ (matches spec)
- 90-day cookie set on `*.impt.io` domain ✓
- nginx reload clean, no errors ✓
