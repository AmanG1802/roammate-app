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


def _default_page(resp_json: dict) -> dict | None:
    pages = resp_json.get("pages", [])
    if not pages:
        return None
    idx = resp_json.get("default_index", 0)
    return pages[idx]


@pytest.mark.asyncio
async def test_today_empty_when_no_trips(client, auth_headers):
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["pages"] == []


@pytest.mark.asyncio
async def test_today_pre_trip_with_future_start(client, auth_headers):
    future = datetime.combine(date.today() + timedelta(days=10), datetime.min.time())
    await make_trip(client, auth_headers, "Future Trip", future)
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    assert r.status_code == 200
    page = _default_page(r.json())
    assert page is not None
    assert page["state"] == "pre_trip"
    assert page["trip"]["name"] == "Future Trip"
    assert page["days_until_start"] == 10


@pytest.mark.asyncio
async def test_today_in_trip_when_today_within_range(client, auth_headers):
    start = datetime.combine(date.today() - timedelta(days=1), datetime.min.time())
    end = datetime.combine(date.today() + timedelta(days=2), datetime.min.time())
    await make_trip(client, auth_headers, "Active Trip", start, end)
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    page = _default_page(r.json())
    assert page is not None
    assert page["state"] == "in_trip"
    assert page["day_number"] == 2
    assert page["total_days"] == 4


@pytest.mark.asyncio
async def test_today_post_trip(client, auth_headers):
    start = datetime.combine(date.today() - timedelta(days=10), datetime.min.time())
    end = datetime.combine(date.today() - timedelta(days=3), datetime.min.time())
    await make_trip(client, auth_headers, "Past Trip", start, end)
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    page = _default_page(r.json())
    assert page is not None
    assert page["state"] == "post_trip"
    assert page["days_since_end"] == 3


@pytest.mark.asyncio
async def test_today_prefers_active_over_upcoming(client, auth_headers):
    active_start = datetime.combine(date.today(), datetime.min.time())
    active_end = datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
    upcoming = datetime.combine(date.today() + timedelta(days=7), datetime.min.time())
    await make_trip(client, auth_headers, "Upcoming", upcoming)
    await make_trip(client, auth_headers, "Active", active_start, active_end)
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    body = r.json()
    page = _default_page(body)
    assert page is not None
    assert page["state"] == "in_trip"
    assert page["trip"]["name"] == "Active"


@pytest.mark.asyncio
async def test_today_page_order_is_past_active_upcoming(client, auth_headers):
    """Pages must be ordered: past → active → upcoming."""
    active_start = datetime.combine(date.today(), datetime.min.time())
    active_end = datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
    upcoming = datetime.combine(date.today() + timedelta(days=7), datetime.min.time())
    past_start = datetime.combine(date.today() - timedelta(days=10), datetime.min.time())
    past_end = datetime.combine(date.today() - timedelta(days=3), datetime.min.time())
    await make_trip(client, auth_headers, "Active", active_start, active_end)
    await make_trip(client, auth_headers, "Upcoming", upcoming)
    await make_trip(client, auth_headers, "Past", past_start, past_end)
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    body = r.json()
    states = [p["state"] for p in body["pages"]]
    assert states == ["post_trip", "in_trip", "pre_trip"]


@pytest.mark.asyncio
async def test_today_caps_past_at_2_upcoming_at_3(client, auth_headers):
    """Max 2 past, max 3 upcoming shown."""
    for i in range(4):
        s = datetime.combine(date.today() - timedelta(days=20 + i * 5), datetime.min.time())
        e = datetime.combine(date.today() - timedelta(days=16 + i * 5), datetime.min.time())
        await make_trip(client, auth_headers, f"Past-{i}", s, e)
    for i in range(5):
        s = datetime.combine(date.today() + timedelta(days=5 + i * 5), datetime.min.time())
        await make_trip(client, auth_headers, f"Upcoming-{i}", s)
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    body = r.json()
    past_pages = [p for p in body["pages"] if p["state"] == "post_trip"]
    upcoming_pages = [p for p in body["pages"] if p["state"] == "pre_trip"]
    assert len(past_pages) <= 2
    assert len(upcoming_pages) <= 3
    assert len(body["pages"]) <= 6


@pytest.mark.asyncio
async def test_today_default_index_closer_past(client, auth_headers):
    """When no active trip, default to past if it's closer than upcoming."""
    past_s = datetime.combine(date.today() - timedelta(days=5), datetime.min.time())
    past_e = datetime.combine(date.today() - timedelta(days=1), datetime.min.time())
    upcoming_s = datetime.combine(date.today() + timedelta(days=10), datetime.min.time())
    await make_trip(client, auth_headers, "Past", past_s, past_e)
    await make_trip(client, auth_headers, "Upcoming", upcoming_s)
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    body = r.json()
    page = _default_page(body)
    assert page["state"] == "post_trip"


@pytest.mark.asyncio
async def test_today_isolated_per_user(client, auth_headers, second_auth_headers):
    future = datetime.combine(date.today() + timedelta(days=5), datetime.min.time())
    await make_trip(client, auth_headers, "Alice's", future)
    r = await client.get("/api/dashboard/today", headers=second_auth_headers)
    assert r.json()["pages"] == []
