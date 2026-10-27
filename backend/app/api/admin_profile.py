import secrets
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select

from app.api.auth import set_auth_cookies
from app.core.config import settings
from app.core.deps import AdminUser, SessionDep, StaffUser
from app.core.security import hash_password, verify_password
from app.models import User, UserRole
from app.schemas.user import PasswordChange, ProfileUpdate, UserAdminUpdate, UserCreate, UserOut

router = APIRouter(prefix="/api/admin", tags=["admin: profile & users"])

AVATAR_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
AVATAR_MAX_BYTES = 2 * 1024 * 1024


async def _email_taken(session, email: str, exclude_id: int | None = None) -> bool:
    stmt = select(User.id).where(User.email == email)
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return await session.scalar(stmt) is not None


@router.get("/profile", response_model=UserOut)
async def get_profile(user: StaffUser) -> User:
    return user


@router.patch("/profile", response_model=UserOut)
async def update_profile(data: ProfileUpdate, session: SessionDep, user: StaffUser) -> User:
    if data.email is not None:
        email = str(data.email).lower()
        if await _email_taken(session, email, exclude_id=user.id):
            raise HTTPException(status.HTTP_409_CONFLICT, "Этот email уже используется")
        user.email = email
    if data.name is not None:
        user.name = data.name.strip()
    if data.phone is not None:
        user.phone = data.phone.strip() or None
    await session.commit()
    return user


@router.post("/profile/password", response_model=UserOut)
async def change_password(
    data: PasswordChange, response: Response, session: SessionDep, user: StaffUser
) -> User:
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Текущий пароль указан неверно")
    user.password_hash = hash_password(data.new_password)
    user.token_version += 1  # выходим со всех других устройств
    await session.commit()
    set_auth_cookies(response, user)
    return user


@router.post("/profile/avatar", response_model=UserOut)
async def upload_avatar(
    session: SessionDep, user: StaffUser, file: UploadFile = File(...)
) -> User:
    ext = AVATAR_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Загрузите изображение JPG, PNG или WebP")
    content = await file.read(AVATAR_MAX_BYTES + 1)
    if len(content) > AVATAR_MAX_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Файл больше 2 МБ")
    folder = Path(settings.media_dir) / "avatars"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{user.id}-{secrets.token_hex(8)}{ext}"
    (folder / name).write_bytes(content)
    user.avatar_url = f"/media/avatars/{name}"
    await session.commit()
    return user


# --- Управление пользователями (только admin) ---


@router.get("/users", response_model=list[UserOut])
async def list_users(session: SessionDep, _: AdminUser) -> list[User]:
    return list(await session.scalars(select(User).order_by(User.created_at)))


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, session: SessionDep, _: AdminUser) -> User:
    email = str(data.email).lower()
    if await _email_taken(session, email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Этот email уже используется")
    user = User(
        email=email,
        name=data.name.strip(),
        password_hash=hash_password(data.password),
        role=data.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int, data: UserAdminUpdate, session: SessionDep, admin: AdminUser
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    demoting_self = user.id == admin.id and (
        data.is_active is False or (data.role is not None and data.role != UserRole.admin)
    )
    if demoting_self:
        active_admins = await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.admin, User.is_active.is_(True))
        )
        if (active_admins or 0) <= 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Нельзя заблокировать или понизить последнего администратора"
            )
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
        if not data.is_active:
            user.token_version += 1
    await session.commit()
    return user
