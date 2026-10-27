import csv
import io
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Lead,
    LeadStatus,
    Order,
    OrderComment,
    OrderSource,
    OrderStatus,
    OrderStatusHistory,
    User,
)
from app.schemas.order import OrderCreate

SORT_FIELDS = {"created_at": Order.created_at, "budget": Order.budget, "status": Order.status}


async def create_order(session: AsyncSession, data: OrderCreate, ip: str | None) -> Order:
    lead: Lead | None = None
    if data.ref == "bot" and data.lead_id:
        lead = await session.scalar(select(Lead).where(Lead.public_token == data.lead_id))

    if lead is not None:
        source = OrderSource.bot
    elif data.utm_source:
        source = OrderSource.utm
    else:
        source = OrderSource.site

    order = Order(
        name=data.name,
        email=str(data.email).lower(),
        budget=data.budget,
        description=data.description,
        service_type=data.service_type,
        contact_channel=data.contact_channel,
        contact_value=data.contact_value,
        source=source,
        utm_source=data.utm_source,
        utm_medium=data.utm_medium,
        utm_campaign=data.utm_campaign,
        utm_content=data.utm_content,
        utm_term=data.utm_term,
        lead_id=lead.id if lead else None,
        status=OrderStatus.new,
        ip_address=ip,
    )
    session.add(order)
    await session.flush()
    session.add(OrderStatusHistory(order_id=order.id, old_status=None, new_status=OrderStatus.new))
    if lead is not None:
        lead.status = LeadStatus.converted
    await session.commit()
    return order


def _filtered_query(
    status: OrderStatus | None,
    source: OrderSource | None,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
) -> Select:
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == status)
    if source:
        stmt = stmt.where(Order.source == source)
    if date_from:
        stmt = stmt.where(Order.created_at >= datetime.combine(date_from, time.min, tzinfo=UTC))
    if date_to:
        stmt = stmt.where(Order.created_at < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC))
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Order.name.ilike(pattern),
                Order.email.ilike(pattern),
                Order.description.ilike(pattern),
            )
        )
    return stmt


async def list_orders(
    session: AsyncSession,
    *,
    status: OrderStatus | None = None,
    source: OrderSource | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    sort: str = "created_at",
    direction: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Order], int]:
    stmt = _filtered_query(status, source, date_from, date_to, q)
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORT_FIELDS.get(sort, Order.created_at)
    order_by = asc(column) if direction == "asc" else desc(column)
    rows = await session.scalars(
        stmt.order_by(order_by, desc(Order.id)).offset((page - 1) * page_size).limit(page_size)
    )
    return list(rows), total


async def export_csv(session: AsyncSession, **filters) -> str:
    stmt = _filtered_query(**filters).order_by(desc(Order.created_at))
    rows = await session.scalars(stmt)
    buffer = io.StringIO()
    buffer.write("﻿")  # BOM, чтобы Excel корректно открыл кириллицу
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        ["ID", "Дата", "Имя", "Email", "Связь", "Контакт", "Бюджет", "Услуга", "Источник", "UTM source", "Статус", "Описание"]
    )
    for o in rows:
        writer.writerow(
            [
                o.id,
                o.created_at.strftime("%d.%m.%Y %H:%M") if o.created_at else "",
                o.name,
                o.email,
                o.contact_channel,
                o.contact_value or "",
                f"{o.budget:.2f}",
                o.service_type or "",
                o.source,
                o.utm_source or "",
                o.status,
                o.description.replace("\n", " "),
            ]
        )
    return buffer.getvalue()


async def get_order(session: AsyncSession, order_id: int) -> Order | None:
    return await session.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.comments), selectinload(Order.history))
        .execution_options(populate_existing=True)
    )


async def change_status(
    session: AsyncSession, order: Order, new_status: OrderStatus, user: User
) -> None:
    if order.status == new_status:
        return
    session.add(
        OrderStatusHistory(
            order_id=order.id, old_status=order.status, new_status=new_status, changed_by=user.id
        )
    )
    order.status = new_status
    await session.commit()


async def add_comment(session: AsyncSession, order: Order, text: str, user: User) -> OrderComment:
    comment = OrderComment(order_id=order.id, author_id=user.id, text=text.strip())
    session.add(comment)
    await session.commit()
    return comment


async def count_new(session: AsyncSession) -> int:
    return await session.scalar(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.new)
    ) or 0
