from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from app.core.config import settings
from app.core.deps import SessionDep
from app.core.ratelimit import client_ip, rate_limit
from app.schemas.order import OrderCreate, OrderCreated
from app.services.notify import OrderSnapshot, notify_new_order
from app.services.orders import create_order

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post(
    "/orders",
    response_model=OrderCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("orders", settings.order_rate_limit, 3600))],
)
async def submit_order(
    data: OrderCreate, request: Request, session: SessionDep, background: BackgroundTasks
) -> OrderCreated:
    # Honeypot заполнен — это бот. Отвечаем как обычно, но ничего не сохраняем.
    if data.website:
        return OrderCreated()
    order = await create_order(session, data, client_ip(request))
    # Уведомление во ВКонтакте уходит после ответа клиенту и не задерживает форму
    background.add_task(notify_new_order, OrderSnapshot.of(order))
    return OrderCreated()
