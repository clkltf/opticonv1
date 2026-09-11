#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo '[1/5] Git durumunu kontrol ediyorum...'
git fetch origin main
git diff --quiet && git diff --cached --quiet || {
  echo 'HATA: Sunucuda commit edilmemiş yerel değişiklik var. Önce inceleyin.'
  exit 1
}

echo '[2/5] GitHub main güncelleniyor...'
git pull --ff-only origin main

echo '[3/5] Caddyfile doğrulanıyor...'
docker run --rm -v "$ROOT/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile

echo '[4/5] Docker imajları build ediliyor...'
docker compose build --pull

echo '[5/5] Servisler başlatılıyor...'
docker compose up -d

sleep 3
curl -fsS http://127.0.0.1/api/health >/dev/null
printf '\nDEPLOY OK\n'
docker compose ps
