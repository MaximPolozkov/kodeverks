from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from app.models.enums import LeadSource


class SourceError(Exception):
    """Ошибка внешнего API — пишется в лог запуска, запуск продолжается."""


@dataclass
class FoundPost:
    source: LeadSource
    external_id: str
    text: str
    author_external_id: str | None = None
    author_name: str | None = None
    profile_url: str | None = None
    post_url: str | None = None
    # Разрешено ли правилами площадки написать автору первыми
    can_contact: bool = False
    published_at: datetime | None = None
    extra: dict = field(default_factory=dict)


class Source(ABC):
    name: LeadSource
    timeout = httpx.Timeout(15.0)

    @property
    @abstractmethod
    def configured(self) -> bool:
        """Заданы ли ключи доступа в настройках."""

    @abstractmethod
    async def search(self, keywords: list[str], limit: int) -> list[FoundPost]:
        """Найти публичные запросы по ключевым словам."""

    async def send_message(self, author_external_id: str, text: str) -> None:
        raise SourceError(f"Источник {self.name} не поддерживает отправку сообщений")

    async def can_message(self, author_external_id: str) -> bool:
        """Разрешил ли пользователь сообщения (проверяется перед первым контактом)."""
        return False
