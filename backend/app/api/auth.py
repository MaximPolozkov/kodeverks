from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import ACCESS_COOKIE, REFRESH_COOKIE, CurrentUser, SessionDep
from app.core.ratelimit import rate_limit
from app.core.security import create_token, decode_token, verify_password
from app.models import User
from app.schemas.user import LoginIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def set_auth_cookies(response: Response, user: User) -> None:
    response.set_cookie(
        ACCESS_COOKIE,
        create_token(user.id, "access", user.token_version),
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        create_token(user.id, "refresh", user.token_version),
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/api/auth",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")


@router.post(
    "/login",
    response_model=UserOut,
    dependencies=[Depends(rate_limit("login", 10, 300))],
)
async def login(data: LoginIn, response: Response, session: SessionDep) -> User:
    user = await session.scalar(select(User).where(User.email == str(data.email).lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Учётная запись заблокирована")
    set_auth_cookies(response, user)
    return user


@router.post("/refresh", response_model=UserOut)
async def refresh(
    response: Response,
    session: SessionDep,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> User:
    expired = HTTPException(status.HTTP_401_UNAUTHORIZED, "Сессия истекла, войдите снова")
    payload = decode_token(refresh_token, "refresh") if refresh_token else None
    if payload is None:
        raise expired
    user = await session.get(User, int(payload["sub"]))
    if user is None or not user.is_active or user.token_version != payload.get("ver", 0):
        clear_auth_cookies(response)
        raise expired
    set_auth_cookies(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
