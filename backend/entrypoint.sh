#!/bin/sh
set -e

# Миграции и первый админ — только для API-контейнера (у воркера RUN_MIGRATIONS=0)
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "Применяю миграции..."
  alembic upgrade head
  python -m app.scripts.create_admin
fi

exec "$@"
