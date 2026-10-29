"""Биржи фриланса: FL.ru, Kwork (Россия), Freelancer.com и Reddit (зарубежные).

Читаем только открытые ленты заказов, без входа в аккаунт. Иностранные заказы
предварительно отбираются по английским словам, переводятся на русский и
помечаются «🌍 Иностранный заказ».
"""

import html
import json
import re
import time
from email.utils import parsedate_to_datetime

import httpx

from app.bot.sources.base import FoundPost, Source, SourceError
from app.bot.translate import to_russian
from app.models.enums import LeadSource

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
MAX_AGE = 3 * 24 * 3600

# Отбор иностранных заказов до перевода (экономит лимит переводчика)
EN_RELEVANT = re.compile(
    r"\b(website|web ?site|landing|web app|web application|wordpress|shopify|woocommerce|e-?commerce|"
    r"online store|telegram|chat ?bot|bot|crm|hubspot|bitrix|mobile app|ios|android|flutter|"
    r"react|next\.?js|django|fastapi|laravel|php|python|api integration|dashboard|saas|mvp)\b",
    re.I,
)
FREELANCER_QUERIES = ["website", "telegram bot", "crm", "mobile app", "web app"]
REDDIT_SUBS = ["forhire", "slavelabour", "hiring"]
KWORK_CATEGORIES = ["11"]  # «Разработка и IT»
FL_URL = "https://www.fl.ru/rss/all.xml?category=2"  # «Программирование»; сайты — в той же ленте

SITE_URLS = {
    "fl": "https://www.fl.ru/projects/",
    "kwork": "https://kwork.ru/projects?c=11",
    "freelancer": "https://www.freelancer.com/jobs/",
    "reddit": "https://www.reddit.com/r/forhire/",
}

# Уже обработанные иностранные заказы (в памяти воркера) — чтобы не тратить
# лимит переводчика повторно каждые 15 минут
_SEEN_FOREIGN: set[str] = set()

ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S)
ENTRY_RE = re.compile(r"<entry>(.*?)</entry>", re.S)


def _tag(block: str, name: str) -> str:
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, re.S)
    if not m:
        return ""
    value = re.sub(r"^<!\[CDATA\[|\]\]>$", "", m.group(1).strip(), flags=re.S)
    value = html.unescape(value)
    value = re.sub(r"<br\s*/?>", "\n", value)
    return html.unescape(re.sub(r"<[^>]+>", " ", value)).strip()


def _fresh(ts: float | None) -> bool:
    return ts is None or time.time() - ts < MAX_AGE


