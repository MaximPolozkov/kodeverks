#!/usr/bin/env bash
# Резервная копия базы в папку backups/ (храните 14 последних). Добавьте в cron:
# 0 3 * * * cd /opt/kodverk && bash deploy/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "backups/db-$(date +%F-%H%M).sql.gz"
ls -1t backups/*.sql.gz | tail -n +15 | xargs -r rm
