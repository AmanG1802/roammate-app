"""Integration tests for the /dashboard/today endpoint."""
from datetime import datetime, timedelta, date
import pytest
from httpx import AsyncClient


async def make_trip(client: AsyncClient, headers, name: str, start: datetime | None, end: datetime | None = None):
    body: dict = {"name": name}
    if start is not None:
        body["start_date"] = start.isoformat()
    if end is not None:
        body["end_date"] = end.isoformat()
    r = await client.post("/api/trips/", json=body, headers=headers)
    assert r.status_code == 200
    return r.json()


@pytest.mark.asyncio
async def test_today_state_none_when_no_trips(client, auth_headers):
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["state"] == "none"


@pytest.mark.asyncio
async def test_today_pre_trip_with_future_start(client, auth_headers):
    future = datetime.combine(date.today() + timedelta(days=10), datetime.min.time())
    await make_trip(client, auth_headers, "Future Trip", future)
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "pre_trip"
    assert body["trip"]["name"] == "Future Trip"
    assert body["days_until_start"] == 10


@pytest.mark.asyncio
async def test_today_in_trip_when_today_within_range(client, auth_headers):
    start = datetime.combine(date.today() - timedelta(days=1), datetime.min.time())
    end = datetime.combine(date.today() + timedelta(days=2), datetime.min.time())
    await make_trip(client, auth_headers, "Active Trip", start, end)
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    body = r.json()
    assert body["state"] == "in_trip"
    assert body["day_number"] == 2
    assert body["total_days"] == 4


@pytest.mark.asyncio
async def test_today_post_trip_within_30d(client, auth_headers):
    start = datetime.combine(date.today() - timedelta(days=10), datetime.min.time())
    end = datetime.combine(date.today() - timedelta(days=3), datetime.min.time())
    await make_trip(client, auth_headers, "Past Trip", start, end)
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    body = r.json()
    assert body["state"] == "post_trip"
    assert body["days_since_end"] == 3


@pytest.mark.asyncio
async def test_today_prefers_active_over_upcoming(client, auth_headers):
    active_start = datetime.combine(date.today(), datetime.min.time())
    active_end = datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
    upcoming = datetime.combine(date.today() + timedelta(days=7), datetime.min.time())
    await make_trip(client, auth_headers, "Upcoming", upcoming)
    await make_trip(client, auth_headers, "Active", active_start, active_end)
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    body = r.json()
    assert body["state"] == "in_trip"
    assert body["trip"]["name"] == "Active"


@pytest.mark.asyncio
async def test_today_isolated_per_user(client, auth_headers, second_auth_headers):
    future = datetime.combine(date.today() + timedelta(days=5), datetime.min.time())
    await make_trip(client, auth_headers, "Alice's", future)
    r = await client.get("/api/dashboard/today", headers=second_auth_headers)
    assert r.json()["state"] == "none"
