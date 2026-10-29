"""Telegram через Bot API.

Bot API не умеет искать по всему Telegram. Бот видит только:
  * группы, куда его добавили администраторы (сообщения приходят на вебхук) —
    подходящие по ключевым словам сохраняются как лиды;
  * личные сообщения от пользователей, которые сами написали боту.
Писать первым пользователю Telegram-бот не может (это ограничение платформы),
поэтому лиды из групп помечаются can_contact=False — с ними работает менеджер.
"""

import httpx

from app.bot.sources.base import FoundPost, Source, SourceError
from app.bot.sources.tg_web import ChannelPage, fetch_channel, normalize_username
from app.core.config import settings
from app.core.tg_http import tg_api, tg_client
from app.models.enums import LeadSource


class TelegramSource(Source):
    """Два режима: чтение публичных каналов (t.me/s/...) и вебхук для чатов с ботом."""

    name = LeadSource.telegram

    def __init__(self, channels: list[str] | None = None) -> None:
        self.channels = [c for c in (normalize_username(x) for x in channels or []) if c]
        # Заполняется при поиске: какие каналы прочитаны и какие чаты упоминались
        self.pages: dict[str, ChannelPage] = {}

    @property
    def configured(self) -> bool:
        return bool(self.channels or settings.telegram_bot_token)

    async def search(self, keywords: list[str], limit: int) -> list[FoundPost]:
        posts: list[FoundPost] = []
        if not self.channels:
            return posts
        headers = {"User-Agent": "Mozilla/5.0 (compatible; KodverkLeadBot/1.0)", "Accept-Language": "ru"}
        async with tg_client(timeout=self.timeout, headers=headers) as client:
            for username in self.channels:
                try:
                    page = await fetch_channel(client, username)
                except httpx.HTTPError as exc:
                    raise SourceError(f"t.me/s/{username}: {exc}") from exc
                if page is None:
                    continue
                self.pages[username] = page
                for p in page.posts[-limit:]:
                    posts.append(
                        FoundPost(
                            source=self.name,
                            external_id=f"{p.channel}/{p.post_id}",
                            text=p.text,
                            author_name=p.author or page.title,
                            post_url=f"https://t.me/{p.channel}/{p.post_id}",
                            can_contact=False,
                            extra={"place": username, "place_title": page.title, "place_kind": "channel"},
                        )
                    )
        return posts

    async def send_message(self, author_external_id: str, text: str) -> None:
        if not settings.telegram_bot_token:
            raise SourceError("Telegram: не задан TELEGRAM_BOT_TOKEN")
        url = tg_api("sendMessage")
        async with tg_client(timeout=self.timeout) as client:
            resp = await client.post(
                url,
                json={"chat_id": author_external_id, "text": text, "disable_web_page_preview": False},
            )
        body = resp.json()
        if not body.get("ok"):
            raise SourceError(f"Telegram sendMessage: {body.get('description')}")

    async def can_message(self, author_external_id: str) -> bool:
        return False


def parse_update(update: dict) -> tuple[str, FoundPost] | None:
    """Разбирает апдейт Telegram.

    Возвращает ("private", post) для личного сообщения боту или
    ("group", post) для сообщения в группе, иначе None.
    """
    message = update.get("message") or update.get("channel_post")
    if not message or not message.get("text"):
        return None
    chat = message.get("chat", {})
    sender = message.get("from") or {}
    chat_type = chat.get("type")
    name = " ".join(filter(None, [sender.get("first_name"), sender.get("last_name")])) or None
    username = sender.get("username")
    profile_url = f"https://t.me/{username}" if username else None

    if chat_type == "private":
        return "private", FoundPost(
            source=LeadSource.telegram,
            external_id=f"dm_{chat['id']}",
            text=message["text"],
            author_external_id=str(chat["id"]),
            author_name=name,
            profile_url=profile_url,
            can_contact=True,  # пользователь написал сам
        )

    chat_username = chat.get("username")
    post_url = (
        f"https://t.me/{chat_username}/{message['message_id']}" if chat_username else None
    )
    return "group", FoundPost(
        source=LeadSource.telegram,
        external_id=f"{chat['id']}_{message['message_id']}",
        text=message["text"],
        author_external_id=str(sender["id"]) if sender.get("id") else None,
        author_name=name,
        profile_url=profile_url,
        post_url=post_url,
        can_contact=False,
        extra={
            "place": chat_username or str(chat["id"]),
            "place_title": chat.get("title"),
            "place_kind": "channel" if chat_type == "channel" else "group",
            "place_url": f"https://t.me/{chat_username}" if chat_username else None,
            "bot_added": True,
        },
    )


def parse_membership(update: dict) -> dict | None:
    """Бота добавили в чат или удалили из него (апдейт my_chat_member)."""
    member = update.get("my_chat_member")
    if not member:
        return None
    chat = member.get("chat", {})
    status = (member.get("new_chat_member") or {}).get("status")
    username = chat.get("username")
    return {
        "place": username or str(chat.get("id")),
        "place_title": chat.get("title"),
        "place_kind": "channel" if chat.get("type") == "channel" else "group",
        "place_url": f"https://t.me/{username}" if username else None,
        "bot_added": status in {"member", "administrator"},
    }
