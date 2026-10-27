"""Поиск публичных запросов на сайтах (биржи фриланса, форумы) через SerpAPI.

Связаться с автором автоматически нельзя — лиды помечаются can_contact=False,
менеджер откликается вручную по ссылке.
"""

import hashlib

import httpx

from app.bot.sources.base import FoundPost, Source, SourceError
from app.core.config import settings
from app.models.enums import LeadSource

SERP_URL = "https://serpapi.com/search.json"


class WebSource(Source):
    name = LeadSource.web

    def __init__(self, sites: list[str] | None = None) -> None:
        self.sites = sites or []

    @property
    def configured(self) -> bool:
        return bool(settings.serpapi_key)

    async def search(self, keywords: list[str], limit: int) -> list[FoundPost]:
        if not settings.serpapi_key:
            return []
        site_filter = " OR ".join(f"site:{s}" for s in self.sites)
        found: dict[str, FoundPost] = {}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for keyword in keywords:
                query = f'"{keyword}" {site_filter}'.strip()
                resp = await client.get(
                    SERP_URL,
                    params={
                        "engine": "google",
                        "q": query,
                        "hl": "ru",
                        "num": min(limit, 20),
                        "tbs": "qdr:w",  # за последнюю неделю
                        "api_key": settings.serpapi_key,
                    },
                )
                if resp.status_code != 200:
                    raise SourceError(f"SerpAPI: HTTP {resp.status_code}")
                for item in resp.json().get("organic_results", []):
                    link = item.get("link")
                    if not link:
                        continue
                    key = hashlib.sha1(link.encode()).hexdigest()
                    found[key] = FoundPost(
                        source=self.name,
                        external_id=key,
                        text=f"{item.get('title', '')}. {item.get('snippet', '')}".strip(),
                        post_url=link,
                        can_contact=False,
                    )
                if len(found) >= limit:
                    break
        return list(found.values())[:limit]
