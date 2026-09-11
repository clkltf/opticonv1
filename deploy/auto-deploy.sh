#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="/var/lock/opticonv1-deploy.lock"
LOG_FILE="/var/log/opticonv1-deploy.log"
mkdir -p "$(dirname "$LOG_FILE")"
exec 9>"$LOCK_FILE"
flock -n 9 || exit 0
cd "$ROOT"
exec >>"$LOG_FILE" 2>&1

echo "[$(date -Is)] Checking GitHub..."
git fetch --quiet origin main
LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/main)"

# The web self-healer runs even when there is no new application commit.
chmod +x deploy/self-heal-web.sh deploy/network-diagnose.sh deploy/update.sh

auto_heal(){
  echo "[$(date -Is)] Running web self-heal..."
  deploy/self-heal-web.sh || echo "[$(date -Is)] Web self-heal reported a non-fatal error."
}

if [[ "$LOCAL" != "$REMOTE" ]]; then
  echo "[$(date -Is)] New commit: $LOCAL -> $REMOTE"
  # GitHub is the deployment source of truth. Never touch .env (it is untracked).
  git reset --hard origin/main
  chmod +x deploy/self-heal-web.sh deploy/network-diagnose.sh deploy/update.sh
  deploy/update.sh
else
  echo "[$(date -Is)] Already up to date."
fi

auto_heal

echo "[$(date -Is)] Running network diagnosis..."
deploy/network-diagnose.sh || echo "[$(date -Is)] Network diagnosis reported a non-fatal error."
echo "[$(date -Is)] Automatic deployment check finished."
