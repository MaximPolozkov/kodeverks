import pytest
from sqlalchemy import select

from app.api import public
from app.models import ContactChannel, Order
from app.services import notify
from app.services.contacts import contact_url, normalize_contact


@pytest.mark.parametrize(
    ("channel", "raw", "expected", "url"),
    [
        (ContactChannel.telegram, "https://t.me/ivan_petrov", "@ivan_petrov", "https://t.me/ivan_petrov"),
        (ContactChannel.telegram, "@ivan_petrov", "@ivan_petrov", "https://t.me/ivan_petrov"),
        (ContactChannel.vk, "https://vk.ru/id12345", "id12345", "https://vk.com/id12345"),
        (ContactChannel.whatsapp, "8 (912) 345-67-89", "+79123456789", "https://wa.me/79123456789"),
        (ContactChannel.phone, "+7 912 345 67 89", "+79123456789", "tel:+79123456789"),
    ],
)
def test_normalize_and_link(channel, raw, expected, url):
    value = normalize_contact(channel, raw)
    assert value == expected
    assert contact_url(channel, value, "a@b.ru") == url


def test_bad_contact_rejected():
    with pytest.raises(ValueError):
        normalize_contact(ContactChannel.whatsapp, "abc")
    with pytest.raises(ValueError):
        normalize_contact(ContactChannel.telegram, "")


def test_message_has_buttons():
    snap = notify.OrderSnapshot(
        id=7, name="Иван", email="ivan@example.com", budget="150 000 ₽",
        description="Нужен бот для записи", service_type="bot", source="site", utm_source=None,
        contact_channel=ContactChannel.telegram, contact_value="@ivan_petrov",
    )
    text, keyboard = notify.build_message(snap)
    assert "Новый заказ №7" in text and "Telegram — @ivan_petrov" in text
    links = [row[0]["action"]["link"] for row in keyboard["buttons"]]
    assert links[0].endswith("/admin/orders/7")
    assert links[1] == "https://t.me/ivan_petrov"


async def test_order_triggers_notification(client, session_factory, order_payload, monkeypatch):
    sent = []

    async def fake_notify(snapshot):
        sent.append(snapshot)

    monkeypatch.setattr(public, "notify_new_order", fake_notify)
    order_payload.update(contact_channel="vk", contact_value="vk.com/ivan_petrov")
    resp = await client.post("/api/orders", json=order_payload)
    assert resp.status_code == 201, resp.text
    assert sent and sent[0].contact_value == "ivan_petrov"
    async with session_factory() as s:
        order = await s.scalar(select(Order))
    assert order.contact_channel == "vk"


async def test_contact_error_returned_for_field(client, order_payload):
    order_payload.update(contact_channel="whatsapp", contact_value="не номер")
    resp = await client.post("/api/orders", json=order_payload)
    assert resp.status_code == 422
    err = next(e for e in resp.json()["errors"] if e["field"] == "contact_value")
    assert "номер телефона" in err["message"]
