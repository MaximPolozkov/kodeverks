"""Генерация ответов бота: Anthropic, OpenAI-совместимый API или сценарий без LLM."""

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant"
    text: str


class LLMError(Exception):
    pass


def llm_configured() -> bool:
    return settings.llm_provider in {"anthropic", "openai"} and bool(settings.llm_api_key)


async def _anthropic(system: str, history: list[ChatTurn]) -> str:
    messages = _merge_turns(history)
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        resp = await client.post(
            (settings.llm_base_url or "https://api.anthropic.com") + "/v1/messages",
            headers={
                "x-api-key": settings.llm_api_key or "",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "max_tokens": 600,
                "system": system,
                "messages": messages,
            },
        )
    if resp.status_code != 200:
        raise LLMError(f"Anthropic API: HTTP {resp.status_code} {resp.text[:200]}")
    blocks = resp.json().get("content", [])
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()


async def _openai(system: str, history: list[ChatTurn]) -> str:
    messages = [{"role": "system", "content": system}, *_merge_turns(history)]
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        resp = await client.post(
            (settings.llm_base_url or "https://api.openai.com/v1") + "/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={"model": settings.llm_model, "messages": messages, "max_tokens": 600},
        )
    if resp.status_code != 200:
        raise LLMError(f"LLM API: HTTP {resp.status_code} {resp.text[:200]}")
    return resp.json()["choices"][0]["message"]["content"].strip()


def _merge_turns(history: list[ChatTurn]) -> list[dict]:
    """API требуют чередования ролей и первое сообщение от пользователя."""
    merged: list[dict] = []
    for turn in history:
        if merged and merged[-1]["role"] == turn.role:
            merged[-1]["content"] += "\n" + turn.text
        else:
            merged.append({"role": turn.role, "content": turn.text})
    if merged and merged[0]["role"] != "user":
        merged.insert(0, {"role": "user", "content": "(начало диалога)"})
    return merged


def _scripted(history: list[ChatTurn]) -> str:
    """Простой сценарий на случай, если LLM не подключена."""
    user_turns = [t for t in history if t.role == "user"]
    if len(user_turns) <= 1:
        return (
            "Спасибо, что ответили! Подскажите, пожалуйста: что именно нужно сделать, "
            "к какому сроку и на какой бюджет вы ориентируетесь?"
        )
    return (
        "Понял задачу, спасибо. Чтобы менеджер подготовил оценку сроков и стоимости, "
        "оставьте заявку на сайте — это займёт пару минут. [READY]"
    )


async def generate_reply(system: str, history: list[ChatTurn]) -> str:
    if not llm_configured():
        return _scripted(history)
    try:
        if settings.llm_provider == "anthropic":
            return await _anthropic(system, history)
        return await _openai(system, history)
    except (LLMError, httpx.HTTPError, KeyError) as exc:
        log.warning("LLM недоступна, используем сценарий: %s", exc)
        return _scripted(history)
