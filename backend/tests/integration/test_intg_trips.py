"""§3 Trips — CRUD, access control, start-date shifting, day auto-creation,
and full lifecycle tests.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


# ── CRUD basics ───────────────────────────────────────────────────────────────

async def test_create_trip_returns_trip_with_member(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, name="Rome 2026")
    assert trip["name"] == "Rome 2026"
    members = (await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)).json()
    assert any(m["role"] == "admin" for m in members)


async def test_create_trip_sets_destination_metadata(client: AsyncClient, auth_headers):
    trip = await create_trip(
        client, auth_headers,
        destination_city="Tokyo", country_code="JP",
        destination_lat=35.68, destination_lng=139.69,
    )
    assert trip["destination_city"] == "Tokyo"
    assert trip["country_code"] == "JP"


async def test_list_trips_returns_only_own(client: AsyncClient, auth_headers, second_auth_headers):
    await create_trip(client, auth_headers, name="Alice's trip")
    await create_trip(client, second_auth_headers, name="Bob's trip")
    alice_trips = (await client.get("/api/trips", headers=auth_headers)).json()
    names = [t["name"] for t in alice_trips]
    assert "Alice's trip" in names
    assert "Bob's trip" not in names


async def test_get_trip_detail(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == trip["id"]


async def test_get_trip_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/trips/{trip['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


async def test_patch_trip_admin_only(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only")
    resp = await client.patch(f"/api/trips/{trip['id']}", json={"name": "New"}, headers=second_auth_headers)
    assert resp.status_code == 403


async def test_patch_trip_updates_fields(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    resp = await client.patch(f"/api/trips/{trip['id']}", json={"name": "Updated"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


async def test_delete_trip_admin_only(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    resp = await client.delete(f"/api/trips/{trip['id']}", headers=second_auth_headers)
    assert resp.status_code == 403
    resp = await client.delete(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert resp.status_code == 204


# ── Start date / day auto-creation ────────────────────────────────────────────

async def test_create_trip_with_start_date_auto_creates_day1(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    assert len(days) >= 1
    assert days[0]["day_number"] == 1


async def test_create_trip_without_start_date_creates_no_days(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    assert days == []


# ── Start-date shift cascades ─────────────────────────────────────────────────

async def test_patch_trip_start_date_shift_forward_moves_days_and_events(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    days_before = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    resp = await client.patch(
        f"/api/trips/{trip['id']}",
        json={"start_date": "2026-06-05T00:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    days_after = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    if days_after:
        assert days_after[0]["date"] == "2026-06-05"


async def test_patch_trip_end_date_or_timezone_only_no_day_shift(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    resp = await client.patch(
        f"/api/trips/{trip['id']}",
        json={"timezone": "Asia/Bangkok"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    if days:
        assert days[0]["date"] == "2026-06-01"


# ── Lifecycle ─────────────────────────────────────────────────────────────────

async def test_full_trip_lifecycle(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers, name="Italy", start_date="2026-06-01T00:00:00")
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    assert (await client.get(f"/api/trips/{trip['id']}", headers=second_auth_headers)).status_code == 200
    resp = await client.post(f"/api/trips/{trip['id']}/days", json={"date": "2026-06-02"}, headers=auth_headers)
    assert resp.status_code == 201
    with patch("app.services.idea_bin.google_maps_service.find_place", new=AsyncMock(return_value=None)):
        await client.post(f"/api/trips/{trip['id']}/ingest", json={"text": "Colosseum"}, headers=auth_headers)
    await client.post("/api/events", json={
        "trip_id": trip["id"], "title": "Lunch", "day_date": "2026-06-01",
        "start_time": "2026-06-01T13:00:00", "end_time": "2026-06-01T14:00:00",
    }, headers=auth_headers)
    resp = await client.post(f"/api/events/ripple/{trip['id']}", json={
        "delta_minutes": 30, "start_from_time": "2026-06-01T12:00:00",
    }, headers=auth_headers)
    assert resp.status_code == 200
    members = (await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)).json()
    bob = [m for m in members if m["user"]["email"] == "bob@test.com"][0]
    assert (await client.delete(f"/api/trips/{trip['id']}/members/{bob['id']}", headers=auth_headers)).status_code == 204
    assert (await client.get(f"/api/trips/{trip['id']}", headers=second_auth_headers)).status_code == 403
    assert (await client.delete(f"/api/trips/{trip['id']}", headers=auth_headers)).status_code == 204


async def test_view_only_cannot_mutate(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", role="view_only")
    assert (await client.post(f"/api/trips/{trip['id']}/invite", json={"email": "x@x.com"}, headers=second_auth_headers)).status_code == 403
    assert (await client.post(f"/api/trips/{trip['id']}/days", json={"date": "2026-06-01"}, headers=second_auth_headers)).status_code == 403


async def test_idor_across_trips(client: AsyncClient, auth_headers, second_auth_headers):
    trip_a = await create_trip(client, auth_headers, name="A")
    trip_b = await create_trip(client, second_auth_headers, name="B")
    assert (await client.get(f"/api/trips/{trip_a['id']}", headers=second_auth_headers)).status_code == 403
    assert (await client.get(f"/api/events?trip_id={trip_b['id']}", headers=auth_headers)).status_code == 403
