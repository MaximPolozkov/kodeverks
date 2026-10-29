"""Учёт площадок (чатов и каналов), где встречаются подходящие запросы."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatPlace


async def upsert_place(
    session: AsyncSession,
    key: str,
    *,
    title: str | None = None,
    url: str | None = None,
    kind: str | None = None,
    found: int = 0,
    bot_added: bool | None = None,
    watch: bool | None = None,
) -> ChatPlace:
    place = await session.scalar(select(ChatPlace).where(ChatPlace.key == key))
    if place is None:
        place = ChatPlace(
            platform="telegram",
            key=key,
            title=title,
            url=url or (f"https://t.me/{key}" if not key.lstrip("-").isdigit() else None),
            kind=kind or "unknown",
            found_count=0,
            bot_added=False,
            watch=False,
            hidden=False,
        )
        session.add(place)
    if title:
        place.title = title
    if url:
        place.url = url
    if kind and kind != "unknown":
        place.kind = kind
    if found:
        place.found_count = (place.found_count or 0) + found
        place.last_found_at = datetime.now(UTC)
    if bot_added is not None:
        place.bot_added = bot_added
    if watch is not None:
        place.watch = watch
    await session.flush()
    return place


async def watched_channels(session: AsyncSession) -> list[str]:
    rows = await session.scalars(
        select(ChatPlace.key).where(ChatPlace.watch.is_(True), ChatPlace.hidden.is_(False))
    )
    return list(rows)
