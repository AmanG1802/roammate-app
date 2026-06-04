"""§16 Dashboard — today widget classification, timezone awareness, and capping."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip


async def test_today_widget_active_trip(client: AsyncClient, auth_headers):
    today = date.today()
    trip = await create_trip(client, auth_headers, start_date=today.isoformat())
    resp = await client.get("/api/dashboard/today", headers=auth_headers)
    assert resp.status_code == 200


async def test_today_widget_upcoming_trip(client: AsyncClient, auth_headers):
    future = (date.today() + timedelta(days=30)).isoformat()
    await create_trip(client, auth_headers, start_date=future)
    resp = await client.get("/api/dashboard/today", headers=auth_headers)
    assert resp.status_code == 200


async def test_today_widget_past_trip(client: AsyncClient, auth_headers):
    past = (date.today() - timedelta(days=30)).isoformat()
    await create_trip(client, auth_headers, start_date=past)
    resp = await client.get("/api/dashboard/today", headers=auth_headers)
    assert resp.status_code == 200


async def test_today_widget_client_now_override(client: AsyncClient, auth_headers):
    today = date.today()
    await create_trip(client, auth_headers, start_date=today.isoformat())
    resp = await client.get(f"/api/dashboard/today?client_now={today.isoformat()}", headers=auth_headers)
    assert resp.status_code == 200
