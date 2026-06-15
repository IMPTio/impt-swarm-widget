#!/bin/bash
# IMPT Swarm Widget — DB backup. Runs every 12h via cron.
# Keeps 14 days of 12-hourly snapshots (28 files) + 30 days of dailies.
set -euo pipefail
SRC=/home/mike/impt-swarm-oss-2026-05-05/backend/swarm_widget.db
DEST_DIR=/home/mike/backups/swarm-widget
TS=$(date -u +%Y%m%d-%H%M)
mkdir -p "$DEST_DIR"
# Use SQLite's online .backup (atomic, safe with WAL writes in flight)
/home/mike/impt-swarm-oss-2026-05-05/backend/.venv/bin/python -c "
import sqlite3, sys
src = sqlite3.connect('$SRC')
dst = sqlite3.connect('$DEST_DIR/swarm-${TS}.db')
src.backup(dst)
dst.close(); src.close()
print('backed up to $DEST_DIR/swarm-${TS}.db')
"
gzip -9 "$DEST_DIR/swarm-${TS}.db"
# Retention: keep last 28 12h snapshots (= 14 days)
ls -1t "$DEST_DIR"/swarm-*.db.gz | tail -n +29 | xargs -r rm -f
