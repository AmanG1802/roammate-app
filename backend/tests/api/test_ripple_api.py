"""Tests for /api/events/ripple/{trip_id}."""
from datetime import datetime
from httpx import AsyncClient
from tests.conftest import create_trip


async def _create_event(client, headers, trip_id, **extra):
    payload = {"trip_id": trip_id, "title": "E"}
    payload.update(extra)
    resp = await client.post("/api/events/", json=payload, headers=headers)
    return resp.json()


async def test_ripple_shifts_future_events(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await _create_event(
        client, auth_headers, trip["id"],
        title="A", start_time="2026-06-01T10:00:00", end_time="2026-06-01T11:00:00",
    )
    resp = await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 30, "start_from_time": "2026-06-01T09:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    shifted = resp.json()
    assert shifted[0]["start_time"].startswith("2026-06-01T10:30:00")
    assert shifted[0]["end_time"].startswith("2026-06-01T11:30:00")


async def test_ripple_non_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 10},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_ripple_missing_delta(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/events/ripple/{trip['id']}", json={}, headers=auth_headers
    )
    assert resp.status_code == 422


async def test_ripple_strips_tz_on_start_from_time(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    await _create_event(
        client, auth_headers, trip["id"],
        start_time="2026-06-01T10:00:00", end_time="2026-06-01T11:00:00",
    )
    # tz-aware input should be handled
    resp = await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 15, "start_from_time": "2026-06-01T09:00:00Z"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


async def test_ripple_isolated_to_trip(
    client: AsyncClient, auth_headers
):
    trip_a = await create_trip(client, auth_headers, name="A")
    trip_b = await create_trip(client, auth_headers, name="B")
    await _create_event(
        client, auth_headers, trip_a["id"],
        title="a-evt", start_time="2026-06-01T10:00:00", end_time="2026-06-01T11:00:00",
    )
    await _create_event(
        client, auth_headers, trip_b["id"],
        title="b-evt", start_time="2026-06-01T10:00:00", end_time="2026-06-01T11:00:00",
    )
    await client.post(
        f"/api/events/ripple/{trip_a['id']}",
        json={"delta_minutes": 60, "start_from_time": "2026-06-01T09:00:00"},
        headers=auth_headers,
    )
    b_events = (
        await client.get(
            f"/api/events/?trip_id={trip_b['id']}", headers=auth_headers
        )
    ).json()
    assert b_events[0]["start_time"].startswith("2026-06-01T10:00:00")
