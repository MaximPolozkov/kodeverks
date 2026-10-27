"""Работа с настройками, стоп-листом и лимитами бота."""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BotMessage,
    BotSettings,
    BotStopList,
    Lead,
    LeadSource,
    LeadStatus,
    MessageDirection,
)
from app.schemas.bot import BotSettingsData

SETTINGS_ID = 1


async def get_settings_row(session: AsyncSession) -> BotSettings:
    row = await session.get(BotSettings, SETTINGS_ID)
    if row is None:
        row = BotSettings(
            id=SETTINGS_ID, enabled=False, data=BotSettingsData().model_dump(mode="json")
        )
        session.add(row)
        await session.flush()
    return row


async def load_settings(session: AsyncSession) -> tuple[bool, BotSettingsData]:
    row = await get_settings_row(session)
    # Новые поля, появившиеся в коде, получают значения по умолчанию
    return row.enabled, BotSettingsData.model_validate(row.data or {})


def new_public_token() -> str:
    return secrets.token_urlsafe(24)


async def is_stopped(session: AsyncSession, source: LeadSource, author_id: str | None) -> bool:
    if not author_id:
        return False
    return (
        await session.scalar(
            select(BotStopList.id).where(
                BotStopList.source == source, BotStopList.author_external_id == author_id
            )
        )
        is not None
    )


async def add_to_stoplist(
    session: AsyncSession, lead: Lead, reason: str = "Клиент отказался"
) -> None:
    lead.status = LeadStatus.opted_out
    lead.manual_mode = True
    if lead.author_external_id and not await is_stopped(
        session, lead.source, lead.author_external_id
    ):
        session.add(
            BotStopList(
                source=lead.source, author_external_id=lead.author_external_id, reason=reason
            )
        )


async def outgoing_count(session: AsyncSession, source: LeadSource, since: datetime) -> int:
    """Количество автоматических исходящих сообщений бота по источнику."""
    return (
        await session.scalar(
            select(func.count())
            .select_from(BotMessage)
            .join(Lead, Lead.id == BotMessage.lead_id)
            .where(
                Lead.source == source,
                BotMessage.direction == MessageDirection.outgoing,
                BotMessage.is_manual.is_(False),
                BotMessage.created_at >= since,
            )
        )
        or 0
    )


async def within_limits(
    session: AsyncSession, source: LeadSource, config: BotSettingsData
) -> bool:
    limits = config.sources.get(source)
    if limits is None or not limits.enabled:
        return False
    now = datetime.now(UTC)
    if await outgoing_count(session, source, now - timedelta(hours=1)) >= limits.per_hour:
        return False
    if await outgoing_count(session, source, now - timedelta(days=1)) >= limits.per_day:
        return False
    return True
