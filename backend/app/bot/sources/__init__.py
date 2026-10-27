from app.bot.sources.base import FoundPost, Source, SourceError
from app.bot.sources.telegram import TelegramSource
from app.bot.sources.vk import VKSource
from app.bot.sources.web import WebSource
from app.models.enums import LeadSource


def get_source(name: LeadSource, web_sites: list[str] | None = None) -> Source:
    if name == LeadSource.vk:
        return VKSource()
    if name == LeadSource.telegram:
        return TelegramSource()
    return WebSource(web_sites)


__all__ = ["FoundPost", "Source", "SourceError", "get_source"]
