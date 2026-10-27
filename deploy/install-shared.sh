#!/usr/bin/env bash
# Установка рядом с уже работающим сайтом. Ничего не трогает в настройках другого сайта:
# добавляет только отдельный файл для kodverks.ru в nginx или Apache.
# Запуск из папки проекта:  sudo bash deploy/install-shared.sh
set -euo pipefail
cd "$(dirname "$0")/.."
DOMAIN="${DOMAIN:-kodverks.ru}"
EMAIL="${EMAIL:-admin@$DOMAIN}"
PORT=8081

[ -f .env ] || { echo "Нет файла .env в $(pwd)"; exit 1; }

echo "== 1. Какой веб-сервер обслуживает порт 80"
WEB=$(ss -ltnp '( sport = :80 )' 2>/dev/null | grep -oE 'nginx|apache2|httpd|caddy|docker-proxy' | head -1 || true)
echo "   найден: ${WEB:-ничего}"
case "$WEB" in
  nginx|apache2|httpd) ;;
  "") echo "   Порт 80 свободен — используйте обычную установку: sudo bash deploy/install.sh"; exit 1 ;;
  *) echo "   $WEB — автоматическая настройка не поддерживается. Пришлите этот вывод разработчику."; exit 1 ;;
esac

echo "== 2. Резервная копия настроек веб-сервера"
tar czf "/root/webserver-backup-$(date +%F-%H%M).tgz" /etc/nginx /etc/apache2 /etc/httpd 2>/dev/null || true

echo "== 3. Docker"
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

echo "== 4. Настройки .env"
set_var() { grep -q "^$1=" .env && sed -i "s|^$1=.*|$1=$2|" .env || echo "$1=$2" >> .env; }
set_var SITE_URL "https://$DOMAIN"; set_var CORS_ORIGINS "[\"https://$DOMAIN\"]"; set_var COOKIE_SECURE true
chmod 600 .env

touch .shared
echo "== 5. Запуск проекта на 127.0.0.1:$PORT"
docker compose -f docker-compose.yml -f docker-compose.shared.yml up -d --build
for i in $(seq 1 40); do curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1 && break; sleep 5; done
curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null && echo "   сайт отвечает" || { echo "   сайт не запустился: docker compose logs backend"; exit 1; }

echo "== 6. Виртуальный хост для $DOMAIN"
if [ "$WEB" = nginx ]; then
  CONF=/etc/nginx/sites-available/$DOMAIN.conf
  [ -d /etc/nginx/sites-available ] || CONF=/etc/nginx/conf.d/$DOMAIN.conf
  cat > "$CONF" <<NGX
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    client_max_body_size 5m;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGX
  [ -d /etc/nginx/sites-enabled ] && ln -sf "$CONF" /etc/nginx/sites-enabled/
  nginx -t && systemctl reload nginx
  PLUGIN=python3-certbot-nginx; CB=--nginx
else
  A2=/etc/apache2/sites-available/$DOMAIN.conf
  cat > "$A2" <<APA
<VirtualHost *:80>
    ServerName $DOMAIN
    ServerAlias www.$DOMAIN
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https" env=HTTPS
    ProxyPass / http://127.0.0.1:$PORT/
    ProxyPassReverse / http://127.0.0.1:$PORT/
</VirtualHost>
APA
  a2enmod proxy proxy_http headers >/dev/null; a2ensite "$DOMAIN" >/dev/null
  apache2ctl configtest && systemctl reload apache2
  PLUGIN=python3-certbot-apache; CB=--apache
fi

echo "== 7. HTTPS (Let's Encrypt)"
IP=$(curl -fsS https://api.ipify.org || true); DNS=$(getent hosts "$DOMAIN" | awk '{print $1}' | head -1 || true)
if [ "$IP" != "$DNS" ]; then
  echo "   !! $DOMAIN пока указывает на '${DNS:-ничего}', а сервер — $IP."
  echo "   Когда DNS обновится, выполните: certbot $CB -d $DOMAIN -d www.$DOMAIN --redirect -m $EMAIL --agree-tos -n"
else
  command -v certbot >/dev/null || { apt-get update -qq && apt-get install -y -qq certbot $PLUGIN; }
  certbot $CB -d "$DOMAIN" -d "www.$DOMAIN" --redirect -m "$EMAIL" --agree-tos -n
fi

echo "== 8. ВКонтакте"
docker compose -f docker-compose.yml -f docker-compose.shared.yml exec -T backend python -m app.scripts.vk_setup --test || true

echo; echo "Готово: https://$DOMAIN  (панель /admin). Сайт салона не затронут."
