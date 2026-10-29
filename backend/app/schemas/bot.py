from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import LeadSource, LeadStatus, MessageDirection, ServiceType
from app.schemas.common import ORMModel

DEFAULT_SYSTEM_PROMPT = (
    "Ты — автоматический помощник IT-студии, которая разрабатывает сайты, ботов, "
    "CRM-системы и приложения. Всегда честно говори, что ты бот. Пиши коротко, "
    "вежливо, на «вы», без давления и без обещаний конкретной цены. Твоя задача — "
    "понять задачу клиента: что нужно сделать, сроки, примерный бюджет. Не проси "
    "паспортные данные, телефоны третьих лиц и другие лишние персональные данные. "
    "Если клиент готов оформить заказ или просит, куда отправить заявку, добавь в "
    "конец ответа маркер [READY]. Если клиент просит больше не писать — добавь "
    "маркер [STOP] и ничего больше не предлагай."
)

DEFAULT_FIRST_MESSAGE = (
    "Здравствуйте! Я автоматический помощник IT-студии. Увидел ваш запрос: «{snippet}». "
    "Мы делаем {service} под ключ. Если актуально — расскажите чуть подробнее о задаче, "
    "и я подскажу сроки. Если не интересно, просто напишите «стоп», и я больше не побеспокою."
)


class SourceLimits(BaseModel):
    enabled: bool = True
    per_hour: int = Field(default=5, ge=0, le=100)
    per_day: int = Field(default=30, ge=0, le=1000)


class BotSettingsData(BaseModel):
    keywords: list[str] = Field(
        default_factory=lambda: [
            "нужен сайт",
            "ищу разработчика",
            "сделать сайт",
            "нужен телеграм бот",
            "разработать бота",
            "внедрить crm",
            "нужна crm",
            "разработка приложения",
        ]
    )
    stop_words: list[str] = Field(
        default_factory=lambda: ["вакансия", "резюме", "ищу работу", "бесплатно", "даром"]
    )
    sources: dict[LeadSource, SourceLimits] = Field(
        default_factory=lambda: {
            LeadSource.vk: SourceLimits(),
            LeadSource.telegram: SourceLimits(per_hour=0, per_day=0),  # писать первым в TG нельзя
            LeadSource.web: SourceLimits(per_hour=0, per_day=0),
        }
    )
    web_sites: list[str] = Field(default_factory=list, description="Домены для поиска через SerpAPI")
    tg_channels: list[str] = Field(
        default_factory=lambda: [
            "zakazy_it", "freegolup", "allgigs", "FreeWorkFeed", "FrWork3", "frilancekomfort",
            "workk_on", "freelancce", "javascript_jobs_feed", "designbirzha", "cgfreelance",
        ],
        description="Публичные Telegram-каналы для чтения через t.me/s/",
    )
    notify_vk: bool = True
    min_score: int = Field(default=50, ge=0, le=100)
    auto_contact: bool = False
    schedule_minutes: int = Field(default=60, ge=15, le=24 * 60)
    search_limit: int = Field(default=30, ge=1, le=200)
    first_message_template: str = Field(default=DEFAULT_FIRST_MESSAGE, max_length=2000)
    system_prompt: str = Field(default=DEFAULT_SYSTEM_PROMPT, max_length=8000)
    retention_days: int = Field(default=180, ge=7, le=3650)


class BotSettingsOut(BaseModel):
    enabled: bool
    data: BotSettingsData
    updated_at: datetime | None


class BotStatus(BaseModel):
    enabled: bool
    running: bool
    worker_available: bool
    last_run: "BotRunOut | None"
    sources_configured: dict[str, bool]
    llm_configured: bool


class BotRunOut(ORMModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    found_count: int
    contacted_count: int
    errors: int
    log: list


class LeadOut(ORMModel):
    id: int
    source: LeadSource
    external_id: str
    author_name: str | None
    profile_url: str | None
    post_url: str | None
    request_text: str
    relevance_score: int
    service_guess: ServiceType | None
    status: LeadStatus
    can_contact: bool
    manual_mode: bool
    link_sent_at: datetime | None
    created_at: datetime


class LeadUpdate(BaseModel):
    status: LeadStatus | None = None
    manual_mode: bool | None = None


class BotMessageOut(ORMModel):
    id: int
    direction: MessageDirection
    text: str
    is_manual: bool
    created_at: datetime


class ManualMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class FunnelStats(BaseModel):
    found: int
    contacted: int
    replied: int
    link_sent: int
    converted: int
    opted_out: int
    by_source: dict[str, int]


BotStatus.model_rebuild()


class PlaceOut(ORMModel):
    id: int
    key: str
    title: str | None
    url: str | None
    kind: str
    found_count: int
    bot_added: bool
    watch: bool
    hidden: bool
    last_found_at: datetime | None
    created_at: datetime


class PlaceUpdate(BaseModel):
    watch: bool | None = None
    hidden: bool | None = None


class PlacesOut(BaseModel):
    items: list[PlaceOut]
    bot_username: str | None
