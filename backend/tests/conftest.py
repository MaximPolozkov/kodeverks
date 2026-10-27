import os

# Настройки тестового окружения — до импорта приложения
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["MEDIA_DIR"] = "/tmp/itstudio-test-media"
os.environ["LLM_PROVIDER"] = "none"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.core.db import Base, get_session  # noqa: E402
from app.core.ratelimit import limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User, UserRole  # noqa: E402


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def client(session_factory):
    async def override():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    limiter.reset()
    limiter._redis_failed = True  # в тестах счётчик в памяти
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver.local") as c:
        yield c
    app.dependency_overrides.clear()


async def make_user(session_factory, email: str, role: UserRole, password: str = "password123"):
    async with session_factory() as s:
        user = User(email=email, name="Тест", password_hash=hash_password(password), role=role)
        s.add(user)
        await s.commit()
        return user


@pytest_asyncio.fixture
async def admin_client(client, session_factory):
    await make_user(session_factory, "admin@example.com", UserRole.admin)
    resp = await client.post(
        "/api/auth/login", json={"email": "admin@example.com", "password": "password123"}
    )
    assert resp.status_code == 200, resp.text
    return client


@pytest.fixture
def order_payload():
    return {
        "name": "Иван",
        "email": "ivan@example.com",
        "budget": 150000,
        "description": "Нужен интернет-магазин с каталогом и оплатой онлайн",
        "service_type": "website",
        "consent": True,
    }
