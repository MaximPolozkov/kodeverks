from app.models import UserRole
from tests.conftest import make_user


async def test_admin_requires_auth(client):
    for url in ["/api/admin/orders", "/api/admin/profile", "/api/admin/bot/leads"]:
        resp = await client.get(url)
        assert resp.status_code == 401, url


async def test_wrong_password(client, session_factory):
    await make_user(session_factory, "m@example.com", UserRole.manager)
    resp = await client.post("/api/auth/login", json={"email": "m@example.com", "password": "nope"})
    assert resp.status_code == 401


async def test_manager_cannot_manage_users(client, session_factory):
    await make_user(session_factory, "m@example.com", UserRole.manager)
    await client.post("/api/auth/login", json={"email": "m@example.com", "password": "password123"})
    assert (await client.get("/api/admin/orders")).status_code == 200
    assert (await client.get("/api/admin/users")).status_code == 403


async def test_order_workflow(admin_client, order_payload):
    await admin_client.post("/api/orders", json=order_payload)

    listing = (await admin_client.get("/api/admin/orders", params={"status": "new"})).json()
    assert listing["total"] == 1
    order_id = listing["items"][0]["id"]

    resp = await admin_client.patch(f"/api/admin/orders/{order_id}", json={"status": "in_progress"})
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["status"] == "in_progress"
    assert [h["new_status"] for h in detail["history"]] == ["new", "in_progress"]

    resp = await admin_client.post(
        f"/api/admin/orders/{order_id}/comments", json={"text": "Созвонились, ждём ТЗ"}
    )
    assert resp.status_code == 201
    assert resp.json()["comments"][0]["text"] == "Созвонились, ждём ТЗ"

    count = (await admin_client.get("/api/admin/orders/new-count")).json()["count"]
    assert count == 0

    csv = await admin_client.get("/api/admin/orders/export.csv")
    assert csv.status_code == 200
    assert "ivan@example.com" in csv.text


async def test_search_and_filters(admin_client, order_payload):
    await admin_client.post("/api/orders", json=order_payload)
    order_payload.update(email="olga@example.com", description="Нужна CRM для отдела продаж и склада")
    await admin_client.post("/api/orders", json=order_payload)

    found = (await admin_client.get("/api/admin/orders", params={"q": "CRM"})).json()
    assert found["total"] == 1
    assert found["items"][0]["email"] == "olga@example.com"


async def test_profile_and_password(admin_client):
    resp = await admin_client.patch("/api/admin/profile", json={"name": "Анна", "phone": "+7 900 000-00-00"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Анна"

    bad = await admin_client.post(
        "/api/admin/profile/password", json={"old_password": "wrong", "new_password": "newpassword1"}
    )
    assert bad.status_code == 400
    ok = await admin_client.post(
        "/api/admin/profile/password",
        json={"old_password": "password123", "new_password": "newpassword1"},
    )
    assert ok.status_code == 200
    # Новые cookies выставлены — доступ сохраняется
    assert (await admin_client.get("/api/admin/profile")).status_code == 200


async def test_last_admin_protected(admin_client):
    me = (await admin_client.get("/api/auth/me")).json()
    resp = await admin_client.patch(f"/api/admin/users/{me['id']}", json={"is_active": False})
    assert resp.status_code == 400


async def test_bot_settings_roundtrip(admin_client):
    data = (await admin_client.get("/api/admin/bot/settings")).json()
    assert data["enabled"] is False
    settings = data["data"]
    settings["keywords"] = ["нужен сайт", "  ", "сделать бота"]
    resp = await admin_client.put("/api/admin/bot/settings", json=settings)
    assert resp.status_code == 200
    assert resp.json()["data"]["keywords"] == ["нужен сайт", "сделать бота"]

    status = (await admin_client.get("/api/admin/bot/status")).json()
    assert status["worker_available"] is False
    stats = (await admin_client.get("/api/admin/bot/stats")).json()
    assert stats["found"] == 0
