"""D3 — opt-in cursor pagination on GET /api/trips/.

Verifies the backward-compatible contract: no params → full bare list (current
client behaviour); with limit/cursor → one keyset page + X-Next-Cursor header.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip


@pytest.fixture
async def two_trips(client: AsyncClient, auth_headers: dict):
    # Free tier caps active trips at 2 — enough to exercise multi-page keyset.
    for i in range(2):
        await create_trip(client, auth_headers, name=f"Trip {i}")
    return auth_headers


async def test_no_params_returns_full_list(client: AsyncClient, two_trips):
    resp = await client.get("/api/trips/", headers=two_trips)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)            # bare array shape unchanged
    assert len(body) == 2
    assert "X-Next-Cursor" not in resp.headers


async def test_limit_returns_one_page_with_cursor(client: AsyncClient, two_trips):
    resp = await client.get("/api/trips/?limit=1", headers=two_trips)
    assert resp.status_code == 200
    page = resp.json()
    assert len(page) == 1
    assert resp.headers["X-Has-More"] == "true"
    assert "X-Next-Cursor" in resp.headers


async def test_cursor_walks_all_pages_without_overlap(client: AsyncClient, two_trips):
    seen: list[int] = []
    cursor = None
    for _ in range(10):  # safety bound
        url = "/api/trips/?limit=1" + (f"&cursor={cursor}" if cursor else "")
        resp = await client.get(url, headers=two_trips)
        assert resp.status_code == 200
        page = resp.json()
        seen.extend(t["id"] for t in page)
        if resp.headers.get("X-Has-More") != "true":
            break
        cursor = resp.headers["X-Next-Cursor"]
    # Both trips, each exactly once, newest-first (descending id).
    assert len(seen) == 2
    assert len(set(seen)) == 2
    assert seen == sorted(seen, reverse=True)
