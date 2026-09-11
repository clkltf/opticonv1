#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="/var/log/opticonv1-network-diagnose.log"
mkdir -p "$(dirname "$LOG_FILE")"
exec >>"$LOG_FILE" 2>&1

echo "[$(date -Is)] === OpticonV1 network diagnosis ==="
cd "$ROOT"

public_ip="$(curl -4 -fsS --max-time 5 https://ifconfig.me 2>/dev/null || true)"
private_ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
route="$(ip route get 1.1.1.1 2>/dev/null || true)"
echo "public_ip=$public_ip"
echo "private_ip=$private_ip"
echo "route=$route"

echo "--- listeners ---"
ss -lntp 2>/dev/null | grep -E ':(80|443)\\s' || true

echo "--- firewall ---"
ufw status verbose 2>/dev/null || true
iptables -L INPUT -n -v 2>/dev/null || true

echo "--- local http ---"
for url in http://127.0.0.1/ http://127.0.0.1/api/health; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$url" || true)"
  echo "$url => HTTP $code"
done

echo "--- caddy container ---"
docker compose ps proxy 2>/dev/null || true
docker compose logs --tail=80 proxy 2>/dev/null || true

echo "--- ecs metadata ---"
META="http://100.100.100.200/latest/meta-data"
TOKEN="$(curl -fsS --max-time 2 -X PUT "$META/../api/token" -H 'X-aliyun-ecs-metadata-token-ttl-seconds:60' 2>/dev/null || true)"
meta_get(){
  local p="$1"
  if [[ -n "$TOKEN" ]]; then
    curl -fsS --max-time 2 -H "X-aliyun-ecs-metadata-token: $TOKEN" "$META/$p" 2>/dev/null || true
  else
    curl -fsS --max-time 2 "$META/$p" 2>/dev/null || true
  fi
}
echo "instance_id=$(meta_get instance-id)"
echo "region=$(meta_get region-id)"
echo "metadata_eip=$(meta_get eipv4)"
echo "metadata_private_ip=$(meta_get private-ipv4)"

echo "--- conclusion ---"
if curl -fsS --max-time 10 http://127.0.0.1/api/health >/dev/null 2>&1; then
  echo "LOCAL_OK: API/Caddy stack responds locally."
else
  echo "LOCAL_FAIL: API/Caddy stack does not respond locally."
fi

echo "EXTERNAL_TEST_REQUIRED: test http://$public_ip/ from a different network/device."
echo "CLOUD_CHECK_REQUIRED_IF_TIMEOUT: attached Security Groups, vSwitch Network ACL, EIP association, route table, Cloud Firewall/Anti-DDoS, and ECS diagnostics."
echo "[$(date -Is)] === diagnosis finished ==="