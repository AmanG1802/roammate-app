"""Tests for route persistence (DayRoute): POST upsert + GET with staleness."""
from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, wait_for_tracker_writes


async def _create_event(
    client: AsyncClient,
    headers: dict,
    trip_id: int,
    *,
    title: str,
    day: date,
    start: datetime | None,
    end: datetime | None,
    lat: float = 13.75,
    lng: float = 100.50,
    sort_order: int = 0,
) -> dict:
    payload = {
        "trip_id": trip_id,
        "title": title,
        "lat": lat,
        "lng": lng,
        "day_date": day.isoformat(),
        "start_time": start.isoformat() if start else None,
        "end_time": end.isoformat() if end else None,
        "sort_order": sort_order,
    }
    resp = await client.post("/api/events/", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _setup_routable_day(client: AsyncClient, headers: dict):
    """Create a trip with two timed events — the minimum for a route."""
    trip = await create_trip(client, headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())
    await _create_event(
        client, headers, trip["id"],
        title="Stop A", day=today,
        start=base.replace(hour=9), end=base.replace(hour=10),
        lat=13.7465, lng=100.4927, sort_order=1,
    )
    await _create_event(
        client, headers, trip["id"],
        title="Stop B", day=today,
        start=base.replace(hour=11), end=base.replace(hour=12),
        lat=13.7500, lng=100.4914, sort_order=2,
    )
    return trip, today


# ─── POST persists route to DB ─────────────────────────────────────────────


async def test_post_route_returns_fingerprint_and_computed_at(
    client: AsyncClient, auth_headers
):
    trip, today = await _setup_routable_day(client, auth_headers)

    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["waypoint_fingerprint"] is not None
    assert len(body["waypoint_fingerprint"]) == 16
    assert body["computed_at"] is not None
    assert body["is_stale"] is False


async def test_post_route_persists_and_get_returns_same_data(
    client: AsyncClient, auth_headers
):
    trip, today = await _setup_routable_day(client, auth_headers)

    post_resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert post_resp.status_code == 200
    post_body = post_resp.json()

    get_resp = await client.get(
        f"/api/trips/{trip['id']}/route",
        params={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    get_body = get_resp.json()

    assert get_body["encoded_polyline"] == post_body["encoded_polyline"]
    assert get_body["legs"] == post_body["legs"]
    assert get_body["total_duration_s"] == post_body["total_duration_s"]
    assert get_body["total_distance_m"] == post_body["total_distance_m"]
    assert get_body["ordered_event_ids"] == post_body["ordered_event_ids"]
    assert get_body["waypoint_fingerprint"] == post_body["waypoint_fingerprint"]
    assert get_body["is_stale"] is False


async def test_post_route_upserts_on_second_call(
    client: AsyncClient, auth_headers
):
    trip, today = await _setup_routable_day(client, auth_headers)

    resp1 = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp1.status_code == 200

    resp2 = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["waypoint_fingerprint"] == resp1.json()["waypoint_fingerprint"]


# ─── GET endpoint ──────────────────────────────────────────────────────────


async def test_get_route_returns_null_when_no_stored_route(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    tomorrow = date.today() + timedelta(days=1)

    resp = await client.get(
        f"/api/trips/{trip['id']}/route",
        params={"day_date": tomorrow.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json() is None or resp.text == "null"


async def test_get_route_detects_stale_after_event_time_change(
    client: AsyncClient, auth_headers
):
    trip, today = await _setup_routable_day(client, auth_headers)

    # Compute and persist route
    post_resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert post_resp.status_code == 200

    # Change event time — alters the fingerprint
    events_resp = await client.get(
        f"/api/events/", params={"trip_id": trip["id"]},
        headers=auth_headers,
    )
    events = events_resp.json()
    ev = events[0]
    base = datetime.combine(today, datetime.min.time())
    new_start = base.replace(hour=8)
    new_end = base.replace(hour=9)
    patch_resp = await client.patch(
        f"/api/events/{ev['id']}",
        json={"start_time": new_start.isoformat(), "end_time": new_end.isoformat()},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200, patch_resp.text

    # GET should now report stale
    get_resp = await client.get(
        f"/api/trips/{trip['id']}/route",
        params={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["is_stale"] is True


async def test_get_route_detects_stale_after_event_added(
    client: AsyncClient, auth_headers
):
    trip, today = await _setup_routable_day(client, auth_headers)

    # Compute and persist route
    await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )

    # Add a third event
    base = datetime.combine(today, datetime.min.time())
    await _create_event(
        client, auth_headers, trip["id"],
        title="Stop C", day=today,
        start=base.replace(hour=14), end=base.replace(hour=15),
        lat=13.7600, lng=100.5000, sort_order=3,
    )

    get_resp = await client.get(
        f"/api/trips/{trip['id']}/route",
        params={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["is_stale"] is True


async def test_get_route_not_stale_when_title_changes(
    client: AsyncClient, auth_headers
):
    """Non-waypoint changes (title, description) should NOT make route stale."""
    trip, today = await _setup_routable_day(client, auth_headers)

    await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )

    # Change title only
    events_resp = await client.get(
        f"/api/events/", params={"trip_id": trip["id"]},
        headers=auth_headers,
    )
    events = events_resp.json()
    ev = events[0]
    patch_resp = await client.patch(
        f"/api/events/{ev['id']}",
        json={"title": "Renamed Stop"},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200, patch_resp.text

    get_resp = await client.get(
        f"/api/trips/{trip['id']}/route",
        params={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["is_stale"] is False


# ─── Fingerprint unit tests ────────────────────────────────────────────────


def test_fingerprint_deterministic():
    """Same inputs produce same fingerprint."""
    from app.api.endpoints.maps import compute_waypoint_fingerprint
    from unittest.mock import MagicMock

    def make_event(id, lat, lng, place_id, start_time, end_time, sort_order):
        e = MagicMock()
        e.id = id
        e.lat = lat
        e.lng = lng
        e.place_id = place_id
        e.start_time = start_time
        e.end_time = end_time
        e.sort_order = sort_order
        return e

    base = datetime(2026, 5, 9, 9, 0)
    events = [
        make_event(1, 13.75, 100.50, None, base, base.replace(hour=10), 1),
        make_event(2, 13.76, 100.51, None, base.replace(hour=11), base.replace(hour=12), 2),
    ]
    fp1 = compute_waypoint_fingerprint(events)
    fp2 = compute_waypoint_fingerprint(events)
    assert fp1 == fp2
    assert len(fp1) == 16


def test_fingerprint_changes_on_time_change():
    """Changing start_time alters the fingerprint."""
    from app.api.endpoints.maps import compute_waypoint_fingerprint
    from unittest.mock import MagicMock

    def make_event(id, lat, lng, place_id, start_time, end_time, sort_order):
        e = MagicMock()
        e.id = id
        e.lat = lat
        e.lng = lng
        e.place_id = place_id
        e.start_time = start_time
        e.end_time = end_time
        e.sort_order = sort_order
        return e

    base = datetime(2026, 5, 9, 9, 0)
    events_v1 = [
        make_event(1, 13.75, 100.50, None, base, base.replace(hour=10), 1),
        make_event(2, 13.76, 100.51, None, base.replace(hour=11), base.replace(hour=12), 2),
    ]
    events_v2 = [
        make_event(1, 13.75, 100.50, None, base.replace(hour=8), base.replace(hour=9), 1),
        make_event(2, 13.76, 100.51, None, base.replace(hour=11), base.replace(hour=12), 2),
    ]
    fp1 = compute_waypoint_fingerprint(events_v1)
    fp2 = compute_waypoint_fingerprint(events_v2)
    assert fp1 != fp2


def test_fingerprint_ignores_non_routable_events():
    """Events without lat/lng/place_id are excluded from the fingerprint."""
    from app.api.endpoints.maps import compute_waypoint_fingerprint
    from unittest.mock import MagicMock

    def make_event(id, lat, lng, place_id, start_time, end_time, sort_order):
        e = MagicMock()
        e.id = id
        e.lat = lat
        e.lng = lng
        e.place_id = place_id
        e.start_time = start_time
        e.end_time = end_time
        e.sort_order = sort_order
        return e

    base = datetime(2026, 5, 9, 9, 0)
    events_with = [
        make_event(1, 13.75, 100.50, None, base, base.replace(hour=10), 1),
        make_event(2, 13.76, 100.51, None, base.replace(hour=11), base.replace(hour=12), 2),
        make_event(3, None, None, None, base.replace(hour=13), base.replace(hour=14), 3),
    ]
    events_without = [
        make_event(1, 13.75, 100.50, None, base, base.replace(hour=10), 1),
        make_event(2, 13.76, 100.51, None, base.replace(hour=11), base.replace(hour=12), 2),
    ]
    assert compute_waypoint_fingerprint(events_with) == compute_waypoint_fingerprint(events_without)
