"""Подключение Telegram-бота к сайту (вебхук).

Запуск на сервере из папки проекта:
  docker compose exec backend python -m app.scripts.tg_setup
Делает: проверяет ключ, регистрирует вебхук SITE_URL/api/webhooks/telegram
с секретом TELEGRAM_WEBHOOK_SECRET и показывает состояние.
"""

import asyncio
import sys

import httpx

from app.core.config import settings


async def main() -> int:
    token = settings.telegram_bot_token
    if not token:
        print("✗ TELEGRAM_BOT_TOKEN не задан в .env")
        return 1
    if not settings.telegram_webhook_secret:
        print("✗ TELEGRAM_WEBHOOK_SECRET не задан. Добавьте в .env строку, например:")
        print("  TELEGRAM_WEBHOOK_SECRET=" + __import__("secrets").token_urlsafe(24))
        print("  и выполните: sudo bash deploy/update.sh, затем запустите этот скрипт снова.")
        return 1
    if not settings.site_url.startswith("https://"):
        print(f"✗ SITE_URL={settings.site_url} — Telegram требует https-адрес")
        return 1

    api = f"https://api.telegram.org/bot{token}/"
    url = settings.site_url.rstrip("/") + "/api/webhooks/telegram"
    async with httpx.AsyncClient(timeout=20) as c:
        me = (await c.get(api + "getMe")).json()
        if not me.get("ok"):
            print(f"✗ Ключ не подходит: {me.get('description')}")
            return 1
        bot = me["result"]
        print(f"✓ Бот @{bot['username']} ({bot['first_name']})")
        if not bot.get("can_read_all_group_messages"):
            print("! Бот видит в группах только команды и ответы ему. Чтобы он находил запросы,")
            print("  в @BotFather: /setprivacy → выберите бота → Disable, затем заново добавьте его в группы.")

        r = (await c.post(api + "setWebhook", json={
            "url": url,
            "secret_token": settings.telegram_webhook_secret,
            "allowed_updates": ["message", "channel_post"],
            "drop_pending_updates": True,
        })).json()
        print(("✓ Вебхук: " + url) if r.get("ok") else f"✗ setWebhook: {r.get('description')}")

        await asyncio.sleep(2)
        info = (await c.get(api + "getWebhookInfo")).json().get("result", {})
        if info.get("last_error_message"):
            print(f"! Telegram сообщает об ошибке: {info['last_error_message']}")
        else:
            print("✓ Telegram может достучаться до сайта")
        print(f"\nНапишите боту в Telegram: https://t.me/{bot['username']} — он должен ответить.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
