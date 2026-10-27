from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError

from app.models.enums import ContactChannel, OrderSource, OrderStatus, ServiceType
from app.schemas.common import ORMModel
from app.services.contacts import normalize_contact


class OrderCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    budget: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str = Field(min_length=20, max_length=5000)
    service_type: ServiceType | None = None
    contact_channel: ContactChannel = ContactChannel.email
    contact_value: str | None = Field(default=None, max_length=200, validate_default=True)
    consent: Literal[True]
    # Honeypot: скрытое поле, люди его не заполняют
    website: str | None = Field(default=None, max_length=200)
    # Атрибуция
    ref: str | None = Field(default=None, max_length=32)
    lead_id: str | None = Field(default=None, max_length=64)
    utm_source: str | None = Field(default=None, max_length=100)
    utm_medium: str | None = Field(default=None, max_length=100)
    utm_campaign: str | None = Field(default=None, max_length=100)
    utm_content: str | None = Field(default=None, max_length=100)
    utm_term: str | None = Field(default=None, max_length=100)

    @field_validator("name", "description")
    @classmethod
    def strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Поле не может быть пустым")
        return value

    @field_validator("contact_value")
    @classmethod
    def check_contact(cls, value: str | None, info: ValidationInfo) -> str | None:
        channel = info.data.get("contact_channel")
        if channel is None:
            return value
        try:
            return normalize_contact(channel, value)
        except ValueError as exc:
            raise PydanticCustomError("contact_error", str(exc)) from exc


class OrderCreated(BaseModel):
    ok: bool = True
    detail: str = "Заявка отправлена. Мы свяжемся с вами в течение рабочего дня."


class OrderListItem(ORMModel):
    id: int
    name: str
    email: str
    budget: Decimal
    service_type: ServiceType | None
    source: OrderSource
    utm_source: str | None
    contact_channel: ContactChannel
    contact_value: str | None
    status: OrderStatus
    created_at: datetime


class CommentOut(ORMModel):
    id: int
    text: str
    author_id: int | None
    author_name: str | None = None
    created_at: datetime


class HistoryOut(ORMModel):
    id: int
    old_status: OrderStatus | None
    new_status: OrderStatus
    changed_by: int | None
    author_name: str | None = None
    changed_at: datetime


class OrderDetail(OrderListItem):
    description: str
    utm_medium: str | None
    utm_campaign: str | None
    utm_content: str | None
    utm_term: str | None
    lead_id: int | None
    vk_notified_at: datetime | None = None
    contact_link: str | None = None
    updated_at: datetime
    comments: list[CommentOut]
    history: list[HistoryOut]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
