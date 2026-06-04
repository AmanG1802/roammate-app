"""§15 Ripple API — admin-only gating and endpoint behaviour."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


async def test_ripple_endpoint_admin_only(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(f"/api/events/ripple/{trip['id']}", json={"delta_minutes": 15}, headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.parametrize("role", ["view_only", "view_with_vote"])
async def test_ripple_endpoint_non_admin_403(client: AsyncClient, auth_headers, second_auth_headers, role):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", role)
    resp = await client.post(f"/api/events/ripple/{trip['id']}", json={"delta_minutes": 15}, headers=second_auth_headers)
    assert resp.status_code == 403


async def test_ripple_endpoint_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(f"/api/events/ripple/{trip['id']}", json={"delta_minutes": 15}, headers=second_auth_headers)
    assert resp.status_code == 403


async def test_ripple_endpoint_fires_and_returns_events(client: AsyncClient, auth_headers):
    today_iso = date.today().isoformat()
    trip = await create_trip(client, auth_headers, start_date=today_iso)
    start = (datetime.now() + timedelta(hours=2)).isoformat()
    await client.post("/api/events", json={
        "trip_id": trip["id"], "title": "Later",
        "day_date": today_iso, "start_time": start,
    }, headers=auth_headers)
    resp = await client.post(f"/api/events/ripple/{trip['id']}", json={"delta_minutes": 15}, headers=auth_headers)
    assert resp.status_code == 200
