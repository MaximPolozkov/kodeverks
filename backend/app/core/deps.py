from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import decode_token
from app.models import User, UserRole

SessionDep = Annotated[AsyncSession, Depends(get_session)]

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


async def get_current_user(
    session: SessionDep,
    access_token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE)] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    token = access_token
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется вход в систему"
    )
    if not token:
        raise unauthorized
    payload = decode_token(token, "access")
    if payload is None:
        raise unauthorized
    user = await session.get(User, int(payload["sub"]))
    if user is None or not user.is_active or user.token_version != payload.get("ver", 0):
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    async def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав"
            )
        return user

    return dependency


StaffUser = Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))]
AdminUser = Annotated[User, Depends(require_roles(UserRole.admin))]
