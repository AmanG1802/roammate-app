"""§4D — Circuit breaker tests for Google Maps."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from app.services.google_maps.breaker import CircuitBreaker


@pytest.fixture
def breaker():
    return CircuitBreaker(failure_threshold=3, window_s=60, cool_down_s=2)


async def test_breaker_starts_closed(breaker):
    assert breaker.state == "closed"
    assert await breaker.allow() is True


async def test_breaker_opens_after_N_consecutive_failures(breaker):
    with patch("app.services.google_maps.breaker.track_call"):
        for _ in range(3):
            await breaker.record_failure()
    assert breaker.state == "open"


async def test_breaker_open_short_circuits_calls(breaker):
    with patch("app.services.google_maps.breaker.track_call"):
        for _ in range(3):
            await breaker.record_failure()
    assert await breaker.allow() is False


async def test_breaker_half_open_after_cooldown_recovers_on_success(breaker):
    with patch("app.services.google_maps.breaker.track_call"):
        for _ in range(3):
            await breaker.record_failure()

    assert breaker.state == "open"

    # Simulate cooldown elapsed
    breaker._state.opened_at = time.monotonic() - 10

    with patch("app.services.google_maps.breaker.track_call"):
        # Next allow() call transitions to half_open
        assert await breaker.allow() is True
        assert breaker.state == "half_open"

        # Success closes the breaker
        await breaker.record_success()
    assert breaker.state == "closed"
    assert await breaker.allow() is True


async def test_breaker_half_open_failure_reopens(breaker):
    with patch("app.services.google_maps.breaker.track_call"):
        for _ in range(3):
            await breaker.record_failure()

    breaker._state.opened_at = time.monotonic() - 10

    with patch("app.services.google_maps.breaker.track_call"):
        await breaker.allow()  # transitions to half_open
        await breaker.record_failure()  # reopens

    assert breaker.state == "open"


async def test_breaker_success_resets_failure_count(breaker):
    with patch("app.services.google_maps.breaker.track_call"):
        await breaker.record_failure()
        await breaker.record_failure()
        await breaker.record_success()
    assert breaker.state == "closed"
    assert len(breaker._state.failure_times) == 0


async def test_breaker_failures_outside_window_do_not_count():
    brk = CircuitBreaker(failure_threshold=3, window_s=1, cool_down_s=2)
    with patch("app.services.google_maps.breaker.track_call"):
        # Record failures in the past (outside the 1s window)
        now = time.monotonic()
        brk._state.failure_times = [now - 5, now - 4]
        await brk.record_failure()
    # Old failures outside window get pruned; only 1 recent failure
    assert brk.state == "closed"
