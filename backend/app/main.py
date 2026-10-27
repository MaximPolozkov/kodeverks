import logging
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin_bot, admin_orders, admin_profile, auth, public, webhooks
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

FIELD_NAMES = {
    "name": "Имя",
    "email": "Email",
    "budget": "Бюджет",
    "description": "Описание",
    "consent": "Согласие на обработку данных",
    "contact_value": "Контакт для связи",
    "password": "Пароль",
    "new_password": "Новый пароль",
}

ERROR_MESSAGES = {
    "string_too_short": "слишком короткое значение",
    "string_too_long": "слишком длинное значение",
    "value_error": "некорректное значение",
    "missing": "обязательное поле",
    "greater_than": "должно быть больше нуля",
    "literal_error": "требуется отметить",
    "decimal_parsing": "должно быть числом",
    "decimal_max_digits": "слишком большое число",
    "decimal_max_places": "не больше двух знаков после запятой",
}


def create_app() -> FastAPI:
    app = FastAPI(title=f"{settings.app_name} API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for err in exc.errors():
            field = str(err["loc"][-1]) if err.get("loc") else ""
            if err["type"] == "value_error" and "email" in err.get("msg", "").lower():
                message = "некорректный адрес почты"
            elif err["type"] == "contact_error":
                errors.append({"field": field, "message": err["msg"]})
                continue
            else:
                message = ERROR_MESSAGES.get(err["type"], err.get("msg", "ошибка"))
            errors.append({"field": field, "message": f"{FIELD_NAMES.get(field, field)}: {message}"})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Проверьте правильность заполнения полей", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("Необработанная ошибка: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Внутренняя ошибка сервера. Попробуйте позже."},
        )

    for module in (public, auth, admin_orders, admin_profile, admin_bot, webhooks):
        app.include_router(module.router)

    media = Path(settings.media_dir)
    media.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media), name="media")
    return app


app = create_app()
