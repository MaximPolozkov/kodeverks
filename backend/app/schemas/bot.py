from datetime import datetime

from pydantic import BaseModel, Field, model_validator

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


DEFAULT_KEYWORDS = [
    "нужен сайт", "сделать сайт", "создать сайт", "разработать сайт", "разработка сайта",
    "доработать сайт", "доработка сайта", "переделать сайт", "редизайн сайта", "лендинг",
    "landing page", "интернет-магазин", "интернет магазин", "сайт на тильде", "сайт на wordpress",
    "сайт на битрикс", "ищу разработчика", "ищу программиста", "ищу веб-разработчика",
    "нужен программист", "нужен разработчик", "нужен телеграм бот", "нужен бот", "сделать бота",
    "разработать бота", "чат-бот", "чат бот", "бот для telegram", "бот в телеграм", "бот для вк",
    "мини-приложение telegram", "mini app", "парсер", "интеграция с api", "автоматизация",
    "внедрить crm", "нужна crm", "настроить crm", "amocrm", "битрикс24", "crm-система",
    "разработка приложения", "мобильное приложение", "приложение для android", "приложение для ios",
    "веб-приложение", "личный кабинет", "админ-панель", "техническое задание",
]


class SourceLimits(BaseModel):
    enabled: bool = True
    per_hour: int = Field(default=5, ge=0, le=100)
    per_day: int = Field(default=30, ge=0, le=1000)


class BotSettingsData(BaseModel):
    keywords: list[str] = Field(default_factory=lambda: list(DEFAULT_KEYWORDS))
    stop_words: list[str] = Field(
        default_factory=lambda: ["вакансия", "резюме", "ищу работу", "бесплатно", "даром"]
    )
    sources: dict[LeadSource, SourceLimits] = Field(
        default_factory=lambda: {
            LeadSource.vk: SourceLimits(),
            LeadSource.telegram: SourceLimits(per_hour=0, per_day=0),  # писать первым в TG нельзя
            LeadSource.web: SourceLimits(per_hour=0, per_day=0),
            LeadSource.freelance: SourceLimits(per_hour=0, per_day=0),
        }
    )
    # Биржи: русские и зарубежные (иностранные заказы переводятся на русский)
    freelance_feeds: list[str] = Field(
        default_factory=lambda: ["fl", "kwork", "freelancer", "reddit"],
        description="fl, kwork, freelancer, reddit",
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

    @model_validator(mode="after")
    def _fill_sources(self) -> "BotSettingsData":
        # Новые источники появляются и у тех, кто сохранил настройки раньше
        for src in LeadSource:
            if src not in self.sources:
                self.sources[src] = SourceLimits(per_hour=0, per_day=0)
        return self


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
