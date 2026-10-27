"""Ограничение частоты запросов.

Используется Redis (общий счётчик для всех процессов). Если Redis недоступен,
работает запасной счётчик в памяти процесса.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore[assignment,misc]


class RateLimiter:
    def __init__(self) -> None:
        self._memory: dict[str, deque[float]] = defaultdict(deque)
        self._redis = None
        self._redis_failed = False

    async def _get_redis(self):
        if self._redis_failed or Redis is None:
            return None
        if self._redis is None:
            self._redis = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        return self._redis

    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Возвращает True, если запрос укладывается в лимит."""
        redis = await self._get_redis()
        if redis is not None:
            try:
                bucket = f"rl:{key}:{int(time.time() // window_seconds)}"
                count = await redis.incr(bucket)
                if count == 1:
                    await redis.expire(bucket, window_seconds)
                return count <= limit
            except Exception:
                self._redis_failed = True

        now = time.monotonic()
        hits = self._memory[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._memory.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(name: str, limit: int, window_seconds: int):
    async def dependency(request: Request) -> None:
        allowed = await limiter.hit(f"{name}:{client_ip(request)}", limit, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много запросов. Попробуйте позже.",
            )

    return dependency
