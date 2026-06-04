"""Unit tests for app.services.google_maps.breaker — in-process circuit breaker.

Tests the CircuitBreaker state machine (closed → open → half_open → closed).
Uses asyncio but no DB or network. The Redis-backed variant is integration-tier.
"""
import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock

from app.services.google_maps.breaker import CircuitBreaker


@pytest.fixture
def breaker():
    """Small thresholds for fast tests."""
    return CircuitBreaker(failure_threshold=3, window_s=10, cool_down_s=1)


class TestCircuitBreakerClosed:
    @pytest.mark.asyncio
    async def test_initial_state_closed(self, breaker):
        # Test 1a - Breaker starts in closed state
        assert breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_allow_when_closed(self, breaker):
        # Test 1b - Calls are allowed when closed
        assert await breaker.allow() is True

    @pytest.mark.asyncio
    async def test_stays_closed_below_threshold(self, breaker):
        # Test 1c - Fewer failures than threshold keeps breaker closed
        await breaker.record_failure()
        await breaker.record_failure()
        assert breaker.state == "closed"
        assert await breaker.allow() is True


class TestCircuitBreakerOpening:
    @pytest.mark.asyncio
    async def test_opens_at_threshold(self, breaker):
        # Test 1a - Reaching failure_threshold opens the breaker
        for _ in range(3):
            await breaker.record_failure()
        assert breaker.state == "open"

    @pytest.mark.asyncio
    async def test_blocks_calls_when_open(self, breaker):
        # Test 1b - Calls are blocked when open
        for _ in range(3):
            await breaker.record_failure()
        assert await breaker.allow() is False


class TestCircuitBreakerHalfOpen:
    @pytest.mark.asyncio
    async def test_transitions_to_half_open(self, breaker):
        # Test 1a - After cool_down_s, breaker becomes half_open on next allow()
        for _ in range(3):
            await breaker.record_failure()
        assert breaker.state == "open"

        await asyncio.sleep(1.1)  # Wait for cool_down_s=1
        result = await breaker.allow()
        assert result is True
        assert breaker.state == "half_open"

    @pytest.mark.asyncio
    async def test_success_in_half_open_closes(self, breaker):
        # Test 1b - Success during half_open closes the breaker
        for _ in range(3):
            await breaker.record_failure()
        await asyncio.sleep(1.1)
        await breaker.allow()  # transitions to half_open
        await breaker.record_success()
        assert breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_failure_in_half_open_reopens(self, breaker):
        # Test 1c - Failure during half_open re-opens the breaker
        for _ in range(3):
            await breaker.record_failure()
        await asyncio.sleep(1.1)
        await breaker.allow()  # transitions to half_open
        await breaker.record_failure()
        assert breaker.state == "open"


class TestCircuitBreakerRecovery:
    @pytest.mark.asyncio
    async def test_success_clears_failures(self, breaker):
        # Test 1a - record_success resets failure count
        await breaker.record_failure()
        await breaker.record_failure()
        await breaker.record_success()
        # One more failure should not open (failures were cleared)
        await breaker.record_failure()
        assert breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_old_failures_expire_from_window(self):
        # Test 1b - Failures older than window_s are pruned
        breaker = CircuitBreaker(failure_threshold=3, window_s=1, cool_down_s=1)
        await breaker.record_failure()
        await breaker.record_failure()
        await asyncio.sleep(1.1)  # Window expires
        await breaker.record_failure()  # Only 1 recent failure
        assert breaker.state == "closed"


class TestCircuitBreakerEdgeCases:
    @pytest.mark.asyncio
    async def test_zero_failures_stays_closed(self):
        # Test 1a - Never calling record_failure keeps closed
        breaker = CircuitBreaker(failure_threshold=5, window_s=60, cool_down_s=30)
        for _ in range(10):
            assert await breaker.allow() is True
        assert breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_threshold_one(self):
        # Test 1b - failure_threshold=1 opens on first failure
        breaker = CircuitBreaker(failure_threshold=1, window_s=60, cool_down_s=1)
        await breaker.record_failure()
        assert breaker.state == "open"
