#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$ROOT"
[[ $EUID -eq 0 ]] || { echo 'Hata: sudo ./kur.sh ile çalıştırın.'; exit 1; }
command -v apt-get >/dev/null || { echo 'Ubuntu/Debian tabanlı sistem gerekli.'; exit 1; }
apt-get update && apt-get install -y ca-certificates curl git ufw openssl
if ! command -v docker >/dev/null; then curl -fsSL https://get.docker.com | sh; fi
systemctl enable --now docker
docker compose version >/dev/null 2>&1 || { echo 'Docker Compose plugin bulunamadı.'; exit 1; }
if [[ ! -f .env ]]; then
  cp .env.example .env
  DBPASS="$(openssl rand -hex 24)"
  sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${DBPASS}/" .env
  sed -i "s#^DATABASE_URL=.*#DATABASE_URL=postgresql://opticon:${DBPASS}@postgres:5432/opticon#" .env
fi
mkdir -p data && chmod 700 data
ufw allow OpenSSH || true; ufw allow 80/tcp; ufw allow 443/tcp; ufw --force enable
docker compose up -d --build
sleep 8
docker compose ps
if docker compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=5)"; then
  echo 'API health OK'
else
  echo 'API henüz hazır değil. docker compose logs --tail=100 api ile kontrol edin.'
  exit 1
fi
