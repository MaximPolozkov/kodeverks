from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response

from app.core.deps import SessionDep, StaffUser
from app.models import Order, OrderSource, OrderStatus
from app.schemas.common import Page
from app.schemas.order import (
    CommentCreate,
    CommentOut,
    HistoryOut,
    OrderDetail,
    OrderListItem,
    OrderStatusUpdate,
)
from app.services import orders as svc
from app.services.contacts import contact_url

router = APIRouter(prefix="/api/admin/orders", tags=["admin: orders"])


def _detail(order: Order) -> OrderDetail:
    base = OrderListItem.model_validate(order).model_dump()
    return OrderDetail(
        **base,
        description=order.description,
        utm_medium=order.utm_medium,
        utm_campaign=order.utm_campaign,
        utm_content=order.utm_content,
        utm_term=order.utm_term,
        lead_id=order.lead_id,
        vk_notified_at=order.vk_notified_at,
        contact_link=contact_url(order.contact_channel, order.contact_value, order.email),
        updated_at=order.updated_at,
        comments=[
            CommentOut(
                id=c.id,
                text=c.text,
                author_id=c.author_id,
                author_name=c.author.name if c.author else None,
                created_at=c.created_at,
            )
            for c in order.comments
        ],
        history=[
            HistoryOut(
                id=h.id,
                old_status=h.old_status,
                new_status=h.new_status,
                changed_by=h.changed_by,
                author_name=h.author.name if h.author else None,
                changed_at=h.changed_at,
            )
            for h in order.history
        ],
    )


@router.get("", response_model=Page[OrderListItem])
async def list_orders(
    session: SessionDep,
    _: StaffUser,
    status_: OrderStatus | None = Query(default=None, alias="status"),
    source: OrderSource | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = Query(default=None, max_length=200),
    sort: Literal["created_at", "budget", "status"] = "created_at",
    direction: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[OrderListItem]:
    items, total = await svc.list_orders(
        session,
        status=status_,
        source=source,
        date_from=date_from,
        date_to=date_to,
        q=q,
        sort=sort,
        direction=direction,
        page=page,
        page_size=page_size,
    )
    return Page(
        items=[OrderListItem.model_validate(o) for o in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/new-count")
async def new_count(session: SessionDep, _: StaffUser) -> dict:
    return {"count": await svc.count_new(session)}


@router.get("/export.csv")
async def export_orders(
    session: SessionDep,
    _: StaffUser,
    status_: OrderStatus | None = Query(default=None, alias="status"),
    source: OrderSource | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = Query(default=None, max_length=200),
) -> Response:
    content = await svc.export_csv(
        session, status=status_, source=source, date_from=date_from, date_to=date_to, q=q
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="orders.csv"'},
    )


async def _get_or_404(session, order_id: int) -> Order:
    order = await svc.get_order(session, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Заказ не найден")
    return order


@router.get("/{order_id}", response_model=OrderDetail)
async def get_order(order_id: int, session: SessionDep, _: StaffUser) -> OrderDetail:
    return _detail(await _get_or_404(session, order_id))


@router.patch("/{order_id}", response_model=OrderDetail)
async def update_order(
    order_id: int, data: OrderStatusUpdate, session: SessionDep, user: StaffUser
) -> OrderDetail:
    order = await _get_or_404(session, order_id)
    await svc.change_status(session, order, data.status, user)
    session.expire_all()
    return _detail(await _get_or_404(session, order_id))


@router.post(
    "/{order_id}/comments", response_model=OrderDetail, status_code=status.HTTP_201_CREATED
)
async def add_comment(
    order_id: int, data: CommentCreate, session: SessionDep, user: StaffUser
) -> OrderDetail:
    order = await _get_or_404(session, order_id)
    await svc.add_comment(session, order, data.text, user)
    session.expire_all()
    return _detail(await _get_or_404(session, order_id))
