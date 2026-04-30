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


breaker = CircuitBreaker()
