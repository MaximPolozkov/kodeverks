"""VK: поиск публичных постов через newsfeed.search и сообщения от имени сообщества.

Писать первыми можно только пользователям, которые разрешили сообщения от
сообщества (messages.isMessagesFromGroupAllowed) — это правило VK.
"""

import random
from datetime import UTC, datetime

import httpx

from app.bot.sources.base import FoundPost, Source, SourceError
from app.core.config import settings
from app.models.enums import LeadSource

API_URL = "https://api.vk.com/method/"
API_VERSION = "5.199"


class VKSource(Source):
    name = LeadSource.vk

    @property
    def configured(self) -> bool:
        return bool(settings.vk_user_token or settings.vk_group_token)

    async def _call(self, method: str, token: str | None, **params) -> dict | list | int:
        if not token:
            raise SourceError(f"VK: не задан токен для метода {method}")
        params.update(access_token=token, v=API_VERSION)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(API_URL + method, data=params)
        resp.raise_for_status()
        body = resp.json()
        if "error" in body:
            err = body["error"]
            raise SourceError(f"VK {method}: {err.get('error_code')} {err.get('error_msg')}")
        return body["response"]

    async def search(self, keywords: list[str], limit: int) -> list[FoundPost]:
        if not settings.vk_user_token:
            return []
        per_keyword = max(1, min(200, limit // max(1, len(keywords)) or 1))
        found: dict[str, FoundPost] = {}
        for keyword in keywords:
            data = await self._call(
                "newsfeed.search",
                settings.vk_user_token,
                q=keyword,
                count=per_keyword,
                extended=1,
            )
            profiles = {p["id"]: p for p in data.get("profiles", [])}
            for item in data.get("items", []):
                owner_id = item.get("owner_id")
                from_id = item.get("from_id", owner_id)
                post_id = item.get("id")
                if owner_id is None or post_id is None:
                    continue
                key = f"{owner_id}_{post_id}"
                author = profiles.get(from_id)
                is_person = from_id is not None and from_id > 0
                found[key] = FoundPost(
                    source=self.name,
                    external_id=key,
                    text=item.get("text", ""),
                    author_external_id=str(from_id) if is_person else None,
                    author_name=(
                        f"{author.get('first_name', '')} {author.get('last_name', '')}".strip()
                        if author
                        else None
                    ),
                    profile_url=f"https://vk.com/id{from_id}" if is_person else None,
                    post_url=f"https://vk.com/wall{key}",
                    can_contact=False,  # уточняется через can_message перед отправкой
                    published_at=datetime.fromtimestamp(item["date"], UTC) if "date" in item else None,
                )
            if len(found) >= limit:
                break
        return list(found.values())[:limit]

    async def can_message(self, author_external_id: str) -> bool:
        if not (settings.vk_group_token and settings.vk_group_id):
            return False
        data = await self._call(
            "messages.isMessagesFromGroupAllowed",
            settings.vk_group_token,
            group_id=settings.vk_group_id,
            user_id=author_external_id,
        )
        return bool(isinstance(data, dict) and data.get("is_allowed"))

    async def send_message(self, author_external_id: str, text: str) -> None:
        await self._call(
            "messages.send",
            settings.vk_group_token,
            user_id=author_external_id,
            message=text,
            random_id=random.randint(1, 2**31 - 1),
        )
