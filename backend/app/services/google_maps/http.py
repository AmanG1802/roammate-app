"""Process-wide shared httpx client for Google Maps single-hit calls.

The batch enrichment loop already reuses one client across its N calls, but the
bare single-hit endpoints (find_place, place_details, route polyline, photo)
each opened a fresh ``httpx.AsyncClient`` — paying a ~50-100ms TCP+TLS handshake
every time. This module holds one app-scoped client (created in the FastAPI
lifespan, closed on shutdown) that those calls reuse. See docs/[31] A5.

The client is ``None`` until the lifespan sets it, so unit tests (which patch
``v1.httpx.AsyncClient`` and never run the app lifespan) transparently fall back
to the per-call ``async with httpx.AsyncClient()`` path.
"""
from __future__ import annotations

from typing import Optional

import httpx

_shared_client: Optional[httpx.AsyncClient] = None


def build_client() -> httpx.AsyncClient:
    """Construct the shared client with sane connect/read timeouts and pooling."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(connect=3, read=10, write=5, pool=5),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
    )


def set_shared_client(client: Optional[httpx.AsyncClient]) -> None:
    global _shared_client
    _shared_client = client


def get_shared_client() -> Optional[httpx.AsyncClient]:
    """Return the app-scoped client, or None when running outside the app
    lifespan (tests / scripts) so callers fall back to a per-call client."""
    return _shared_client
