"""Чтение публичных Telegram-каналов через веб-версию t.me/s/<канал>.

Не требует вступления и ключей: это та же страница, что видит любой посетитель
в браузере. Закрытые группы так прочитать нельзя — туда нужно добавить бота.
"""
from app.core.config import settings


import html
import re
from dataclasses import dataclass, field

import httpx

USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")
POST_RE = re.compile(
    r'<div class="tgme_widget_message [^"]*"[^>]*data-post="([^"/]+)/(\d+)"(.*?)(?=<div class="tgme_widget_message_wrap|\Z)',
    re.S,
)
TEXT_RE = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
TITLE_RE = re.compile(r'<meta property="og:title" content="([^"]*)"')
AUTHOR_RE = re.compile(r'<span class="tgme_widget_message_from_author"[^>]*>(.*?)</span>', re.S)
LINK_RE = re.compile(r"(?:https?://)?t\.me/(?:s/)?([A-Za-z][A-Za-z0-9_]{3,31})(?![A-Za-z0-9_/])")
SKIP_NAMES = {"joinchat", "share", "addstickers", "proxy", "socks", "iv", "c", "s", "addlist", "boost"}


@dataclass
class ChannelPost:
    channel: str
    post_id: str
    text: str
    author: str | None = None


@dataclass
class ChannelPage:
    username: str
    title: str | None
    posts: list[ChannelPost] = field(default_factory=list)
    mentioned: set[str] = field(default_factory=set)


def normalize_username(value: str) -> str | None:
    value = value.strip()
    value = re.sub(r"^(https?://)?(t\.me|telegram\.me)/(s/)?", "", value).lstrip("@").strip("/")
    value = value.split("/")[0]
    return value if USERNAME_RE.match(value) and value.lower() not in SKIP_NAMES else None


def _clean(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return html.unescape(fragment).strip()


def parse_page(username: str, page: str) -> ChannelPage:
    title_match = TITLE_RE.search(page)
    result = ChannelPage(username=username, title=html.unescape(title_match.group(1)) if title_match else None)
    for channel, post_id, body in POST_RE.findall(page):
        text_match = TEXT_RE.search(body)
        if not text_match:
            continue
        author = AUTHOR_RE.search(body)
        result.posts.append(
            ChannelPost(channel, post_id, _clean(text_match.group(1)), _clean(author.group(1)) if author else None)
        )
        for name in LINK_RE.findall(text_match.group(1)):
            norm = normalize_username(name)
            if norm and norm.lower() != username.lower():
                result.mentioned.add(norm)
    return result


async def fetch_channel(client: httpx.AsyncClient, username: str) -> ChannelPage | None:
    resp = await client.get(f"{settings.telegram_web_base.rstrip('/')}/s/{username}", follow_redirects=False)
    if resp.status_code != 200:
        return None
    # Если канала нет или он закрыт, Telegram отдаёт страницу без ленты
    if "tgme_channel_history" not in resp.text:
        return ChannelPage(username=username, title=None)
    return parse_page(username, resp.text)
