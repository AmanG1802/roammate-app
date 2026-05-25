"""API tests for dashboard.py — GET /api/dashboard/today."""

import pytest
from httpx import AsyncClient
from tests.conftest import create_trip

NO_AUTH = {"Cookie": "", "Authorization": ""}


# ── GET /api/dashboard/today ───────────────────────────────────────────────

async def test_get_today_widget_get(client: AsyncClient, auth_headers: dict):
    # Test 1a - GET - 200 OK - Empty pages when no trips
    resp = await client.get("/api/dashboard/today", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "pages" in data

    # Test 1b - GET - 200 OK - Returns pages after trip creation with start_date
    await create_trip(client, auth_headers, name="Dashboard Trip", start_date="2025-06-01T00:00:00")
    resp = await client.get("/api/dashboard/today", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "pages" in data

    # Test 1c - GET - 200 OK - Default index is present
    assert "default_index" in data

    # Test 1d - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/dashboard/today", headers=NO_AUTH)
    assert resp.status_code == 401
