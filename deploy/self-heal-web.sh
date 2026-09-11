#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="/var/log/opticonv1-web-self-heal.log"
LOCK_FILE="/var/lock/opticonv1-web-self-heal.lock"
mkdir -p "$(dirname "$LOG_FILE")"
exec 9>"$LOCK_FILE"
flock -n 9 || exit 0
exec >>"$LOG_FILE" 2>&1

log(){ echo "[$(date -Is)] $*"; }
warn(){ echo "[$(date -Is)] WARNING: $*" >&2; }

cd "$ROOT"
log "=== OpticonV1 web self-heal ==="

# 1) Host firewall: make the required public web ports reachable.
if command -v ufw >/dev/null 2>&1; then
  if ufw status 2>/dev/null | grep -q '^Status: active'; then
    ufw allow 80/tcp >/dev/null || true
    ufw allow 443/tcp >/dev/null || true
    ufw reload >/dev/null 2>&1 || true
    log "UFW: 80/tcp and 443/tcp allowed."
  fi
fi

# 2) Validate the proxy configuration before restarting it.
docker run --rm -v "$ROOT/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2-alpine \
  caddy validate --config /etc/caddy/Caddyfile

# 3) Make sure the proxy is recreated from the current repository config.
docker compose up -d --force-recreate proxy

# 4) Verify the application and proxy locally. 405 is acceptable here: it proves
#    that Caddy reached Uvicorn and the HTTP stack is alive.
api_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1/api/health || true)"
root_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1/ || true)"
log "Local /api/health HTTP=$api_code; local / HTTP=$root_code"

if [[ "$api_code" != "2"* ]]; then
  warn "API health check failed; restarting the whole compose stack."
  docker compose up -d --remove-orphans
  sleep 3
  api_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1/api/health || true)"
  log "API health after stack restart: HTTP=$api_code"
fi

# 5) Verify that Docker really published the public ports.
log "Listening sockets:"
ss -lntp 2>/dev/null | grep -E ':(80|443)\s' || true

# 6) Collect Alibaba ECS metadata without changing cloud resources.
META="http://100.100.100.200/latest/meta-data"
TOKEN="$(curl -fsS --max-time 2 -X PUT "$META/../api/token" \
  -H 'X-aliyun-ecs-metadata-token-ttl-seconds:60' 2>/dev/null || true)"
meta_get(){
  local path="$1"
  if [[ -n "$TOKEN" ]]; then
    curl -fsS --max-time 2 -H "X-aliyun-ecs-metadata-token: $TOKEN" "$META/$path" 2>/dev/null || true
  else
    curl -fsS --max-time 2 "$META/$path" 2>/dev/null || true
  fi
}

EIP="$(meta_get eipv4)"
PUBLIC="$(curl -4 -fsS --max-time 5 https://ifconfig.me 2>/dev/null || true)"
PRIVATE="$(meta_get private-ipv4)"
INSTANCE="$(meta_get instance-id)"
REGION="$(meta_get region-id)"

log "ECS instance=$INSTANCE region=$REGION private-ip=$PRIVATE eip=$EIP observed-public-ip=$PUBLIC"
log "Route: $(ip route get 1.1.1.1 2>/dev/null || true)"

# 7) Important: an ECS instance cannot repair a cloud-side ACL/security-group/
#    EIP/network-path problem from inside the OS. If local HTTP works but the
#    public path is still blocked, leave a precise diagnostic instead of looping
#    or making destructive network changes.
if [[ "$api_code" == "2"* ]] && [[ "$root_code" =~ ^(2|3|4|5)[0-9][0-9]$ ]]; then
  log "LOCAL_OK: Docker + Caddy + API are responding."
else
  warn "LOCAL_WEB_FAILED: inspect docker compose logs --tail=100 proxy api"
fi

if [[ -n "$EIP" && -n "$PUBLIC" && "$EIP" != "$PUBLIC" ]]; then
  warn "PUBLIC_IP_MISMATCH: ECS metadata EIP=$EIP but outbound observed IP=$PUBLIC. Check EIP/NAT attachment."
fi

log "If an external browser still times out while LOCAL_OK is present, the remaining fault is outside this host: check ALL attached Alibaba security groups, vSwitch Network ACL, EIP association, route table, Cloud Firewall/Anti-DDoS, and ECS diagnostics."
log "=== self-heal finished ==="
