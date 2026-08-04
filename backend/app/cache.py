"""
app/cache.py — Redis client.
Redis is optional — if unavailable, the app runs in degraded mode
(no brute-force protection or token revocation, but login/register still works).
"""
from __future__ import annotations

import structlog
import redis.asyncio as aioredis

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
