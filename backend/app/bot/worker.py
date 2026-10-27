"""Фоновый воркер бота (ARQ + Redis).

Запуск: arq app.bot.worker.WorkerSettings
"""

import logging

from arq import cron
from arq.connections import RedisSettings

from app.bot.runner import cleanup_old_leads, due_for_run, run_search
from app.core.config import settings
from app.core.db import SessionLocal

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot.worker")


async def search_job(ctx: dict, force: bool = False) -> dict:
    async with SessionLocal() as session:
        run = await run_search(session, force=force)
    if run is None:
        return {"skipped": True}
    return {"run_id": run.id, "found": run.found_count, "contacted": run.contacted_count}


async def scheduler_tick(ctx: dict) -> None:
    """Каждые 5 минут проверяет, не пора ли запустить поиск по расписанию."""
    async with SessionLocal() as session:
        due = await due_for_run(session)
    if due:
        await search_job(ctx)


async def cleanup_job(ctx: dict) -> None:
    async with SessionLocal() as session:
        removed = await cleanup_old_leads(session)
    log.info("Удалено устаревших лидов: %s", removed)


class WorkerSettings:
    functions = [search_job]
    cron_jobs = [
        cron(scheduler_tick, minute=set(range(0, 60, 5)), run_at_startup=True),
        cron(cleanup_job, hour=3, minute=17),
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 30 * 60
