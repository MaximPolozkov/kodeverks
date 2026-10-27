"""Создаёт первого администратора из переменных окружения.

FIRST_ADMIN_EMAIL, FIRST_ADMIN_PASSWORD, FIRST_ADMIN_NAME
Запуск: python -m app.scripts.create_admin
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import User, UserRole


async def main() -> int:
    email = (settings.first_admin_email or "").strip().lower()
    password = settings.first_admin_password or ""
    if not email or not password:
        print("FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD не заданы — пропускаю")
        return 0
    if len(password) < 8:
        print("FIRST_ADMIN_PASSWORD должен быть не короче 8 символов", file=sys.stderr)
        return 1
    async with SessionLocal() as session:
        exists = await session.scalar(select(User.id).where(User.email == email))
        if exists:
            print(f"Пользователь {email} уже существует")
            return 0
        session.add(
            User(
                email=email,
                name=settings.first_admin_name,
                password_hash=hash_password(password),
                role=UserRole.admin,
            )
        )
        await session.commit()
    print(f"Создан администратор {email}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
