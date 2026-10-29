from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    app_name: str = "IT Studio"
    environment: str = "dev"

    database_url: str = "postgresql+asyncpg://itstudio:itstudio@db:5432/itstudio"
    redis_url: str = "redis://redis:6379/0"

    # Безопасность
    secret_key: str = "change-me-in-production"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    # Публичный адрес сайта — используется ботом в ссылке на форму заказа
    site_url: str = "http://localhost:8080"

    # Лимит заявок с одного IP в час
    order_rate_limit: int = 5

    media_dir: Path = Path("media")

    first_admin_email: str | None = None
    first_admin_password: str | None = None
    first_admin_name: str = "Администратор"

    # Бот: ключи источников
    vk_user_token: str | None = None  # для поиска (newsfeed.search)
    vk_group_token: str | None = None  # для сообщений от имени сообщества
    vk_group_id: int | None = None
    # Кому присылать уведомления о новых заказах: ID пользователей VK через запятую
    # (каждый должен один раз написать сообществу) или peer_id беседы (2000000000 + id)
    vk_notify_peer_ids: str | None = None
    vk_confirmation_code: str | None = None
    vk_callback_secret: str | None = None
    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None
    # Прокси только для Telegram (http://user:pass@host:port или socks5://...)
    telegram_proxy: str | None = None
    # Альтернативный адрес Bot API (например, свой воркер-прокси)
    telegram_api_base: str = "https://api.telegram.org"
    serpapi_key: str | None = None

    # Бот: LLM (anthropic | openai | none)
    llm_provider: str = "none"
    llm_api_key: str | None = None
    llm_model: str = "claude-sonnet-5-5"
    llm_base_url: str | None = None  # для OpenAI-совместимых API


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
