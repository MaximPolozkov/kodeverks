from sqlalchemy import select

from app.models import Lead, LeadSource, LeadStatus, Order, OrderSource


async def test_create_order(client, session_factory, order_payload):
    resp = await client.post("/api/orders", json=order_payload)
    assert resp.status_code == 201, resp.text
    async with session_factory() as s:
        order = await s.scalar(select(Order))
    assert order.email == "ivan@example.com"
    assert order.source == OrderSource.site
    assert order.status == "new"


async def test_validation_errors_in_russian(client, order_payload):
    order_payload.update(email="not-an-email", description="коротко", budget=0)
    resp = await client.post("/api/orders", json=order_payload)
    assert resp.status_code == 422
    fields = {e["field"] for e in resp.json()["errors"]}
    assert {"email", "description", "budget"} <= fields


async def test_consent_required(client, order_payload):
    order_payload["consent"] = False
    resp = await client.post("/api/orders", json=order_payload)
    assert resp.status_code == 422


async def test_honeypot_is_not_saved(client, session_factory, order_payload):
    order_payload["website"] = "http://spam.example"
    resp = await client.post("/api/orders", json=order_payload)
    assert resp.status_code == 201
    async with session_factory() as s:
        assert await s.scalar(select(Order)) is None


async def test_rate_limit(client, order_payload):
    codes = [(await client.post("/api/orders", json=order_payload)).status_code for _ in range(6)]
    assert codes[:5] == [201] * 5
    assert codes[5] == 429


async def test_order_from_bot_links_lead(client, session_factory, order_payload):
    async with session_factory() as s:
        lead = Lead(
            source=LeadSource.vk,
            external_id="1_1",
            request_text="нужен сайт",
            relevance_score=80,
            status=LeadStatus.qualified,
            can_contact=True,
            manual_mode=False,
            public_token="tok123",
        )
        s.add(lead)
        await s.commit()
        lead_id = lead.id

    order_payload.update(ref="bot", lead_id="tok123")
    resp = await client.post("/api/orders", json=order_payload)
    assert resp.status_code == 201

    async with session_factory() as s:
        order = await s.scalar(select(Order))
        lead = await s.get(Lead, lead_id)
    assert order.source == OrderSource.bot
    assert order.lead_id == lead_id
    assert lead.status == LeadStatus.converted


async def test_utm_source(client, session_factory, order_payload):
    order_payload["utm_source"] = "yandex"
    await client.post("/api/orders", json=order_payload)
    async with session_factory() as s:
        order = await s.scalar(select(Order))
    assert order.source == OrderSource.utm
