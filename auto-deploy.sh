#!/bin/bash
# Auto-deploy: pulls latest code and restarts Odoo if new commits exist on main branch

REPO_DIR="/Users/naman/Desktop/Odoo-17-Docker"
BRANCH="claude/awesome-bartik-2ea7dc"
LOG_FILE="$REPO_DIR/auto-deploy.log"

cd "$REPO_DIR" || exit 1

git fetch origin "$BRANCH" --quiet

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
  exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] New commits detected — deploying..." >> "$LOG_FILE"

git pull origin "$BRANCH" --quiet >> "$LOG_FILE" 2>&1

docker compose restart web >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deploy complete. Commit: $(git rev-parse --short HEAD)" >> "$LOG_FILE"
