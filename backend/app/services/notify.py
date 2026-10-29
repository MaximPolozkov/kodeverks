"""Уведомление менеджеров о новом заказе сообщением от бота сообщества ВКонтакте.

Сообщение приходит в обычные личные сообщения VK (vk.ru/im) — от имени сообщества.
Под текстом две кнопки: «Открыть заказ» (карточка в /admin) и «Написать клиенту»
(ссылка на выбранный клиентом канал связи).
"""

import json
import logging
import random
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import ContactChannel, Order
from app.services.contacts import CHANNEL_LABELS, contact_url

log = logging.getLogger(__name__)
VK_API = "https://api.vk.com/method/messages.send"

SERVICE_NAMES = {"website": "Сайт", "bot": "Бот", "crm": "CRM-система", "app": "Приложение"}
SOURCE_NAMES = {"site": "сайт", "bot": "бот", "utm": "реклама"}


@dataclass
class OrderSnapshot:
    id: int
    name: str
    email: str
    budget: str
    description: str
    service_type: str | None
    source: str
    utm_source: str | None
    contact_channel: ContactChannel
    contact_value: str | None

    @classmethod
    def of(cls, order: Order) -> "OrderSnapshot":
        return cls(
            id=order.id,
            name=order.name,
            email=order.email,
            budget=f"{int(order.budget):,}".replace(",", " ") + " ₽",
            description=order.description,
            service_type=order.service_type,
            source=order.source,
            utm_source=order.utm_source,
            contact_channel=ContactChannel(order.contact_channel),
            contact_value=order.contact_value,
        )


def raw_peers() -> list[str]:
    """Получатели из настроек: числовые ID, короткие имена (maxim198423) или ссылки vk.ru/…"""
    raw = settings.vk_notify_peer_ids or ""
    out = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip().rstrip("/")
        for prefix in ("https://", "http://", "m.", "vk.com/", "vk.ru/"):
            if part.startswith(prefix):
                part = part[len(prefix):]
        if part.startswith("id") and part[2:].isdigit():
            part = part[2:]
        if part:
            out.append(part)
    return out


def peer_ids() -> list[str]:
    return list(_resolved) if _resolved else [p for p in raw_peers() if p.isdigit()]


_resolved: list[str] = []


async def resolve_peers(client: httpx.AsyncClient) -> list[str]:
    """Переводит короткие имена в числовые ID (один раз за запуск процесса)."""
    global _resolved
    names = raw_peers()
    numeric = [p for p in names if p.isdigit()]
    screen = [p for p in names if not p.isdigit()]
    if screen:
        resp = await client.post(
            "https://api.vk.com/method/users.get",
            data={"access_token": settings.vk_group_token, "v": "5.199", "user_ids": ",".join(screen)},
        )
        numeric += [str(u["id"]) for u in resp.json().get("response", [])]
    _resolved = numeric
    return numeric


def notifications_enabled() -> bool:
    return bool(settings.vk_group_token and raw_peers())


def build_message(o: OrderSnapshot) -> tuple[str, dict]:
    description = o.description if len(o.description) <= 700 else o.description[:697] + "…"
    channel = CHANNEL_LABELS[o.contact_channel]
    contact = o.contact_value or o.email
    source = SOURCE_NAMES.get(o.source, o.source)
    if o.utm_source:
        source += f" ({o.utm_source})"
    text = "\n".join(
        [
            f"🆕 Новый заказ №{o.id}",
            "",
            f"Клиент: {o.name}",
            f"Услуга: {SERVICE_NAMES.get(o.service_type or '', 'не выбрана')}",
            f"Бюджет: {o.budget}",
            f"Источник: {source}",
            "",
            f"Удобная связь: {channel} — {contact}",
            f"Почта: {o.email}",
            "",
            "Задача:",
            description,
        ]
    )
    admin_link = f"{settings.site_url.rstrip('/')}/admin/orders/{o.id}"
    client_link = contact_url(o.contact_channel, o.contact_value, o.email)
    row = [{"action": {"type": "open_link", "link": admin_link, "label": "Открыть заказ"}}]
    # Кнопка VK принимает только http(s); почту и телефон менеджер видит в тексте
    if client_link.startswith("https://"):
        row.append({"action": {"type": "open_link", "link": client_link, "label": f"Написать в {channel}"[:40]}})
    keyboard = {"inline": True, "buttons": [[b] for b in row]}
    return text, keyboard


async def send_vk(text: str, keyboard: dict) -> None:
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        if not _resolved:
            await resolve_peers(client)
        resp = await client.post(
            VK_API,
            data={
                "access_token": settings.vk_group_token,
                "v": "5.199",
                "peer_ids": ",".join(peer_ids()),
                "random_id": random.randint(1, 2**31 - 1),
                "message": text,
                "keyboard": json.dumps(keyboard, ensure_ascii=False),
                "dont_parse_links": 1,
            },
        )
    body = resp.json()
    if "error" in body:
        err = body["error"]
        raise RuntimeError(f"VK messages.send: {err.get('error_code')} {err.get('error_msg')}")
    # По каждому получателю VK возвращает отдельный результат
    for item in body.get("response", []) if isinstance(body.get("response"), list) else []:
        if "error" in item:
            log.warning("VK: не доставлено %s — %s (напишите сообществу, чтобы разрешить сообщения)",
                        item.get("peer_id"), item["error"].get("description"))


async def notify_new_order(snapshot: OrderSnapshot) -> bool:
    """Запускается в фоне после ответа клиенту. Ошибки не мешают приёму заявки."""
    if not notifications_enabled():
        return False
    try:
        await send_vk(*build_message(snapshot))
    except Exception:  # noqa: BLE001
        log.exception("Не удалось отправить уведомление о заказе №%s во ВКонтакте", snapshot.id)
        return False
    try:
        async with SessionLocal() as session:
            order = await session.get(Order, snapshot.id)
            if order:
                order.vk_notified_at = datetime.now(UTC)
                await session.commit()
    except Exception:  # noqa: BLE001
        log.exception("Не удалось отметить уведомление заказа №%s", snapshot.id)
    return True


SERVICE_LABELS = {"website": "сайт", "bot": "бот", "crm": "CRM", "app": "приложение"}


async def notify_new_lead(lead_id: int, text: str, score: int, service: str | None,
                          post_url: str | None, place_title: str | None) -> bool:
    """Оповещение во ВКонтакте о найденном подходящем запросе."""
    if not notifications_enabled():
        return False
    snippet = text if len(text) <= 500 else text[:497] + "…"
    lines = [f"🔎 Найден запрос №{lead_id} (релевантность {score})"]
    if place_title:
        lines.append(f"Где: {place_title}")
    if service:
        lines.append(f"Похоже на: {SERVICE_LABELS.get(service, service)}")
    lines += ["", snippet]
    buttons = []
    if post_url and post_url.startswith("https://"):
        buttons.append([{"action": {"type": "open_link", "link": post_url, "label": "Открыть сообщение"}}])
    buttons.append([{"action": {"type": "open_link",
                                "link": f"{settings.site_url.rstrip('/')}/admin/bot/leads/{lead_id}",
                                "label": "Лид в админке"}}])
    try:
        await send_vk("\n".join(lines), {"inline": True, "buttons": buttons})
        return True
    except Exception:  # noqa: BLE001
        log.exception("Не удалось отправить оповещение о лиде №%s", lead_id)
        return False
