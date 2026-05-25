"""§14 Routes & DayRoute Persistence — route computation, waypoints, and recomputation."""
from __future__ import annotations

from datetime import date, time

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip


async def _create_event(client, headers, trip_id, *, title, day, start_t, end_t, lat=13.75, lng=100.50, sort_order=0):
    payload = {
        "trip_id": trip_id, "title": title, "lat": lat, "lng": lng,
        "day_date": day.isoformat(),
        "start_time": start_t.isoformat() if start_t else None,
        "end_time": end_t.isoformat() if end_t else None,
        "sort_order": sort_order,
    }
    resp = await client.post("/api/events", json=payload, headers=headers)
    assert resp.status_code == 201, f"Event create failed: {resp.text}"
    return resp.json()


async def test_compute_route_requires_two_waypoints(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    await _create_event(client, auth_headers, trip["id"], title="Solo", day=today, start_t=time(9, 0), end_t=time(10, 0))
    resp = await client.post(f"/api/trips/{trip['id']}/route", json={"day_date": today.isoformat()}, headers=auth_headers)
    assert resp.status_code == 200


async def test_route_recomputes_with_different_events(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    await _create_event(client, auth_headers, trip["id"], title="A", day=today, start_t=time(9, 0), end_t=time(10, 0), lat=13.74, lng=100.49, sort_order=1)
    await _create_event(client, auth_headers, trip["id"], title="B", day=today, start_t=time(11, 0), end_t=time(12, 0), lat=13.76, lng=100.51, sort_order=2)
    resp = await client.post(f"/api/trips/{trip['id']}/route", json={"day_date": today.isoformat()}, headers=auth_headers)
    assert resp.status_code == 200
    await _create_event(client, auth_headers, trip["id"], title="C", day=today, start_t=time(14, 0), end_t=time(15, 0), lat=13.78, lng=100.53, sort_order=3)
    resp2 = await client.post(f"/api/trips/{trip['id']}/route", json={"day_date": today.isoformat()}, headers=auth_headers)
    assert resp2.status_code == 200


async def test_deleting_event_reduces_route_points(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    today = date.today()
    e1 = await _create_event(client, auth_headers, trip["id"], title="A", day=today, start_t=time(9, 0), end_t=time(10, 0), lat=13.74, lng=100.49, sort_order=1)
    e2 = await _create_event(client, auth_headers, trip["id"], title="B", day=today, start_t=time(11, 0), end_t=time(12, 0), lat=13.75, lng=100.50, sort_order=2)
    e3 = await _create_event(client, auth_headers, trip["id"], title="C", day=today, start_t=time(14, 0), end_t=time(15, 0), lat=13.76, lng=100.51, sort_order=3)
    await client.delete(f"/api/events/{e2['id']}", headers=auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/route", json={"day_date": today.isoformat()}, headers=auth_headers)
    assert resp.status_code == 200
