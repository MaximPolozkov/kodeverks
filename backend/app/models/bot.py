from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, JSONType, str_enum
from app.models.enums import LeadSource, LeadStatus, MessageDirection, ServiceType


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[LeadSource] = mapped_column(
        str_enum(LeadSource, 16), index=True
    )
    # ID поста / сообщения во внешней системе — по нему идёт дедупликация
    external_id: Mapped[str] = mapped_column(String(128))
    # ID автора во внешней системе — по нему работают диалоги и стоп-лист
    author_external_id: Mapped[str | None] = mapped_column(String(128), index=True)
    author_name: Mapped[str | None] = mapped_column(String(200))
    profile_url: Mapped[str | None] = mapped_column(String(500))
    post_url: Mapped[str | None] = mapped_column(String(500))
    request_text: Mapped[str] = mapped_column(Text, default="")
    relevance_score: Mapped[int] = mapped_column(Integer, default=0)
    service_guess: Mapped[ServiceType | None] = mapped_column(
        str_enum(ServiceType, 16)
    )
    status: Mapped[LeadStatus] = mapped_column(
        str_enum(LeadStatus, 16), default=LeadStatus.found, index=True
    )
    # Можно ли писать первыми по правилам площадки
    can_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    # Менеджер перехватил диалог — бот не отвечает автоматически
    manual_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    # Непрозрачный токен для ссылки на форму заказа (?ref=bot&lead_id=...)
    public_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    link_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["BotMessage"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="BotMessage.id"
    )


class BotMessage(Base):
    __tablename__ = "bot_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    direction: Mapped[MessageDirection] = mapped_column(
        str_enum(MessageDirection, 8)
    )
    text: Mapped[str] = mapped_column(Text)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    lead: Mapped[Lead] = relationship(back_populates="messages")


class BotStopList(Base):
    __tablename__ = "bot_stoplist"
    __table_args__ = (UniqueConstraint("source", "author_external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[LeadSource] = mapped_column(str_enum(LeadSource, 16))
    author_external_id: Mapped[str] = mapped_column(String(128))
    reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BotSettings(Base):
    """Единственная строка с id=1."""

    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    data: Mapped[dict] = mapped_column(JSONType, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BotRun(Base):
    __tablename__ = "bot_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    found_count: Mapped[int] = mapped_column(Integer, default=0)
    contacted_count: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    log: Mapped[list] = mapped_column(JSONType, default=list)
