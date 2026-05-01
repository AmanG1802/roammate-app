"""§8D — Map × Route × Trip days × Events interaction tests.

Verifies route recomputation after event changes.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
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


async def test_route_for_day_with_only_one_event_returns_need_two_points(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())
    await _create_event(
        client, auth_headers, trip["id"],
        title="Solo Event", day=today,
        start=base.replace(hour=9), end=base.replace(hour=10),
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["reason"] == "need_two_points"


async def test_route_recomputes_with_different_events(
    client: AsyncClient, auth_headers
):
    """Route response changes when the underlying events change."""
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())

    e1 = await _create_event(
        client, auth_headers, trip["id"],
        title="A", day=today,
        start=base.replace(hour=9), end=base.replace(hour=10),
        lat=13.74, lng=100.49, sort_order=1,
    )
    e2 = await _create_event(
        client, auth_headers, trip["id"],
        title="B", day=today,
        start=base.replace(hour=11), end=base.replace(hour=12),
        lat=13.76, lng=100.51, sort_order=2,
    )

    resp1 = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp1.status_code == 200
    assert resp1.json()["reason"] is None

    # Add a third event
    await _create_event(
        client, auth_headers, trip["id"],
        title="C", day=today,
        start=base.replace(hour=14), end=base.replace(hour=15),
        lat=13.78, lng=100.53, sort_order=3,
    )

    resp2 = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    # Now 3 events → 2 legs
    assert len(resp2.json()["legs"]) == 2
    assert len(resp2.json()["ordered_event_ids"]) == 3


async def test_deleting_event_reduces_route_points(
    client: AsyncClient, auth_headers
):
    """After deleting an event, the route reflects fewer waypoints."""
    trip = await create_trip(client, auth_headers)
    today = date.today()
    base = datetime.combine(today, datetime.min.time())

    e1 = await _create_event(
        client, auth_headers, trip["id"],
        title="A", day=today,
        start=base.replace(hour=9), end=base.replace(hour=10),
        lat=13.74, lng=100.49, sort_order=1,
    )
    e2 = await _create_event(
        client, auth_headers, trip["id"],
        title="B", day=today,
        start=base.replace(hour=11), end=base.replace(hour=12),
        lat=13.75, lng=100.50, sort_order=2,
    )
    e3 = await _create_event(
        client, auth_headers, trip["id"],
        title="C", day=today,
        start=base.replace(hour=14), end=base.replace(hour=15),
        lat=13.76, lng=100.51, sort_order=3,
    )

    # Delete middle event
    del_resp = await client.delete(
        f"/api/events/{e2['id']}",
        headers=auth_headers,
    )
    assert del_resp.status_code in (200, 204)

    resp = await client.post(
        f"/api/trips/{trip['id']}/route",
        json={"day_date": today.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["ordered_event_ids"]) == 2
    assert len(resp.json()["legs"]) == 1
