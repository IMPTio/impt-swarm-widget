# IMPT Widget — code backup mirror

Auto-synced daily from the LIVE widget code on the management server (35.214.111.96).
This is a **source-only mirror** — no secrets (.env), no database, no venv.

| Folder | Live source |
|---|---|
| `backend/` | `/srv/swarm/impt-swarm-oss-2026-05-05/backend/` (API on :2027) |
| `widget/widget.js` | `/srv/swarm/impt-swarm-oss-2026-05-05/repo/src/widget.js` (served at swarm.impt.io/widget.js) |
| `site/` | widget-relevant files from `/srv/swarm/impt-swarm/site/` |
| `docs/` | repo specs |

Sync: `sync_widget_code.sh` via cron (daily 04:30 Dublin). Clone: `git clone mike@35.214.111.96:/home/mike/git-remotes/impt-widget.git`
