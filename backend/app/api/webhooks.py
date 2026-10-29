"""Вебхуки мессенджеров. Ответ отдаётся сразу, обработка — в фоне."""

import hmac
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from app.bot.dialog import handle_incoming
from app.bot.runner import save_post_as_lead
from app.bot.sources import FoundPost
from app.bot.sources.telegram import parse_membership, parse_update
from app.services.places import upsert_place
from app.bot.store import load_settings
from app.core.config import settings
from app.core.db import SessionLocal
from app.models import LeadSource

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
log = logging.getLogger(__name__)


def _same(a: str | None, b: str | None) -> bool:
    return bool(a and b) and hmac.compare_digest(a, b)


async def _process_private(post: FoundPost) -> None:
    async with SessionLocal() as session:
        try:
            await handle_incoming(session, post)
        except Exception:  # noqa: BLE001
            log.exception("Ошибка обработки входящего сообщения")
            await session.rollback()


async def _process_group(post: FoundPost) -> None:
    async with SessionLocal() as session:
        enabled, config = await load_settings(session)
        # Бот получает сообщения из чата — значит он там есть
        await upsert_place(
            session, post.extra["place"], title=post.extra.get("place_title"),
            url=post.extra.get("place_url"), kind=post.extra.get("place_kind"), bot_added=True,
        )
        limits = config.sources.get(LeadSource.telegram)
        if enabled and limits and limits.enabled:
            await save_post_as_lead(session, post, config)
        await session.commit()


async def _process_membership(info: dict) -> None:
    async with SessionLocal() as session:
        await upsert_place(
            session, info["place"], title=info.get("place_title"), url=info.get("place_url"),
            kind=info.get("place_kind"), bot_added=info["bot_added"],
        )
        await session.commit()


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    background: BackgroundTasks,
    secret: Annotated[str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = None,
) -> dict:
    if not _same(secret, settings.telegram_webhook_secret):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Неверный секрет")
    update = await request.json()
    membership = parse_membership(update)
    if membership is not None:
        background.add_task(_process_membership, membership)
        return {"ok": True}
    parsed = parse_update(update)
    if parsed is not None:
        kind, post = parsed
        background.add_task(_process_private if kind == "private" else _process_group, post)
    return {"ok": True}


@router.post("/vk")
async def vk_webhook(request: Request, background: BackgroundTasks) -> PlainTextResponse:
    body = await request.json()
    if settings.vk_group_id and body.get("group_id") != settings.vk_group_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Чужое сообщество")
    if body.get("type") == "confirmation":
        return PlainTextResponse(settings.vk_confirmation_code or "")
    if not _same(body.get("secret"), settings.vk_callback_secret):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Неверный секрет")

    if body.get("type") == "message_new":
        message = body.get("object", {}).get("message", {})
        from_id = message.get("from_id")
        text = message.get("text")
        if from_id and from_id > 0 and text:
            background.add_task(
                _process_private,
                FoundPost(
                    source=LeadSource.vk,
                    external_id=f"dm_{from_id}",
                    text=text,
                    author_external_id=str(from_id),
                    profile_url=f"https://vk.com/id{from_id}",
                    can_contact=True,
                ),
            )
    # VK ждёт строку "ok", иначе будет повторять запрос
    return PlainTextResponse("ok")
