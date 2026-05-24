"""Shared, process-wide LLM SDK clients.

The registry builds a fresh ``BaseLLMModel`` wrapper per request. Each provider
SDK client (``AsyncOpenAI`` / ``AsyncAnthropic`` / ``genai.Client``) owns an HTTP
connection pool, so constructing one per request leaks sockets and risks a
double-init race that orphans clients under concurrent first-request bursts.

Memoize one client per ``(provider, api_key)``. Construction is synchronous, so
the check-then-set has no ``await`` between read and write and is therefore
race-free under asyncio (single-threaded event loop). See docs/[31] A6.
"""
from __future__ import annotations

from typing import Any, Callable

_clients: dict[tuple[str, str], Any] = {}


def get_shared_client(provider: str, api_key: str, factory: Callable[[], Any]) -> Any:
    """Return the memoized SDK client for *(provider, api_key)*, building once."""
    key = (provider, api_key or "")
    client = _clients.get(key)
    if client is None:
        client = factory()
        _clients[key] = client
    return client


def clear_shared_clients() -> None:
    """Drop all cached clients (test isolation / shutdown)."""
    _clients.clear()
