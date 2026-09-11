#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ $EUID -ne 0 ]]; then
  echo 'Hata: kur.sh root olarak çalıştırılmalı (sudo ./kur.sh)'; exit 1
fi

command -v apt-get >/dev/null || { echo 'Desteklenen Ubuntu/Debian tabanlı sistem gerekli.'; exit 1; }
apt-get update
apt-get install -y ca-certificates curl git ufw openssl

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

docker compose version >/dev/null 2>&1 || { echo 'Docker Compose plugin bulunamadı.'; exit 1; }

if [[ ! -f .env ]]; then
  cp .env.example .env
  DBPASS="$(openssl rand -hex 24)"
  sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${DBPASS}/" .env
  sed -i "s#^DATABASE_URL=.*#DATABASE_URL=postgresql://opticon:${DBPASS}@postgres:5432/opticon#" .env
  echo 'Yeni .env oluşturuldu. DOMAIN değerini gerekirse düzenleyin.'
fi

mkdir -p data
chmod 700 data

# Do not expose database/redis/application ports. Only HTTP(S) is public.
ufw allow OpenSSH || true
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

docker compose up -d --build
echo 'Servisler başlatıldı. Sağlık kontrolü:'
sleep 5
docker compose ps
curl -fsS http://127.0.0.1:8080/api/health >/dev/null 2>&1 && echo 'API health OK' || echo 'API internal health henüz hazır değil; docker compose logs -f api ile kontrol edin.'
