"""Один запуск поиска лидов по всем включённым источникам."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.dialog import first_message, send
from app.bot.scoring import score_text
from app.bot.sources import FoundPost, SourceError, get_source
from app.bot.store import is_stopped, load_settings, new_public_token, within_limits
from app.models import BotRun, Lead, LeadSource, LeadStatus
from app.schemas.bot import BotSettingsData

log = logging.getLogger(__name__)
MAX_LOG_LINES = 200


class RunLog:
    def __init__(self, run: BotRun) -> None:
        self.run = run
        self.lines: list[dict] = []

    def add(self, level: str, text: str) -> None:
        log.log(logging.WARNING if level == "error" else logging.INFO, text)
        self.lines.append({"at": datetime.now(UTC).isoformat(), "level": level, "text": text})
        self.run.log = self.lines[-MAX_LOG_LINES:]


async def save_post_as_lead(
    session: AsyncSession, post: FoundPost, config: BotSettingsData
) -> Lead | None:
    """Сохраняет пост как лид, если он релевантен и ещё не встречался."""
    exists = await session.scalar(
        select(Lead.id).where(Lead.source == post.source, Lead.external_id == post.external_id)
    )
    if exists is not None:
        return None
    if await is_stopped(session, post.source, post.author_external_id):
        return None
    score = score_text(post.text, config.keywords, config.stop_words)
    if score.blocked or score.value < config.min_score:
        return None
    lead = Lead(
        source=post.source,
        external_id=post.external_id,
        author_external_id=post.author_external_id,
        author_name=post.author_name,
        profile_url=post.profile_url,
        post_url=post.post_url,
        request_text=post.text[:5000],
        relevance_score=score.value,
        service_guess=score.service,
        status=LeadStatus.found,
        can_contact=post.can_contact,
        public_token=new_public_token(),
    )
    session.add(lead)
    await session.flush()
    return lead


async def run_search(session: AsyncSession, *, force: bool = False) -> BotRun | None:
    enabled, config = await load_settings(session)
    if not enabled and not force:
        return None

    running = await session.scalar(
        select(BotRun.id).where(
            BotRun.finished_at.is_(None),
            BotRun.started_at > datetime.now(UTC) - timedelta(hours=1),
        )
    )
    if running is not None:
        return None

    run = BotRun(found_count=0, contacted_count=0, errors=0, log=[])
    session.add(run)
    await session.commit()
    logger = RunLog(run)
    logger.add("info", "Запуск поиска")

    for source_name, limits in config.sources.items():
        if not limits.enabled:
            continue
        source = get_source(LeadSource(source_name), config.web_sites)
        if not source.configured:
            hint = " (нужен VK_USER_TOKEN — ключ пользователя)" if source_name == LeadSource.vk else ""
            logger.add("info", f"{source_name}: ключи не заданы, пропускаю{hint}")
            continue
        try:
            posts = await source.search(config.keywords, config.search_limit)
        except (SourceError, Exception) as exc:  # noqa: BLE001 — один источник не должен ронять запуск
            run.errors += 1
            logger.add("error", f"{source_name}: ошибка поиска — {exc}")
            await session.commit()
            continue

        new_leads = 0
        for post in posts:
            lead = await save_post_as_lead(session, post, config)
            if lead is None:
                continue
            new_leads += 1
            run.found_count += 1

            if not (config.auto_contact and lead.author_external_id):
                continue
            if not await within_limits(session, lead.source, config):
                continue
            try:
                if not await source.can_message(lead.author_external_id):
                    continue
                lead.can_contact = True
                await send(session, lead, first_message(lead, config), source=source)
                lead.status = LeadStatus.contacted
                run.contacted_count += 1
                logger.add("info", f"{source_name}: написал лиду #{lead.id}")
            except SourceError as exc:
                run.errors += 1
                logger.add("error", f"{source_name}: не удалось написать лиду #{lead.id} — {exc}")
            await session.commit()

        logger.add("info", f"{source_name}: найдено {len(posts)}, новых лидов {new_leads}")
        await session.commit()

    run.finished_at = datetime.now(UTC)
    logger.add("info", "Запуск завершён")
    await session.commit()
    return run


async def cleanup_old_leads(session: AsyncSession) -> int:
    """Удаляет старые неконвертированные лиды (срок хранения задаётся в настройках)."""
    _, config = await load_settings(session)
    border = datetime.now(UTC) - timedelta(days=config.retention_days)
    result = await session.execute(
        delete(Lead).where(Lead.created_at < border, Lead.status != LeadStatus.converted)
    )
    await session.commit()
    return result.rowcount or 0


async def due_for_run(session: AsyncSession) -> bool:
    enabled, config = await load_settings(session)
    if not enabled:
        return False
    last = await session.scalar(select(BotRun.started_at).order_by(BotRun.started_at.desc()).limit(1))
    if last is None:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return datetime.now(UTC) - last >= timedelta(minutes=config.schedule_minutes)
