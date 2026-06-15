#!/usr/bin/env bash
# Daily backup mirror of the LIVE IMPT widget codebase -> git (bare remote ~/git-remotes/impt-widget.git).
# Source-only: excludes secrets (.env), the live DB (PII/leads), venv, logs, and .bak clutter.
# Created 2026-06-15 (Mike: "create git and have it updated daily").
set -euo pipefail

REPO=/home/mike/impt-widget-code
BACKEND_SRC=/srv/swarm/impt-swarm-oss-2026-05-05/backend
WIDGETJS_SRC=/srv/swarm/impt-swarm-oss-2026-05-05/repo/src/widget.js
OSS_TOP=/srv/swarm/impt-swarm-oss-2026-05-05
SITE_SRC=/srv/swarm/impt-swarm/site

cd "$REPO"

# What never enters git (secrets / data / build / clutter)
EXCLUDES=(--exclude='.venv' --exclude='__pycache__' --exclude='*.pyc'
          --exclude='.env' --exclude='.env.*' --exclude='*.db' --exclude='*.db*'
          --exclude='*.log' --exclude='*.bak' --exclude='*.bak-*' --exclude='*.bak.*')

# 1) backend (the API brain)
mkdir -p backend
rsync -a --delete "${EXCLUDES[@]}" "$BACKEND_SRC"/ backend/

# 2) embed script partners paste
mkdir -p widget
cp -f "$WIDGETJS_SRC" widget/widget.js

# 3) repo-level docs/specs
mkdir -p docs
for f in COMPLETE_STATE.md SPEC.md LAUNCH.md; do
  [ -f "$OSS_TOP/$f" ] && cp -f "$OSS_TOP/$f" "docs/$f" || true
done

# 4) widget-relevant served files (curated; skip generated SEO junk + .bak)
mkdir -p site
for f in dashboard.html go.html widget-install.html widget-launcher.js widget-v3.js mtb-widget.js wavelength.js; do
  [ -f "$SITE_SRC/$f" ] && cp -f "$SITE_SRC/$f" "site/$f" || true
done
mkdir -p site/assets
[ -f "$SITE_SRC/assets/impt-widget-ds.css" ] && cp -f "$SITE_SRC/assets/impt-widget-ds.css" site/assets/ || true

# 5) commit + push only if something changed
git add -A
if git diff --cached --quiet; then
  echo "[sync_widget_code] no changes $(date -u +%FT%TZ)"
else
  git commit -q -m "auto: widget code snapshot $(date -u +%F)" \
    --author="widget-backup <noreply@impt.io>"
  git push -q origin main
  echo "[sync_widget_code] pushed snapshot $(date -u +%FT%TZ)"
fi
