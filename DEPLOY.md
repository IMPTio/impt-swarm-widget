# DEPLOY — how changes in this repo go LIVE

**This repo is the source of truth for the live widget, dashboard, and backend API.**
Push to `main` and a validated deploy puts it live on the server automatically — usually
within ~2 minutes. You do **not** need SSH to the server.

Set up June 2026 so Henry (`henryimpt`) and AJ (`AjayjitSingh`) can ship the widget directly.

## How it works

1. You edit a file here and `git push` to **`main`**.
2. A server job (`deploy_widget.sh`, cron every 2 min) pulls your commit, **validates it**,
   backs up the current live files, and copies your changes to the live serving paths.
3. You get a WhatsApp from Laura's number: `✅ widget deploy live …` (or a 🛑 / 🚨 if something was wrong).

## What maps where (repo → live URL)

| Repo path | Live URL |
|---|---|
| `widget/widget.js` | `https://swarm.impt.io/widget.js` (the embed partners paste) |
| `site/dashboard.html` | `https://swarm.impt.io/dashboard.html` |
| `site/widget-install.html` | `https://swarm.impt.io/widget-install.html` |
| `site/go.html` | `https://swarm.impt.io/go.html` |
| `site/widget-launcher.js`, `widget-v3.js`, `mtb-widget.js`, `wavelength.js` | `https://swarm.impt.io/<file>` |
| `site/assets/impt-widget-ds.css` | `https://swarm.impt.io/assets/impt-widget-ds.css` |
| `backend/*.py` | the widget API (`https://swarm.impt.io/api/widget/…`, uvicorn :2027) |

The **fuel** page (`impt.io/widgetfuel`) lives in a separate repo: **`IMPTio/impt-widgetfuel`** (same system).

## Safe vs. validated

- **Static files (HTML / JS / CSS)** — deployed instantly. They can't take a service down.
  Bad JS (syntax error) is **refused** by `node --check`; tiny/empty HTML is refused.
- **Backend (`backend/*.py`)** — every `.py` is `py_compile`-checked first. If it passes, the
  files are copied and the API service is **restarted**, then **health-checked**
  (`/api/widget/health`). **If the restart is unhealthy, it auto-rolls back to the previous
  version and pings Mike** — the API is never left down. A broken push simply doesn't go live.

## Rules (so nothing breaks)

1. **Never commit secrets or data.** `.env`, `*.db`, and live data never belong in git
   (they're git-ignored on the server). The API reads its real `.env` on the server.
2. **Don't edit files directly on the server.** The repo is source of truth — a direct server
   edit gets overwritten by the next push. Make the change here.
3. **`backend/impt-swarm-widget.service` and `requirements.txt` are NOT auto-deployed.** Changing
   the systemd unit or Python dependencies needs a manual step — ping Mike/ops.
4. **swarm.impt.io / impt.io take paid ad traffic.** Test your change, keep commits focused.

## If a deploy is blocked or rolled back

- 🛑 *"deploy BLOCKED — bad commit"* → your push failed validation (syntax/empty file). Live is
  untouched. Fix and push again.
- 🚨 *"backend deploy FAILED health check — auto-rolled-back"* → your backend change started but
  the service didn't come up healthy. The previous version was restored. Check your last commit.
- Deploy log on the server: `/home/mike/widget-deploy/deploy.log`. Pre-deploy backups:
  `/home/mike/widget-deploy/backups/<timestamp>/`.
