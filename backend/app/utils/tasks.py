"""Helpers for safely spawning fire-and-forget asyncio tasks.

``asyncio.create_task(coro)`` returns a task the event loop holds only a *weak*
reference to.  If the caller drops its reference (the common fire-and-forget
pattern), the task can be garbage-collected mid-flight before it finishes —
silently dropping the work (e.g. token-usage / Maps-usage metric writes).

``fire_and_forget`` keeps a strong reference in a module-level set until the
task completes, then discards it via ``add_done_callback``.  See docs/[31] A3.
"""
from __future__ import annotations

import asyncio
from typing import Any, Coroutine

# Strong references to in-flight fire-and-forget tasks (prevents GC).
_active_tasks: set[asyncio.Task] = set()


def fire_and_forget(coro: Coroutine[Any, Any, Any]) -> None:
    """Schedule *coro* on the running loop without awaiting it.

    Holds a strong reference until completion. No-ops (and closes the coro to
    avoid a "never awaited" warning) when there is no running event loop.
    """
    try:
        task = asyncio.create_task(coro)
    except RuntimeError:
        # No running loop (e.g. called from sync context / outside the app).
        coro.close()
        return
    _active_tasks.add(task)
    task.add_done_callback(_active_tasks.discard)
