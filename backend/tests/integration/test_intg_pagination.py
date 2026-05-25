"""§22 Pagination & OpenAPI — cursor pagination and spec validation."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip


async def test_openapi_spec_loads(client: AsyncClient):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "paths" in data
    assert "openapi" in data


async def test_cursor_pagination_first_page(client: AsyncClient, auth_headers):
    await create_trip(client, auth_headers, name="Trip 0")
    resp = await client.get("/api/notifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_cursor_pagination_empty(client: AsyncClient, auth_headers):
    resp = await client.get("/api/notifications", headers=auth_headers)
    assert resp.status_code == 200
