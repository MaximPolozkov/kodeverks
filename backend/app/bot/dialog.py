"""Логика диалога: первое сообщение, входящие ответы, отказ, переход к заказу."""

import logging
import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bot.llm import ChatTurn, generate_reply
from app.bot.scoring import SERVICE_NAMES, score_text
from app.bot.sources import FoundPost, Source, SourceError, get_source
from app.bot.store import add_to_stoplist, is_stopped, load_settings, new_public_token
from app.core.config import settings
from app.models import BotMessage, Lead, LeadStatus, MessageDirection
from app.schemas.bot import BotSettingsData

log = logging.getLogger(__name__)

OPT_OUT_PATTERNS = [
    r"^\s*стоп\s*[.!]*\s*$",
    r"\bstop\b",
    r"\bне интересн",
    r"\bне пишите\b",
    r"\bне надо\b",
    r"\bотпиш",
    r"\bотстаньте\b",
    r"\bспам\b",
    r"\bunsubscribe\b",
]

READY_PATTERNS = [
    r"\bготов[аы]?\b.*\b(заказ|оформ|начать|работать)",
    r"\bкак (заказать|оформить)\b",
    r"\bкуда (писать|отправить|оставить)\b",
    r"\bдавайте (начн|оформ|работать)",
    r"\bоставлю заявку\b",
    r"\bдоговорились\b",
]

BOT_DISCLOSURE = "Здравствуйте! Я автоматический помощник IT-студии."


def wants_out(text: str) -> bool:
    norm = text.lower().replace("ё", "е")
    return any(re.search(p, norm) for p in OPT_OUT_PATTERNS)


def is_ready(text: str) -> bool:
    norm = text.lower().replace("ё", "е")
    return any(re.search(p, norm) for p in READY_PATTERNS)


def order_link(lead: Lead) -> str:
    return f"{settings.site_url.rstrip('/')}/?ref=bot&lead_id={lead.public_token}#order"


def first_message(lead: Lead, config: BotSettingsData) -> str:
    snippet = re.sub(r"\s+", " ", lead.request_text).strip()
    if len(snippet) > 120:
        snippet = snippet[:117].rstrip() + "…"
    service = SERVICE_NAMES.get(lead.service_guess, "сайты, ботов, CRM и приложения")
    try:
        text = config.first_message_template.format(snippet=snippet, service=service)
    except (KeyError, IndexError, ValueError):
        text = config.first_message_template
    # Бот обязан представиться как бот, даже если шаблон это потерял
    if "бот" not in text.lower() and "автоматическ" not in text.lower():
        text = f"{BOT_DISCLOSURE} {text}"
    if "стоп" not in text.lower():
        text += "\n\nЕсли не интересно, напишите «стоп» — больше не побеспокою."
    return text


async def record(
    session: AsyncSession,
    lead: Lead,
    direction: MessageDirection,
    text: str,
    *,
    manual: bool = False,
    author_id: int | None = None,
) -> BotMessage:
    msg = BotMessage(
        lead_id=lead.id, direction=direction, text=text, is_manual=manual, author_id=author_id
    )
    session.add(msg)
    await session.flush()
    return msg


async def send(
    session: AsyncSession,
    lead: Lead,
    text: str,
    *,
    source: Source | None = None,
    manual: bool = False,
    author_id: int | None = None,
) -> BotMessage:
    if not lead.author_external_id:
        raise SourceError("У лида нет ID автора — написать ему нельзя")
    if lead.status == LeadStatus.opted_out:
        raise SourceError("Клиент отказался от общения")
    source = source or get_source(lead.source)
    await source.send_message(lead.author_external_id, text)
    return await record(
        session, lead, MessageDirection.outgoing, text, manual=manual, author_id=author_id
    )


async def find_or_create_dialog_lead(session: AsyncSession, post: FoundPost) -> Lead:
    """Лид для входящего личного сообщения: последний лид этого автора или новый."""
    lead = await session.scalar(
        select(Lead)
        .where(Lead.source == post.source, Lead.author_external_id == post.author_external_id)
        .order_by(Lead.created_at.desc())
        .limit(1)
    )
    if lead is not None:
        return lead
    _, config = await load_settings(session)
    score = score_text(post.text, config.keywords, [])
    lead = Lead(
        source=post.source,
        external_id=post.external_id,
        author_external_id=post.author_external_id,
        author_name=post.author_name,
        profile_url=post.profile_url,
        post_url=post.post_url,
        request_text=post.text,
        relevance_score=score.value,
        service_guess=score.service,
        status=LeadStatus.replied,
        can_contact=True,
        public_token=new_public_token(),
    )
    session.add(lead)
    await session.flush()
    return lead


async def handle_incoming(session: AsyncSession, post: FoundPost) -> str | None:
    """Обрабатывает входящее личное сообщение. Возвращает отправленный ответ."""
    if not post.author_external_id:
        return None
    lead = await find_or_create_dialog_lead(session, post)
    await record(session, lead, MessageDirection.incoming, post.text)

    if lead.status == LeadStatus.opted_out or await is_stopped(
        session, lead.source, lead.author_external_id
    ):
        await session.commit()
        return None

    if wants_out(post.text):
        await add_to_stoplist(session, lead)
        await session.commit()
        return None

    if lead.status in {LeadStatus.found, LeadStatus.contacted}:
        lead.status = LeadStatus.replied

    if lead.manual_mode:
        # Диалог ведёт менеджер — бот только сохраняет сообщение
        await session.commit()
        return None

    _, config = await load_settings(session)
    await session.refresh(lead, attribute_names=["messages"])
    history = [
        ChatTurn("user" if m.direction == MessageDirection.incoming else "assistant", m.text)
        for m in lead.messages[-20:]
    ]

    reply = await generate_reply(config.system_prompt, history)

    if "[STOP]" in reply:
        await add_to_stoplist(session, lead, reason="Отказ распознан моделью")
        await session.commit()
        return None

    ready = "[READY]" in reply or is_ready(post.text)
    reply = reply.replace("[READY]", "").strip()
    if ready:
        link = order_link(lead)
        if link not in reply:
            reply = (reply + "\n\n" if reply else "") + f"Оставить заявку можно здесь: {link}"
        lead.status = LeadStatus.qualified
        lead.link_sent_at = datetime.now(UTC)

    if not reply:
        await session.commit()
        return None

    try:
        await send(session, lead, reply)
    except SourceError as exc:
        log.warning("Не удалось отправить ответ лиду %s: %s", lead.id, exc)
        await session.commit()
        return None
    await session.commit()
    return reply


async def load_lead_with_messages(session: AsyncSession, lead_id: int) -> Lead | None:
    return await session.scalar(
        select(Lead)
        .where(Lead.id == lead_id)
        .options(selectinload(Lead.messages))
        .execution_options(populate_existing=True)
    )
