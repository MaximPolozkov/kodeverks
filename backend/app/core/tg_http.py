"""HTTP-клиент для Telegram: через TELEGRAM_PROXY, если задан."""
import httpx

from app.core.config import settings


def tg_client(**kwargs) -> httpx.AsyncClient:
    if settings.telegram_proxy:
        kwargs.setdefault("proxy", settings.telegram_proxy)
    return httpx.AsyncClient(**kwargs)


def tg_api(method: str) -> str:
    base = settings.telegram_api_base.rstrip("/")
    return f"{base}/bot{settings.telegram_bot_token}/{method}"
