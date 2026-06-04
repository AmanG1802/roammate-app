"""Unit tests for app.utils.tasks — fire-and-forget async task management.

Tests the fire_and_forget function with and without a running event loop.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch

from app.utils.tasks import fire_and_forget, _active_tasks


class TestFireAndForget:
    @pytest.mark.asyncio
    async def test_fire_and_forget_schedules_task(self):
        # Test 1a - Coroutine is scheduled and runs to completion
        result = []

        async def _coro():
            result.append("done")

        fire_and_forget(_coro())
        await asyncio.sleep(0.05)
        assert result == ["done"]

    @pytest.mark.asyncio
    async def test_fire_and_forget_task_tracked(self):
        # Test 1b - Task is held in _active_tasks while running
        started = asyncio.Event()
        finish = asyncio.Event()

        async def _slow_coro():
            started.set()
            await finish.wait()

        initial_count = len(_active_tasks)
        fire_and_forget(_slow_coro())
        await started.wait()
        assert len(_active_tasks) > initial_count

        finish.set()
        await asyncio.sleep(0.05)
        # Task should be cleaned up after completion
        assert len(_active_tasks) == initial_count

    @pytest.mark.asyncio
    async def test_fire_and_forget_exception_does_not_propagate(self):
        # Test 1c - Exception in coro does not crash the caller
        async def _failing_coro():
            raise ValueError("test error")

        fire_and_forget(_failing_coro())
        await asyncio.sleep(0.05)
        # If we get here, the exception didn't propagate

    def test_fire_and_forget_no_loop(self):
        # Test 1d - When no event loop is running, coro is closed (no-op)
        call_count = []

        async def _coro():
            call_count.append(1)

        # Create a coro outside any running loop context
        coro = _coro()
        # Simulate no running loop by patching create_task to raise RuntimeError
        with patch("app.utils.tasks.asyncio.create_task", side_effect=RuntimeError("no loop")):
            fire_and_forget(coro)

        # Coro should have been closed, not awaited
        assert len(call_count) == 0

    @pytest.mark.asyncio
    async def test_fire_and_forget_cleanup_callback(self):
        # Test 1e - Done callback removes task from _active_tasks
        async def _quick():
            pass

        initial = len(_active_tasks)
        fire_and_forget(_quick())
        await asyncio.sleep(0.05)
        assert len(_active_tasks) == initial
