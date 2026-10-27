#!/usr/bin/env bash
# Установка на чистый VPS (Ubuntu 22.04/24.04 или Debian 12).
# Запуск из папки проекта:  sudo bash deploy/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."
DOMAIN="${DOMAIN:-kodverks.ru}"

echo "== 1. Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

echo "== 2. Файрвол (SSH, HTTP, HTTPS)"
if command -v ufw >/dev/null; then
  ufw allow OpenSSH >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443 >/dev/null
  ufw --force enable >/dev/null
fi

echo "== 3. Настройки"
if [ ! -f .env ]; then
  echo "Нет файла .env — положите его в $(pwd) и запустите снова."; exit 1
fi
set_var() { grep -q "^$1=" .env && sed -i "s|^$1=.*|$1=$2|" .env || echo "$1=$2" >> .env; }
set_var DOMAIN "$DOMAIN"
set_var SITE_URL "https://$DOMAIN"
set_var CORS_ORIGINS "[\"https://$DOMAIN\"]"
set_var COOKIE_SECURE true
chmod 600 .env

echo "== 4. Проверка DNS"
IP=$(curl -fsS https://api.ipify.org || true)
DNS=$(getent hosts "$DOMAIN" | awk '{print $1}' | head -1 || true)
echo "IP сервера: ${IP:-?}   $DOMAIN указывает на: ${DNS:-нет записи}"
[ -n "$IP" ] && [ "$IP" != "$DNS" ] && echo "!! A-запись домена ещё не указывает на сервер — HTTPS выпустится, когда DNS обновится."

echo "== 5. Запуск"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo "== 6. Ждём backend"
for i in $(seq 1 40); do
  docker compose ps backend | grep -q healthy && break; sleep 5
done
docker compose ps

echo "== 7. Настройка сообщества ВКонтакте"
docker compose exec -T backend python -m app.scripts.vk_setup --test || true

echo
echo "Готово: https://$DOMAIN   панель: https://$DOMAIN/admin"
