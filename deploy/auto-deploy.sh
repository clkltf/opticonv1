#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="/var/lock/opticonv1-deploy.lock"
LOG_FILE="/var/log/opticonv1-deploy.log"

exec 9>"$LOCK_FILE"
flock -n 9 || exit 0

cd "$ROOT"
mkdir -p "$(dirname "$LOG_FILE")"
exec >>"$LOG_FILE" 2>&1

echo "[$(date -Is)] Checking GitHub..."

git fetch --quiet origin main
LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/main)"

if [[ "$LOCAL" == "$REMOTE" ]]; then
  echo "[$(date -Is)] Already up to date."
  exit 0
fi

echo "[$(date -Is)] New commit: $LOCAL -> $REMOTE"

# GitHub is the deployment source of truth. Never touch .env (it is untracked).
git reset --hard origin/main

chmod +x deploy/update.sh
deploy/update.sh

echo "[$(date -Is)] Automatic deployment completed."
