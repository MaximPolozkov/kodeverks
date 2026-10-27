"""Настройка сообщества ВКонтакте через API.

Что делает:
  1. Проверяет ключ сообщества (VK_GROUP_TOKEN) и что он от нужного сообщества.
  2. Включает сообщения сообщества, возможности ботов и кнопку «Начать».
  3. Подключает Callback API к SITE_URL/api/webhooks/vk и включает события
     «Входящее сообщение» и «Разрешение на получение сообщений».
  4. Печатает строку подтверждения и секрет — их нужно вписать в .env.
  5. Показывает, кто из VK_NOTIFY_PEER_IDS уже разрешил сообщения от сообщества.

Запуск: python -m app.scripts.vk_setup            (docker compose exec backend python -m app.scripts.vk_setup)
        python -m app.scripts.vk_setup --check    только проверка, без изменений
"""

import asyncio
import secrets
import sys

import httpx

from app.core.config import settings
from app.services.notify import resolve_peers

API = "https://api.vk.com/method/"
V = "5.199"


class VKError(Exception):
    pass


async def call(client: httpx.AsyncClient, method: str, **params):
    params.update(access_token=settings.vk_group_token, v=V)
    body = (await client.post(API + method, data=params)).json()
    if "error" in body:
        e = body["error"]
        raise VKError(f"{method}: {e.get('error_code')} {e.get('error_msg')}")
    return body["response"]


def ok(text: str) -> None:
    print(f"  ✓ {text}")


def warn(text: str) -> None:
    print(f"  ! {text}")


async def main(check_only: bool) -> int:
    if not settings.vk_group_token or not settings.vk_group_id:
        print("Заполните в .env VK_GROUP_TOKEN и VK_GROUP_ID (ID сообщества: 242635535).")
        return 1
    gid = settings.vk_group_id
    webhook = f"{settings.site_url.rstrip('/')}/api/webhooks/vk"

    async with httpx.AsyncClient(timeout=20) as client:
        print("1. Ключ доступа")
        try:
            groups = await call(client, "groups.getById", group_id=gid)
        except VKError as e:
            print(f"  ✗ Ключ не работает: {e}")
            return 1
        group = (groups.get("groups") if isinstance(groups, dict) else groups)[0]
        ok(f"Сообщество «{group['name']}» (club{group['id']})")

        if check_only:
            print("\n(режим проверки — настройки не меняются)")
        else:
            print("\n2. Сообщения и бот")
            try:
                await call(client, "groups.setSettings", group_id=gid, messages=1,
                           bots_capabilities=1, bots_start_button=1, bots_add_to_chat=1)
                ok("Сообщения включены, возможности бота и кнопка «Начать» включены")
            except VKError as e:
                warn(f"Не удалось изменить настройки ({e}). Включите вручную: Управление → Сообщения "
                     "и Сообщения → Настройки для бота. Для автоматической настройки у ключа нужно право «Управление сообществом».")

            print("\n3. Callback API")
            if settings.site_url.startswith("http://localhost"):
                warn(f"SITE_URL = {settings.site_url}. ВКонтакте не достучится до localhost — "
                     "пропишите публичный адрес с HTTPS и запустите скрипт снова. Уведомления о заказах работают и без этого шага.")
            else:
                try:
                    secret = settings.vk_callback_secret or secrets.token_urlsafe(24)
                    servers = (await call(client, "groups.getCallbackServers", group_id=gid))["items"]
                    server = next((s for s in servers if s["url"] == webhook), None)
                    code = await call(client, "groups.getCallbackConfirmationCode", group_id=gid)
                    print(f"\n  Впишите в .env и перезапустите backend, затем снова запустите скрипт:\n"
                          f"    VK_CONFIRMATION_CODE={code['code']}\n    VK_CALLBACK_SECRET={secret}\n")
                    if server is None:
                        if settings.vk_confirmation_code != code["code"]:
                            warn("Сервер ещё не добавлен: сначала сохраните значения выше в .env.")
                        else:
                            res = await call(client, "groups.addCallbackServer", group_id=gid, url=webhook,
                                             title="Сайт студии", secret_key=secret)
                            server = {"id": res["server_id"]}
                            ok(f"Добавлен сервер {webhook}")
                    if server is not None:
                        await call(client, "groups.setCallbackSettings", group_id=gid, server_id=server["id"],
                                   api_version=V, message_new=1, message_allow=1, message_deny=1)
                        ok("События: входящее сообщение, разрешение и запрет сообщений")
                except VKError as e:
                    warn(f"Callback API не настроен: {e}")

        print("\n4. Получатели уведомлений о заказах")
        ids = await resolve_peers(client)
        if ids:
            ok("ID получателей: " + ", ".join(ids))
        if not ids:
            warn("VK_NOTIFY_PEER_IDS пуст. Узнайте свой ID (vk.com/id… или через regvk.com) и впишите через запятую.")
        for pid in ids:
            if int(pid) >= 2_000_000_000:
                ok(f"{pid}: беседа — бот должен быть в неё добавлен")
                continue
            try:
                allowed = await call(client, "messages.isMessagesFromGroupAllowed", group_id=gid, user_id=pid)
                if allowed.get("is_allowed"):
                    ok(f"id{pid}: сообщения разрешены")
                else:
                    warn(f"id{pid}: напишите сообществу vk.ru/im?sel=-{gid} любое сообщение, иначе уведомления не дойдут")
            except VKError as e:
                warn(f"id{pid}: {e}")

        if ids and not check_only and "--test" in sys.argv:
            await call(client, "messages.send", peer_ids=",".join(ids), random_id=secrets.randbelow(2**31),
                       message="✅ Тест: уведомления о заказах с сайта настроены.")
            ok("Отправлено тестовое сообщение")
    print("\nГотово.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--check" in sys.argv)))
