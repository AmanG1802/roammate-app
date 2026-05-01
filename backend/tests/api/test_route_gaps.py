"""§4F — Route endpoint gap tests.

Additional coverage for auth, edge cases, and response shapes.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


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
    place_id: str | None = None,
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
    if place_id:
        payload["place_id"] = place_id
    resp = await client.post("/api/events/", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_route_non_member_403(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_route_unauthenticated_401(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
    )
    assert resp.status_code == 401


async def test_route_with_one_event_returns_need_two_points(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())
    await _create_event(
        client, auth_headers, trip["id"],
        title="Only Event", day=today,
        start=base.replace(hour=9), end=base.replace(hour=10),
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["reason"] == "need_two_points"


async def test_route_returns_per_leg_distance_and_duration(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())
    await _create_event(
        client, auth_headers, trip["id"],
        title="A", day=today,
        start=base.replace(hour=9), end=base.replace(hour=10),
        lat=13.74, lng=100.49, sort_order=1,
    )
    await _create_event(
        client, auth_headers, trip["id"],
        title="B", day=today,
        start=base.replace(hour=11), end=base.replace(hour=12),
        lat=13.75, lng=100.50, sort_order=2,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reason"] is None
    assert len(body["legs"]) == 1
    leg = body["legs"][0]
    assert "duration_s" in leg
    assert "distance_m" in leg
    assert leg["duration_s"] > 0
    assert leg["distance_m"] > 0


async def test_route_two_back_to_back_events_zero_gap_allowed(
    client: AsyncClient, auth_headers
):
    """Events with end_time == next start_time are NOT a conflict."""
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())
    await _create_event(
        client, auth_headers, trip["id"],
        title="A", day=today,
        start=base.replace(hour=9), end=base.replace(hour=10),
        sort_order=1,
    )
    await _create_event(
        client, auth_headers, trip["id"],
        title="B", day=today,
        start=base.replace(hour=10), end=base.replace(hour=11),
        sort_order=2,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    # end_time == start_time means no overlap → should succeed
    assert resp.status_code == 200
    assert resp.json()["reason"] is None


async def test_route_overlap_validation_error_shape(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())
    await _create_event(
        client, auth_headers, trip["id"],
        title="A", day=today,
        start=base.replace(hour=9), end=base.replace(hour=11),
        sort_order=1,
    )
    await _create_event(
        client, auth_headers, trip["id"],
        title="B", day=today,
        start=base.replace(hour=10), end=base.replace(hour=12),
        sort_order=2,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "detail" in detail
    assert "offending_event_ids" in detail
    assert detail["detail"] == "time_conflicts"
    assert isinstance(detail["offending_event_ids"], list)


async def test_route_event_without_lat_lng_is_unroutable(
    client: AsyncClient, auth_headers
):
    """Event without coordinates is skipped (unroutable)."""
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())

    # Event with coords
    await _create_event(
        client, auth_headers, trip["id"],
        title="A", day=today,
        start=base.replace(hour=9), end=base.replace(hour=10),
        lat=13.74, lng=100.49, sort_order=1,
    )
    await _create_event(
        client, auth_headers, trip["id"],
        title="B", day=today,
        start=base.replace(hour=11), end=base.replace(hour=12),
        lat=13.75, lng=100.50, sort_order=2,
    )
    # Event without coords
    resp = await client.post(
        "/api/events/",
        json={
            "trip_id": trip["id"],
            "title": "No Location",
            "lat": None,
            "lng": None,
            "day_date": today.isoformat(),
            "start_time": base.replace(hour=14).isoformat(),
            "end_time": base.replace(hour=15).isoformat(),
            "sort_order": 3,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    route_resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert route_resp.status_code == 200
    body = route_resp.json()
    assert len(body["unroutable"]) == 1
    assert body["unroutable"][0]["reason"] == "no_location"
