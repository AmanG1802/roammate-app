"""A1/A2 — Redis-backed cache + circuit breaker, healthy path.

Real Redis isn't available in CI, so a minimal in-memory fake client is injected
to exercise the "Redis reachable" branch. The fallback (Redis down) path is
covered by the existing test_maps_cache.py / test_maps_breaker.py suites, which
run with no client injected.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.cache import redis_cache
from app.services.google_maps import cache as gmap_cache
from app.services.google_maps.breaker import CircuitBreakerProxy


class FakeRedis:
    """Tiny async stand-in supporting the GET/SET + ZSET ops we use."""

    def __init__(self) -> None:
        self.kv: dict = {}
        self.z: dict = {}

    async def get(self, key):
        return self.kv.get(key)

    async def set(self, key, value, ex=None):
        self.kv[key] = value

    async def delete(self, *keys):
        for k in keys:
            self.kv.pop(k, None)
            self.z.pop(k, None)

    async def exists(self, key):
        return 1 if key in self.kv else 0

    async def zadd(self, key, mapping):
        self.z.setdefault(key, {}).update(mapping)

    async def zremrangebyscore(self, key, lo, hi):
        z = self.z.get(key, {})
        for member, score in list(z.items()):
            if lo <= score <= hi:
                del z[member]

    async def expire(self, key, ttl):
        pass

    async def zcard(self, key):
        return len(self.z.get(key, {}))


@pytest.fixture
def fake_redis():
    fake = FakeRedis()
    redis_cache.backend.set_client_for_test(fake)
    gmap_cache.clear_all()
    yield fake
    redis_cache.backend.reset_for_test()
    gmap_cache.clear_all()


# ── Cache (A1) ────────────────────────────────────────────────────────────────
async def test_redis_find_place_roundtrip(fake_redis):
    await gmap_cache.set_find_place("Eiffel Tower", {"id": "e1"})
    # Stored in Redis, not the local TTLCache.
    assert any(k.startswith("gmap:find_place:") for k in fake_redis.kv)
    val, state = await gmap_cache.get_find_place("Eiffel Tower")
    assert state == "hit" and val["id"] == "e1"


async def test_redis_negative_cache(fake_redis):
    await gmap_cache.set_find_place("nowhere", None)
    val, state = await gmap_cache.get_find_place("nowhere")
    assert state == "negative_hit" and val is None


async def test_redis_miss_returns_sentinel(fake_redis):
    val, state = await gmap_cache.get_find_place("unseen")
    assert state == "miss" and val is gmap_cache.MISS


async def test_redis_place_details_field_signature_isolated(fake_redis):
    await gmap_cache.set_place_details("pid", "sigA", {"r": 4.5})
    await gmap_cache.set_place_details("pid", "sigB", {"r": 3.0})
    a, _ = await gmap_cache.get_place_details("pid", "sigA")
    b, _ = await gmap_cache.get_place_details("pid", "sigB")
    assert a["r"] == 4.5 and b["r"] == 3.0


async def test_falls_back_to_local_when_redis_down():
    # No client injected → backend reports down → local TTLCache is used.
    redis_cache.backend.reset_for_test()
    gmap_cache.clear_all()
    await gmap_cache.set_find_place("Louvre", {"id": "L"})
    val, state = await gmap_cache.get_find_place("Louvre")
    assert state == "hit" and val["id"] == "L"
    gmap_cache.clear_all()


# ── Breaker (A2) ────────────────────────────────────────────────────────────
async def test_redis_breaker_opens_after_threshold(fake_redis):
    b = CircuitBreakerProxy(failure_threshold=3, window_s=60, cool_down_s=30)
    assert await b.allow() is True
    for _ in range(3):
        await b.record_failure()
    assert b.state == "open"
    assert await b.allow() is False


async def test_redis_breaker_success_closes(fake_redis):
    b = CircuitBreakerProxy(failure_threshold=2, window_s=60, cool_down_s=30)
    for _ in range(2):
        await b.record_failure()
    assert await b.allow() is False
    await b.record_success()
    assert await b.allow() is True
    assert b.state == "closed"


async def test_breaker_falls_back_to_local_when_redis_down():
    redis_cache.backend.reset_for_test()
    b = CircuitBreakerProxy(failure_threshold=2, window_s=60, cool_down_s=30)
    with patch("app.services.google_maps.breaker.track_call"):
        for _ in range(2):
            await b.record_failure()
        # Local in-process breaker took over and opened.
        assert await b.allow() is False
