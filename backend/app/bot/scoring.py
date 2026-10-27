"""Оценка релевантности найденного запроса (0–100) и определение типа услуги."""

import re
from dataclasses import dataclass

from app.models.enums import ServiceType

INTENT_PATTERNS = [
    r"\bищу\b",
    r"\bнуж(ен|на|но|ны)\b",
    r"\bтребуется\b",
    r"\bкто (может|сделает|возьмется|возьмётся)\b",
    r"\bсколько стоит\b",
    r"\bпосоветуйте\b",
    r"\bпорекомендуйте\b",
    r"\bхочу (заказать|сделать)\b",
    r"\bзаказать\b",
]

SERVICE_PATTERNS: dict[ServiceType, list[str]] = {
    ServiceType.website: [r"сайт", r"лендинг", r"интернет[- ]магазин", r"landing"],
    ServiceType.bot: [r"бот", r"чат[- ]?бот", r"telegram", r"телеграм"],
    ServiceType.crm: [r"\bcrm\b", r"црм", r"автоматизац", r"учет(а)? (заявок|клиентов)", r"учёт"],
    ServiceType.app: [r"приложени", r"\bapp\b", r"ios", r"android", r"мобильн"],
}

SERVICE_NAMES = {
    ServiceType.website: "сайты",
    ServiceType.bot: "ботов",
    ServiceType.crm: "CRM-системы",
    ServiceType.app: "приложения",
}


@dataclass
class Score:
    value: int
    service: ServiceType | None
    blocked: bool = False


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("ё", "е")).strip()


def score_text(text: str, keywords: list[str], stop_words: list[str]) -> Score:
    norm = _normalize(text)
    if not norm:
        return Score(0, None)

    for word in stop_words:
        if word and _normalize(word) in norm:
            return Score(0, None, blocked=True)

    value = 0
    keyword_hits = sum(1 for k in keywords if k and _normalize(k) in norm)
    value += min(keyword_hits, 2) * 25

    intent_hits = sum(1 for p in INTENT_PATTERNS if re.search(p, norm))
    value += min(intent_hits, 2) * 15

    service: ServiceType | None = None
    best = 0
    for svc, patterns in SERVICE_PATTERNS.items():
        hits = sum(1 for p in patterns if re.search(p, norm))
        if hits > best:
            best, service = hits, svc
    if service:
        value += 15

    # Упоминание бюджета или сроков — признак реальной задачи
    if re.search(r"\d[\d\s]*(₽|руб|р\.|т\.?р|тыс|k\b|к\b)|бюджет|срок", norm):
        value += 10

    # Слишком короткие сообщения обычно малоинформативны
    if len(norm) < 25:
        value -= 15

    return Score(max(0, min(100, value)), service)
