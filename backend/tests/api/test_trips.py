"""Tests for /api/trips/* (CRUD, date-shift cascade, authz)."""
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


async def test_create_trip_basic(client: AsyncClient, auth_headers):
    resp = await client.post("/api/trips/", json={"name": "Paris"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Paris"
    assert "id" in data
    assert "created_by_id" in data


async def test_create_trip_sets_creator_as_admin(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, name="Rome")
    # Creator should now see the trip in their list
    resp = await client.get("/api/trips/", headers=auth_headers)
    assert resp.status_code == 200
    trips = resp.json()
    assert any(t["id"] == trip["id"] and t["my_role"] == "admin" for t in trips)


async def test_create_trip_with_start_date_creates_day1(
    client: AsyncClient, auth_headers
):
    start = datetime(2026, 6, 1).isoformat()
    trip = await create_trip(client, auth_headers, name="T", start_date=start)
    resp = await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)
    days = resp.json()
    assert len(days) == 1
    assert days[0]["day_number"] == 1
    assert days[0]["date"] == "2026-06-01"


async def test_create_trip_without_start_date_has_no_days(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers, name="No date")
    resp = await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)
    assert resp.json() == []


async def test_create_trip_end_before_start_rejected(
    client: AsyncClient, auth_headers
):
    resp = await client.post(
        "/api/trips/",
        json={
            "name": "Invalid",
            "start_date": "2026-06-10T00:00:00",
            "end_date": "2026-06-05T00:00:00",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_get_trips_only_accepted(
    client: AsyncClient, auth_headers, second_auth_headers
):
    # Alice creates a trip; Bob is invited but doesn't accept
    trip = await create_trip(client, auth_headers, name="T")
    await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com", "role": "view_only"},
        headers=auth_headers,
    )
    # Bob's trip list should not include the trip yet
    resp = await client.get("/api/trips/", headers=second_auth_headers)
    assert resp.json() == []


async def test_get_trip_forbidden_for_non_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/trips/{trip['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


async def test_get_trip_allows_any_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com"
    )
    resp = await client.get(f"/api/trips/{trip['id']}", headers=second_auth_headers)
    assert resp.status_code == 200


async def test_patch_trip_name_by_admin(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, name="Old")
    resp = await client.patch(
        f"/api/trips/{trip['id']}", json={"name": "New"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


async def test_patch_trip_by_non_admin_forbidden(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com",
        role="view_only",
    )
    resp = await client.patch(
        f"/api/trips/{trip['id']}", json={"name": "X"}, headers=second_auth_headers
    )
    assert resp.status_code == 403


async def test_patch_trip_by_non_member_forbidden(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.patch(
        f"/api/trips/{trip['id']}", json={"name": "X"}, headers=second_auth_headers
    )
    assert resp.status_code == 403


async def test_patch_trip_end_before_start_rejected(client: AsyncClient, auth_headers):
    trip = await create_trip(
        client, auth_headers,
        start_date="2026-06-01T00:00:00", end_date="2026-06-10T00:00:00",
    )
    resp = await client.patch(
        f"/api/trips/{trip['id']}",
        json={"start_date": "2026-06-11T00:00:00", "end_date": "2026-06-05T00:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ── Date-shift cascade ────────────────────────────────────────────────────────

async def test_patch_trip_start_date_forward_shifts_days(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(
        client, auth_headers, start_date="2026-06-01T00:00:00"
    )
    # add days 2 and 3
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": "2026-06-02"}, headers=auth_headers
    )
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": "2026-06-03"}, headers=auth_headers
    )
    # shift start +5 days
    resp = await client.patch(
        f"/api/trips/{trip['id']}",
        json={"start_date": "2026-06-06T00:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    dates = sorted([d["date"] for d in days])
    assert dates == ["2026-06-06", "2026-06-07", "2026-06-08"]


async def test_patch_trip_start_date_backward_shifts_days(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(
        client, auth_headers, start_date="2026-06-10T00:00:00"
    )
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": "2026-06-11"}, headers=auth_headers
    )
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": "2026-06-12"}, headers=auth_headers
    )
    resp = await client.patch(
        f"/api/trips/{trip['id']}",
        json={"start_date": "2026-06-05T00:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    assert sorted([d["date"] for d in days]) == ["2026-06-05", "2026-06-06", "2026-06-07"]


async def test_patch_trip_date_shift_moves_events(client: AsyncClient, auth_headers):
    trip = await create_trip(
        client, auth_headers, start_date="2026-06-01T00:00:00"
    )
    # Create an event on day 1
    ev = await client.post(
        "/api/events/",
        json={
            "trip_id": trip["id"],
            "title": "Colosseum",
            "day_date": "2026-06-01",
        },
        headers=auth_headers,
    )
    assert ev.status_code == 201
    # Shift +3 days
    await client.patch(
        f"/api/trips/{trip['id']}",
        json={"start_date": "2026-06-04T00:00:00"},
        headers=auth_headers,
    )
    events = (
        await client.get(f"/api/events/?trip_id={trip['id']}", headers=auth_headers)
    ).json()
    assert events[0]["day_date"] == "2026-06-04"


async def test_patch_trip_same_start_date_is_noop(client: AsyncClient, auth_headers):
    trip = await create_trip(
        client, auth_headers, start_date="2026-06-01T00:00:00"
    )
    resp = await client.patch(
        f"/api/trips/{trip['id']}",
        json={"start_date": "2026-06-01T00:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    assert days[0]["date"] == "2026-06-01"


# ── Delete cascade ────────────────────────────────────────────────────────────

async def test_delete_trip_by_admin_cascades(client: AsyncClient, auth_headers):
    trip = await create_trip(
        client, auth_headers, start_date="2026-06-01T00:00:00"
    )
    await client.post(
        f"/api/trips/{trip['id']}/ingest",
        json={"text": "Colosseum"},
        headers=auth_headers,
    )
    await client.post(
        "/api/events/",
        json={"trip_id": trip["id"], "title": "Lunch"},
        headers=auth_headers,
    )
    resp = await client.delete(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert resp.status_code == 204
    # trip is gone
    resp = await client.get(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert resp.status_code in (403, 404)


async def test_delete_trip_by_non_admin_forbidden(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com"
    )
    resp = await client.delete(f"/api/trips/{trip['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


async def test_all_trip_routes_require_auth(client: AsyncClient):
    routes = [
        ("GET", "/api/trips/"),
        ("POST", "/api/trips/"),
        ("GET", "/api/trips/1"),
        ("DELETE", "/api/trips/1"),
    ]
    for method, path in routes:
        resp = await client.request(method, path, json={"name": "x"})
        assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}"
