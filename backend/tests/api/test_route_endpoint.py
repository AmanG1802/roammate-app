"""Tests for the POST /api/trips/{id}/route endpoint."""
from datetime import date, datetime, timedelta

from httpx import AsyncClient

from tests.conftest import create_trip


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


async def test_route_returns_polyline_for_two_timed_events(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())
    await _create_event(
        client, auth_headers, trip["id"],
        title="Wat Pho", day=today,
        start=base.replace(hour=9), end=base.replace(hour=10),
        lat=13.7465, lng=100.4927, sort_order=1,
    )
    await _create_event(
        client, auth_headers, trip["id"],
        title="Grand Palace", day=today,
        start=base.replace(hour=11), end=base.replace(hour=12, minute=30),
        lat=13.7500, lng=100.4914, sort_order=2,
    )

    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reason"] is None
    assert body["encoded_polyline"]
    assert len(body["legs"]) == 1
    assert len(body["ordered_event_ids"]) == 2
    assert body["unroutable"] == []
    assert body["total_duration_s"] > 0


async def test_route_orders_by_start_time(client: AsyncClient, auth_headers):
    """Route is ordered by ``start_time`` ascending.

    We can't directly contrast ``start_time`` vs ``sort_order`` without
    tripping the conflict gate (the conflict gate walks sort_order — any
    disagreement between sort_order and start_time on overlapping events
    *is* a conflict, by the same rule the UI uses to paint the timeline
    red).  So this test verifies the start_time contract using a
    non-conflicting setup.
    """
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())
    earlier = await _create_event(
        client, auth_headers, trip["id"],
        title="Earlier Stop", day=today,
        start=base.replace(hour=9), end=base.replace(hour=10),
        sort_order=1,
    )
    later = await _create_event(
        client, auth_headers, trip["id"],
        title="Later Stop", day=today,
        start=base.replace(hour=14), end=base.replace(hour=15),
        sort_order=2,
    )

    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ordered_event_ids"] == [str(earlier["id"]), str(later["id"])]


async def test_route_422_when_any_event_missing_start_time(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())
    await _create_event(
        client, auth_headers, trip["id"],
        title="Has time", day=today,
        start=base.replace(hour=9), end=base.replace(hour=10),
    )
    no_time = await _create_event(
        client, auth_headers, trip["id"],
        title="Missing time", day=today,
        start=None, end=None,
    )

    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["detail"] == "missing_start_times"
    assert str(no_time["id"]) in detail["offending_event_ids"]


async def test_route_422_when_events_overlap(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())
    a = await _create_event(
        client, auth_headers, trip["id"],
        title="A", day=today,
        start=base.replace(hour=9), end=base.replace(hour=11),
        sort_order=1,
    )
    # Starts before A ends → conflict.
    b = await _create_event(
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
    assert detail["detail"] == "time_conflicts"
    assert str(a["id"]) in detail["offending_event_ids"]
    assert str(b["id"]) in detail["offending_event_ids"]


async def test_route_returns_need_two_points_for_empty_day(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    tomorrow = date.today() + timedelta(days=1)
    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": tomorrow.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["reason"] == "need_two_points"
