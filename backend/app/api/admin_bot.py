from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import desc, func, or_, select

from app.bot import dialog
from app.bot.llm import llm_configured
from app.bot.sources import SourceError, get_source
from app.bot.store import get_settings_row, load_settings
from app.core.config import settings
from app.core.deps import SessionDep, StaffUser
from app.models import BotMessage, BotRun, ChatPlace, Lead, LeadSource, LeadStatus, MessageDirection
from app.schemas.bot import (
    BotMessageOut,
    BotRunOut,
    BotSettingsData,
    BotSettingsOut,
    BotStatus,
    FunnelStats,
    LeadOut,
    LeadUpdate,
    ManualMessageIn,
    PlaceOut,
    PlacesOut,
    PlaceUpdate,
)
from app.schemas.common import Page

router = APIRouter(prefix="/api/admin/bot", tags=["admin: bot"])


async def _enqueue_search() -> bool:
    """Ставит задачу поиска в очередь воркера. False — если Redis недоступен."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(
            RedisSettings.from_dsn(settings.redis_url), retry=0
        )
        try:
            await pool.enqueue_job("search_job", True)
        finally:
            await pool.aclose()
        return True
    except Exception:  # noqa: BLE001
        return False


# --- Настройки и управление ---


@router.get("/settings", response_model=BotSettingsOut)
async def get_bot_settings(session: SessionDep, _: StaffUser) -> BotSettingsOut:
    row = await get_settings_row(session)
    await session.commit()
    return BotSettingsOut(
        enabled=row.enabled,
        data=BotSettingsData.model_validate(row.data or {}),
        updated_at=row.updated_at,
    )


@router.put("/settings", response_model=BotSettingsOut)
async def update_bot_settings(
    data: BotSettingsData, session: SessionDep, _: StaffUser
) -> BotSettingsOut:
    row = await get_settings_row(session)
    data.keywords = [k.strip() for k in data.keywords if k.strip()]
    data.stop_words = [w.strip() for w in data.stop_words if w.strip()]
    row.data = data.model_dump(mode="json")
    await session.commit()
    await session.refresh(row)
    return BotSettingsOut(enabled=row.enabled, data=data, updated_at=row.updated_at)


@router.get("/status", response_model=BotStatus)
async def bot_status(session: SessionDep, _: StaffUser) -> BotStatus:
    enabled, config = await load_settings(session)
    await session.commit()
    last = await session.scalar(select(BotRun).order_by(desc(BotRun.started_at)).limit(1))
    return BotStatus(
        enabled=enabled,
        running=bool(last and last.finished_at is None),
        worker_available=await _redis_alive(),
        last_run=BotRunOut.model_validate(last) if last else None,
        sources_configured={
            s.value: get_source(s, config.web_sites, config.tg_channels).configured for s in LeadSource
        },
        llm_configured=llm_configured(),
    )


async def _redis_alive() -> bool:
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        try:
            return bool(await client.ping())
        finally:
            await client.aclose()
    except Exception:  # noqa: BLE001
        return False


@router.post("/start", response_model=BotStatus)
async def start_bot(session: SessionDep, user: StaffUser) -> BotStatus:
    row = await get_settings_row(session)
    row.enabled = True
    await session.commit()
    await _enqueue_search()
    return await bot_status(session, user)


@router.post("/stop", response_model=BotStatus)
async def stop_bot(session: SessionDep, user: StaffUser) -> BotStatus:
    row = await get_settings_row(session)
    row.enabled = False
    await session.commit()
    return await bot_status(session, user)


@router.post("/run-now", response_model=BotStatus)
async def run_now(session: SessionDep, user: StaffUser) -> BotStatus:
    if not await _enqueue_search():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Воркер недоступен: проверьте, что запущены Redis и сервис worker",
        )
    return await bot_status(session, user)


@router.get("/runs", response_model=list[BotRunOut])
async def list_runs(
    session: SessionDep, _: StaffUser, limit: int = Query(default=20, ge=1, le=100)
) -> list[BotRun]:
    return list(await session.scalars(select(BotRun).order_by(desc(BotRun.started_at)).limit(limit)))


# --- Лиды и переписка ---


@router.get("/leads", response_model=Page[LeadOut])
async def list_leads(
    session: SessionDep,
    _: StaffUser,
    status_: LeadStatus | None = Query(default=None, alias="status"),
    source: LeadSource | None = None,
    min_score: int = Query(default=0, ge=0, le=100),
    q: str | None = Query(default=None, max_length=200),
    sort: Literal["created_at", "relevance_score"] = "created_at",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[LeadOut]:
    stmt = select(Lead).where(Lead.relevance_score >= min_score)
    if status_:
        stmt = stmt.where(Lead.status == status_)
    if source:
        stmt = stmt.where(Lead.source == source)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(Lead.request_text.ilike(pattern), Lead.author_name.ilike(pattern)))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = Lead.relevance_score if sort == "relevance_score" else Lead.created_at
    rows = await session.scalars(
        stmt.order_by(desc(column), desc(Lead.id)).offset((page - 1) * page_size).limit(page_size)
    )
    return Page(
        items=[LeadOut.model_validate(r) for r in rows], total=total, page=page, page_size=page_size
    )


async def _lead_or_404(session, lead_id: int) -> Lead:
    lead = await dialog.load_lead_with_messages(session, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Лид не найден")
    return lead


@router.get("/leads/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: int, session: SessionDep, _: StaffUser) -> Lead:
    return await _lead_or_404(session, lead_id)


@router.patch("/leads/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: int, data: LeadUpdate, session: SessionDep, _: StaffUser
) -> Lead:
    lead = await _lead_or_404(session, lead_id)
    if data.status is not None:
        if data.status == LeadStatus.opted_out:
            await dialog.add_to_stoplist(session, lead, reason="Отмечено менеджером")
        else:
            lead.status = data.status
    if data.manual_mode is not None:
        lead.manual_mode = data.manual_mode
    await session.commit()
    return await _lead_or_404(session, lead_id)


@router.get("/leads/{lead_id}/messages", response_model=list[BotMessageOut])
async def lead_messages(lead_id: int, session: SessionDep, _: StaffUser) -> list[BotMessage]:
    lead = await _lead_or_404(session, lead_id)
    return lead.messages


@router.post(
    "/leads/{lead_id}/messages",
    response_model=list[BotMessageOut],
    status_code=status.HTTP_201_CREATED,
)
async def send_manual(
    lead_id: int, data: ManualMessageIn, session: SessionDep, user: StaffUser
) -> list[BotMessage]:
    lead = await _lead_or_404(session, lead_id)
    lead.manual_mode = True  # менеджер перехватил диалог
    try:
        await dialog.send(session, lead, data.text.strip(), manual=True, author_id=user.id)
    except SourceError as exc:
        await session.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Сообщение не отправлено: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — сетевые ошибки внешнего API
        await session.rollback()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Площадка не ответила, попробуйте ещё раз"
        ) from exc
    if lead.status in {LeadStatus.found}:
        lead.status = LeadStatus.contacted
    await session.commit()
    return (await _lead_or_404(session, lead_id)).messages


# --- Статистика ---


@router.get("/stats", response_model=FunnelStats)
async def funnel(session: SessionDep, _: StaffUser) -> FunnelStats:
    async def count(*conditions) -> int:
        return await session.scalar(select(func.count()).select_from(Lead).where(*conditions)) or 0

    contacted_ids = select(BotMessage.lead_id).where(
        BotMessage.direction == MessageDirection.outgoing
    )
    replied_ids = select(BotMessage.lead_id).where(
        BotMessage.direction == MessageDirection.incoming
    )
    by_source_rows = await session.execute(
        select(Lead.source, func.count()).group_by(Lead.source)
    )
    return FunnelStats(
        found=await count(),
        contacted=await count(Lead.id.in_(contacted_ids)),
        replied=await count(Lead.id.in_(replied_ids)),
        link_sent=await count(Lead.link_sent_at.is_not(None)),
        converted=await count(Lead.status == LeadStatus.converted),
        opted_out=await count(Lead.status == LeadStatus.opted_out),
        by_source={str(src): n for src, n in by_source_rows.all()},
    )


# --- Площадки (чаты и каналы) ---

_bot_username: str | None = None


async def _get_bot_username() -> str | None:
    global _bot_username
    if _bot_username or not settings.telegram_bot_token:
        return _bot_username
    try:
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            body = (await client.get(f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe")).json()
        _bot_username = body.get("result", {}).get("username")
    except Exception:  # noqa: BLE001
        return None
    return _bot_username


@router.get("/places", response_model=PlacesOut)
async def list_places(
    session: SessionDep, _: StaffUser, show_hidden: bool = False
) -> PlacesOut:
    stmt = select(ChatPlace)
    if not show_hidden:
        stmt = stmt.where(ChatPlace.hidden.is_(False))
    rows = await session.scalars(
        stmt.order_by(desc(ChatPlace.found_count), desc(ChatPlace.bot_added), desc(ChatPlace.id)).limit(500)
    )
    return PlacesOut(
        items=[PlaceOut.model_validate(r) for r in rows], bot_username=await _get_bot_username()
    )


@router.patch("/places/{place_id}", response_model=PlaceOut)
async def update_place(
    place_id: int, data: PlaceUpdate, session: SessionDep, _: StaffUser
) -> ChatPlace:
    place = await session.get(ChatPlace, place_id)
    if place is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Площадка не найдена")
    if data.watch is not None:
        place.watch = data.watch
    if data.hidden is not None:
        place.hidden = data.hidden
    await session.commit()
    await session.refresh(place)
    return place
