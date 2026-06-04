"""Fail-open Redis cache backend shared across processes.

Process-local ``TTLCache`` instances mean each uvicorn worker / Railway replica
keeps its own copy of the Google Maps cache, so Maps spend scales linearly with
process count (docs/[31] A1). This module backs the cache with Redis so a hit in
one process is a hit for all.

Design constraints:
  * **Fail-open.** Every operation degrades to "Redis unavailable" on *any*
    error (missing ``redis`` package, connection refused, timeout). Callers then
    fall back to their in-process ``TTLCache``. Enrichment is never blocked on
    Redis.
  * **Cheap when down.** After a failure the backend is marked down for a short
    cooldown, so a server with no Redis (tests, local dev) pays one failed probe
    rather than a connection attempt per call.
  * **Atomic.** Redis GET/SET are atomic, so no application-level lock is needed
    on the Redis path (the lock remains only for the dict fallback).

The client is injectable via :func:`set_client_for_test` so the healthy path can
be exercised with a fake client without a running Redis.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional, Tuple

from app.core.config import settings

log = logging.getLogger("roammate.redis_cache")

# Sentinel stored as the Redis value for a negative (None) cache entry, so a
# cached "we looked and found nothing" is distinguishable from a key miss.
_NEG = "\x00neg\x00"

# Returned by get() when Redis could not serve the request — the caller must
# fall back to its local cache.
DOWN: Any = object()


class _RedisBackend:
    def __init__(self) -> None:
        self._client: Any = None
        self._client_built = False
        self._down_until: float = 0.0
        self._cooldown_s: float = 30.0

    # ── connection management ────────────────────────────────────────────
    def _build_client(self) -> Any:
        try:
            import redis.asyncio as aioredis
        except Exception:  # package not installed
            return None
        try:
            return aioredis.Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
                decode_responses=True,
            )
        except Exception:
            return None

    def _client_or_none(self) -> Any:
        if not self._client_built:
            self._client = self._build_client()
            self._client_built = True
        return self._client

    def _up(self) -> bool:
        """Cheap pre-check: skip Redis entirely while in a failure cooldown."""
        return time.monotonic() >= self._down_until

    def _mark_down(self) -> None:
        self._down_until = time.monotonic() + self._cooldown_s

    # ── public API ───────────────────────────────────────────────────────
    async def get(self, key: str) -> Tuple[Any, str]:
        """Return ``(value, state)`` with state ``hit|negative_hit|miss``, or
        ``(None, "down")`` when Redis is unavailable (caller falls back).

        On ``miss``/``negative_hit`` the value is ``None``; the caller keys off
        *state*, substituting its own MISS sentinel for the "miss" case.
        """
        client = self._client_or_none()
        if client is None or not self._up():
            return None, "down"
        try:
            raw = await client.get(key)
        except Exception:
            self._mark_down()
            return None, "down"
        if raw is None:
            return None, "miss"
        if raw == _NEG:
            return None, "negative_hit"
        try:
            return json.loads(raw), "hit"
        except (ValueError, TypeError):
            return None, "miss"

    async def set(
        self, key: str, value: Optional[Any], ttl_s: int, negative_ttl_s: int
    ) -> bool:
        """Store *value* (or a negative marker when ``value is None``). Returns
        True if written to Redis, False when unavailable (caller stores local)."""
        client = self._client_or_none()
        if client is None or not self._up():
            return False
        try:
            if value is None:
                await client.set(key, _NEG, ex=negative_ttl_s)
            else:
                await client.set(key, json.dumps(value), ex=ttl_s)
            return True
        except Exception:
            self._mark_down()
            return False

    def get_client(self) -> Any:
        """Return the live client, or None while down / unavailable. For
        callers (e.g. the circuit breaker) that need raw Redis commands."""
        if not self._up():
            return None
        return self._client_or_none()

    def note_failure(self) -> None:
        """Record that a raw-command caller saw a Redis error (starts cooldown)."""
        self._mark_down()

    async def aclose(self) -> None:
        """Close the underlying client on app shutdown (best-effort)."""
        client = self._client
        if client is not None and hasattr(client, "aclose"):
            try:
                await client.aclose()
            except Exception:
                pass

    # ── test seam ────────────────────────────────────────────────────────
    def set_client_for_test(self, client: Any) -> None:
        self._client = client
        self._client_built = True
        self._down_until = 0.0

    def reset_for_test(self) -> None:
        self._client = None
        self._client_built = False
        self._down_until = 0.0


backend = _RedisBackend()
