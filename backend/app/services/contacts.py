"""Канал связи с клиентом: проверка, нормализация и ссылка для перехода."""

import re
from urllib.parse import quote

from app.models.enums import ContactChannel

CHANNEL_LABELS = {
    ContactChannel.email: "Почта",
    ContactChannel.telegram: "Telegram",
    ContactChannel.vk: "ВКонтакте",
    ContactChannel.whatsapp: "WhatsApp",
    ContactChannel.phone: "Звонок",
}

_TG_USERNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")
_VK_NAME = re.compile(r"^(id\d+|[A-Za-z0-9_.]{3,64})$")


def normalize_phone(value: str) -> str | None:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "7" + digits
    return "+" + digits if 10 <= len(digits) <= 15 else None


def normalize_contact(channel: ContactChannel, value: str | None) -> str | None:
    """Возвращает нормализованное значение или бросает ValueError с понятным текстом."""
    value = (value or "").strip()
    if channel == ContactChannel.email:
        return value or None  # по умолчанию используется email из формы
    if not value:
        raise ValueError("Укажите контакт для выбранного способа связи")

    if channel == ContactChannel.telegram:
        name = re.sub(r"^(https?://)?(t\.me/|telegram\.me/)", "", value).lstrip("@").strip("/")
        if _TG_USERNAME.match(name):
            return "@" + name
        phone = normalize_phone(value)
        if phone:
            return phone
        raise ValueError("Укажите ник в Telegram (например, @ivan_petrov) или номер телефона")

    if channel == ContactChannel.vk:
        name = re.sub(r"^(https?://)?(m\.)?(vk\.com|vk\.ru)/", "", value).lstrip("@").strip("/")
        if _VK_NAME.match(name):
            return name
        raise ValueError("Укажите ссылку на страницу ВКонтакте, например vk.com/ivan_petrov")

    phone = normalize_phone(value)
    if not phone:
        raise ValueError("Укажите номер телефона, например +7 912 345-67-89")
    return phone


def contact_url(channel: ContactChannel, value: str | None, email: str) -> str:
    """Ссылка, по которой менеджер сразу откроет диалог с клиентом."""
    if channel == ContactChannel.email or not value:
        return f"mailto:{quote(value or email, safe='@.+')}"
    if channel == ContactChannel.telegram:
        return f"https://t.me/{value.lstrip('@')}" if value.startswith("@") else f"https://t.me/{value}"
    if channel == ContactChannel.vk:
        return f"https://vk.com/{value}"
    if channel == ContactChannel.whatsapp:
        return f"https://wa.me/{value.lstrip('+')}"
    return f"tel:{value}"
