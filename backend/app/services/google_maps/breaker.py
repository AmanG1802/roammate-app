"""Tiny in-process circuit breaker for Google Maps calls.

State machine:
  closed   -> normal operation; failures counted in a sliding window.
  open     -> short-circuits all calls for ``cool_down_s`` seconds.
  half_open -> the next call is a probe; success closes, failure re-opens.

This is intentionally minimal — when Google is degraded or our quota is
throttled we want to stop ringing the doorbell so user-facing endpoints
don't pile up timeouts.  The breaker is per-process; if multiple workers
run concurrently each maintains its own counter (acceptable for now).
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from app.services.google_maps.tracker import track_call


@dataclass
class _State:
    failure_times: list[float] = field(default_factory=list)
    opened_at: Optional[float] = None
    half_open: bool = False


class CircuitBreaker:
    """Per-process circuit breaker covering all Google calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        window_s: int = 60,
        cool_down_s: int = 30,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.window_s = window_s
        self.cool_down_s = cool_down_s
        self._state = _State()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        s = self._state
        if s.opened_at is None:
            return "closed"
        return "half_open" if s.half_open else "open"

    async def allow(self) -> bool:
        """Return True if a call may proceed; advance state if needed."""
        async with self._lock:
            s = self._state
            now = time.monotonic()
            if s.opened_at is None:
                return True
            elapsed = now - s.opened_at
            if elapsed < self.cool_down_s:
                return False
            if not s.half_open:
                s.half_open = True
                track_call(op="breaker", status="half_open", breaker_state="half_open")
            return True

    async def record_success(self) -> None:
        async with self._lock:
            s = self._state
            if s.opened_at is not None:
                track_call(op="breaker", status="closed", breaker_state="closed")
            s.failure_times.clear()
            s.opened_at = None
            s.half_open = False

    async def record_failure(self) -> None:
        async with self._lock:
            s = self._state
            now = time.monotonic()
            cutoff = now - self.window_s
            s.failure_times = [t for t in s.failure_times if t >= cutoff]
            s.failure_times.append(now)

            if s.half_open:
                s.opened_at = now
                s.half_open = False
                track_call(op="breaker", status="reopened", breaker_state="open")
                return

            if (
                s.opened_at is None
                and len(s.failure_times) >= self.failure_threshold
            ):
                s.opened_at = now
                track_call(op="breaker", status="open", breaker_state="open")


class _RedisBreaker:
    """Cross-process circuit breaker backed by Redis.

    Failures are recorded in a sorted set scored by timestamp; the breaker is
    "open" while an ``opened_at`` key exists (it carries a ``cool_down_s`` TTL,
    so expiry is the half-open probe window). All ops are best-effort: any Redis
    error raises ``_RedisUnavailable`` so the proxy falls back to the in-process
    breaker. See docs/[31] A2.
    """

    _FAILURES_KEY = "gmap:cb:failures"
    _OPENED_KEY = "gmap:cb:opened_at"

    def __init__(self, failure_threshold: int, window_s: int, cool_down_s: int) -> None:
        self.failure_threshold = failure_threshold
        self.window_s = window_s
        self.cool_down_s = cool_down_s

    def _client(self):
        from app.services.cache import redis_cache
        client = redis_cache.backend.get_client()
        if client is None:
            raise _RedisUnavailable()
        return client, redis_cache.backend

    async def is_open(self) -> bool:
        client, backend = self._client()
        try:
            return bool(await client.exists(self._OPENED_KEY))
        except Exception as exc:
            backend.note_failure()
            raise _RedisUnavailable() from exc

    async def record_success(self) -> None:
        client, backend = self._client()
        try:
            await client.delete(self._FAILURES_KEY, self._OPENED_KEY)
        except Exception as exc:
            backend.note_failure()
            raise _RedisUnavailable() from exc

    async def record_failure(self) -> None:
        client, backend = self._client()
        now = time.time()
        try:
            await client.zadd(self._FAILURES_KEY, {f"{now}:{id(now)}": now})
            await client.zremrangebyscore(self._FAILURES_KEY, 0, now - self.window_s)
            await client.expire(self._FAILURES_KEY, self.window_s)
            count = await client.zcard(self._FAILURES_KEY)
            if count >= self.failure_threshold:
                await client.set(self._OPENED_KEY, str(now), ex=self.cool_down_s)
        except Exception as exc:
            backend.note_failure()
            raise _RedisUnavailable() from exc


class _RedisUnavailable(Exception):
    """Raised when a Redis breaker op can't reach Redis; triggers local fallback."""


class CircuitBreakerProxy:
    """Public breaker: uses Redis when reachable, else the in-process breaker.

    Exposes the same async interface (``allow`` / ``record_success`` /
    ``record_failure``) and a synchronous ``state`` property (best-effort, from
    the most recent operation) that v1/v2/base read for logging.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        window_s: int = 60,
        cool_down_s: int = 30,
    ) -> None:
        self._local = CircuitBreaker(failure_threshold, window_s, cool_down_s)
        self._redis = _RedisBreaker(failure_threshold, window_s, cool_down_s)
        self._cached_state = "closed"

    @property
    def state(self) -> str:
        return self._cached_state

    @property
    def _state(self):
        """Expose the in-process breaker's mutable state.

        Tests reset the module-level breaker via ``breaker._state.…``; when
        Redis is unavailable the proxy delegates to this local breaker, so
        resetting it resets the effective breaker.
        """
        return self._local._state

    async def allow(self) -> bool:
        try:
            is_open = await self._redis.is_open()
            self._cached_state = "open" if is_open else "closed"
            return not is_open
        except _RedisUnavailable:
            allowed = await self._local.allow()
            self._cached_state = self._local.state
            return allowed

    async def record_success(self) -> None:
        try:
            await self._redis.record_success()
            self._cached_state = "closed"
            return
        except _RedisUnavailable:
            await self._local.record_success()
            self._cached_state = self._local.state

    async def record_failure(self) -> None:
        try:
            await self._redis.record_failure()
            self._cached_state = "open" if await self._redis.is_open() else "closed"
            return
        except _RedisUnavailable:
            await self._local.record_failure()
            self._cached_state = self._local.state


breaker = CircuitBreakerProxy()