class FreelanceSource(Source):
    name = LeadSource.freelance

    def __init__(self, feeds: list[str] | None = None) -> None:
        self.feeds = feeds if feeds is not None else ["fl", "kwork", "freelancer", "reddit"]
        self.failed: list[str] = []
        self.translated = 0
        self.untranslated = 0
        # Колбэк из раннера: есть ли уже такой лид в базе
        self.is_known = None

    @property
    def configured(self) -> bool:
        return bool(self.feeds)

    async def search(self, keywords: list[str], limit: int) -> list[FoundPost]:
        posts: list[FoundPost] = []
        self.failed = []
        async with httpx.AsyncClient(
            timeout=self.timeout, headers={"User-Agent": UA, "Accept-Language": "ru,en"}, follow_redirects=True
        ) as client:
            for feed in self.feeds:
                handler = getattr(self, f"_{feed}", None)
                if handler is None:
                    continue
                try:
                    posts += (await handler(client))[:limit]
                except Exception as exc:  # noqa: BLE001 — одна биржа не должна ронять остальные
                    self.failed.append(f"{feed} ({type(exc).__name__})")
        if self.failed and len(self.failed) == len(self.feeds):
            raise SourceError("ни одна биржа не ответила: " + ", ".join(self.failed))
        return posts

    # --- Россия ---

    async def _fl(self, client: httpx.AsyncClient) -> list[FoundPost]:
        resp = await client.get(FL_URL)
        resp.raise_for_status()
        text = resp.content.decode("cp1251", errors="replace")
        out = []
        for block in ITEM_RE.findall(text):
            link = _tag(block, "link")
            pub = _tag(block, "pubDate")
            ts = parsedate_to_datetime(pub).timestamp() if pub else None
            if not link or not _fresh(ts):
                continue
            title, desc = _tag(block, "title"), _tag(block, "description")
            out.append(self._post("fl", link, f"{title}\n\n{desc}", "FL.ru", link))
        return out

    async def _kwork(self, client: httpx.AsyncClient) -> list[FoundPost]:
        out = []
        for cat in KWORK_CATEGORIES:
            resp = await client.get(f"https://kwork.ru/projects?c={cat}")
            resp.raise_for_status()
            start = resp.text.find('"wants":[')
            if start < 0:
                raise SourceError("kwork: не найден список проектов")
            wants, _ = json.JSONDecoder().raw_decode(resp.text, start + len('"wants":'))
            for w in wants:
                wid = w.get("id")
                if not wid:
                    continue
                price = w.get("priceLimit")
                budget = f"\nБюджет: до {int(float(price))} ₽" if price else ""
                url = f"https://kwork.ru/projects/{wid}"
                text = f"{w.get('name', '')}\n\n{w.get('description', '')}{budget}"
                out.append(self._post("kwork", str(wid), text, "Kwork", url))
        return out

    # --- Зарубежные ---

    async def _freelancer(self, client: httpx.AsyncClient) -> list[FoundPost]:
        seen: dict[int, dict] = {}
        for q in FREELANCER_QUERIES:
            resp = await client.get(
                "https://www.freelancer.com/api/projects/0.1/projects/active/",
                params={"query": q, "limit": 20, "full_description": "true", "job_details": "false"},
            )
            resp.raise_for_status()
            for p in resp.json().get("result", {}).get("projects", []):
                seen.setdefault(p["id"], p)
        out = []
        for p in seen.values():
            if not _fresh(p.get("time_submitted")):
                continue
            budget = p.get("budget") or {}
            cur = (p.get("currency") or {}).get("code", "")
            money = f"{budget.get('minimum', '')}–{budget.get('maximum', '')} {cur}".strip("– ")
            text = f"{p.get('title', '')}. {p.get('description', '')}"
            url = f"https://www.freelancer.com/projects/{p.get('seo_url', p['id'])}"
            post = await self._foreign(client, "freelancer", str(p["id"]), text, "Freelancer.com", url, money)
            if post:
                out.append(post)
        return out

    async def _reddit(self, client: httpx.AsyncClient) -> list[FoundPost]:
        out = []
        for sub in REDDIT_SUBS:
            resp = await client.get(f"https://www.reddit.com/r/{sub}/new/.rss")
            resp.raise_for_status()
            for block in ENTRY_RE.findall(resp.text):
                title = _tag(block, "title")
                # В r/forhire публикуют и исполнители — берём только запросы заказчиков
                if sub == "forhire" and "[hiring]" not in title.lower():
                    continue
                if sub == "slavelabour" and "[task]" not in title.lower():
                    continue
                link_m = re.search(r'<link href="([^"]+)"', block)
                eid = _tag(block, "id")
                body = _tag(block, "content")
                if not link_m or not eid:
                    continue
                post = await self._foreign(
                    client, "reddit", eid, f"{title}. {body}", f"Reddit r/{sub}", link_m.group(1), ""
                )
                if post:
                    out.append(post)
        return out

    # --- Общее ---

    def _post(self, feed: str, eid: str, text: str, place: str, url: str, extra: dict | None = None) -> FoundPost:
        return FoundPost(
            source=self.name,
            external_id=f"{feed}:{eid}"[:128],
            text=re.sub(r"\n{3,}", "\n\n", text).strip()[:4000],
            author_name=place,
            post_url=url,
            can_contact=False,
            extra={"place": f"site:{feed}", "place_title": place, "place_kind": "site",
                   "place_url": SITE_URLS.get(feed),
                   "is_order": True, **(extra or {})},
        )

    async def _foreign(self, client, feed, eid, text, place, url, money) -> FoundPost | None:
        text = re.sub(r"\s+", " ", text).strip()
        key = f"{feed}:{eid}"[:128]
        if key in _SEEN_FOREIGN or not EN_RELEVANT.search(text):
            return None
        if self.is_known and await self.is_known(key):
            _SEEN_FOREIGN.add(key)
            return None
        _SEEN_FOREIGN.add(key)
        short = text[:900]
        ru = await to_russian(client, short)
        if ru:
            self.translated += 1
            body = ru
        else:
            self.untranslated += 1
            body = "(перевод недоступен — лимит переводчика) " + short
        head = f"🌍 Иностранный заказ · {place}" + (f" · бюджет {money}" if money else "")
        full = f"{head}\n\n{body}\n\nОригинал: {short[:400]}"
        return self._post(feed, eid, full, f"{place} (иностранный)", url, {"foreign": True})
