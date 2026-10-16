"""
app/cache.py — Redis client.
Redis is optional — if unavailable, the app runs in degraded mode
(no brute-force protection or token revocation, but login/register still works).
"""
from __future__ import annotations

import redis.asyncio as aioredis
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

_client: aioredis.Redis | None = None
_redis_available: bool | None = None   # None = not yet tested


async def get_redis() -> aioredis.Redis | None:
    """Return Redis client, or None if Redis is not reachable."""
    global _client, _redis_available

    if _redis_available is False:
        return None          # already confirmed down — don't retry every call

    if _client is None:
        try:
            _client = aioredis.from_url(
                get_settings().redis_url,
                decode_responses=True,
                socket_connect_timeout=2,   # fail fast
            )
            await _client.ping()            # confirm connection works
            _redis_available = True
            log.info("redis_connected")
        except Exception as exc:
            _redis_available = False
            _client = None
            log.warning("redis_unavailable", reason=str(exc),
                        note="Running without Redis — no rate-limiting or token revocation")
            return None

    return _client


async def close_redis() -> None:
    global _client, _redis_available
    if _client is not None:
        await _client.aclose()
        _client = None
    _redis_available = None


async def allow_rate_limit(key: str, *, limit: int, window_seconds: int) -> bool:
    """Best-effort fixed-window limiter; degraded mode allows traffic if Redis is down."""
    client = await get_redis()
    if client is None:
        return True
    bucket = f"linkforge:rate:{key}"
    try:
        count = await client.incr(bucket)
        if count == 1:
            await client.expire(bucket, window_seconds)
        return count <= limit
    except Exception as exc:
        log.warning("rate_limit_failed", error=str(exc))
        return True
