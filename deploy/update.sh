#!/usr/bin/env bash
# Обновление после загрузки новой версии кода: sudo bash deploy/update.sh
set -euo pipefail
cd "$(dirname "$0")/.."
COMPOSE_FILE_2=$( [ -f .shared ] && echo docker-compose.shared.yml || echo docker-compose.prod.yml )
docker compose -f docker-compose.yml -f "$COMPOSE_FILE_2" up -d --build
docker image prune -f >/dev/null
