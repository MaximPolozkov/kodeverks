"""Перевод иностранных заказов на русский через бесплатный MyMemory API.

Без ключа: ~5 000 символов в сутки; с TRANSLATE_EMAIL в .env — ~50 000.
Переводим только заголовок и начало описания уже отобранных заказов.
"""

import logging
import re

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)
API = "https://api.mymemory.translated.net/get"
CHUNK = 450


def _chunks(text: str) -> list[str]:
    parts, cur = [], ""
    for sentence in re.split(r"(?<=[.!?\n])\s+", text):
        if len(cur) + len(sentence) + 1 > CHUNK:
            if cur:
                parts.append(cur)
            cur = sentence[:CHUNK]
        else:
            cur = f"{cur} {sentence}".strip()
    if cur:
        parts.append(cur)
    return parts


async def to_russian(client: httpx.AsyncClient, text: str, source_lang: str = "en") -> str | None:
    """Возвращает перевод или None, если лимит исчерпан/сервис недоступен."""
    out = []
    for part in _chunks(text):
        params = {"q": part, "langpair": f"{source_lang}|ru"}
        if settings.translate_email:
            params["de"] = settings.translate_email
        try:
            resp = await client.get(API, params=params)
            data = resp.json()
        except Exception:  # noqa: BLE001
            return None
        if data.get("responseStatus") != 200:
            log.info("MyMemory: %s", data.get("responseDetails"))
            return None
        out.append(data["responseData"]["translatedText"])
    return " ".join(out)
