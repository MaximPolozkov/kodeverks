from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, str_enum
from app.models.enums import ContactChannel, OrderSource, OrderStatus, ServiceType


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), index=True)
    budget: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str] = mapped_column(Text)
    service_type: Mapped[ServiceType | None] = mapped_column(
        str_enum(ServiceType, 16)
    )
    # Где клиенту удобно получить ответ
    contact_channel: Mapped[ContactChannel] = mapped_column(
        str_enum(ContactChannel, 16), default=ContactChannel.email, server_default="email"
    )
    contact_value: Mapped[str | None] = mapped_column(String(200))
    # Когда менеджеры получили уведомление во ВКонтакте (None — не отправлено)
    vk_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[OrderSource] = mapped_column(
        str_enum(OrderSource, 16), default=OrderSource.site, index=True
    )
    utm_source: Mapped[str | None] = mapped_column(String(100))
    utm_medium: Mapped[str | None] = mapped_column(String(100))
    utm_campaign: Mapped[str | None] = mapped_column(String(100))
    utm_content: Mapped[str | None] = mapped_column(String(100))
    utm_term: Mapped[str | None] = mapped_column(String(100))
    lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        str_enum(OrderStatus, 16), default=OrderStatus.new, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    comments: Mapped[list["OrderComment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderComment.id"
    )
    history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.id",
    )


class OrderComment(Base):
    __tablename__ = "order_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="comments")
    author: Mapped[Optional["User"]] = relationship(lazy="joined")  # noqa: F821


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    old_status: Mapped[OrderStatus | None] = mapped_column(
        str_enum(OrderStatus, 16)
    )
    new_status: Mapped[OrderStatus] = mapped_column(str_enum(OrderStatus, 16))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="history")
    author: Mapped[Optional["User"]] = relationship(lazy="joined")  # noqa: F821
