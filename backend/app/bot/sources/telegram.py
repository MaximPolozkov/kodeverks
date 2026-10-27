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
from app.core.config import settings
from app.models.enums import LeadSource


class TelegramSource(Source):
    name = LeadSource.telegram

    @property
    def configured(self) -> bool:
        return bool(settings.telegram_bot_token)

    async def search(self, keywords: list[str], limit: int) -> list[FoundPost]:
        # Поиск пассивный: посты приходят через вебхук, см. parse_group_message
        return []

    async def send_message(self, author_external_id: str, text: str) -> None:
        if not settings.telegram_bot_token:
            raise SourceError("Telegram: не задан TELEGRAM_BOT_TOKEN")
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
    )
