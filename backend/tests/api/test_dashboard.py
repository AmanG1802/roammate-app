"""HTTP integration tests for `/api/dashboard/today`.

Covers state classification (pre/in/post), caps + ordering, default-index
selection, event enrichment on the active page, and per-user isolation.
"""
from datetime import datetime, timedelta, date
import pytest
from httpx import AsyncClient


# ── helpers ──────────────────────────────────────────────────────────────────

async def make_trip(client: AsyncClient, headers, name: str,
                    start: datetime | None, end: datetime | None = None):
    body: dict = {"name": name}
    if start is not None:
        body["start_date"] = start.isoformat()
    r = await client.post("/api/trips/", json=body, headers=headers)
    assert r.status_code == 200, r.text
    trip = r.json()
    # Trip.end_date gets auto-synced to match TripDay count on create, so we
    # re-assert the caller's intended end_date via PATCH afterwards.
    if end is not None:
        r2 = await client.patch(
            f"/api/trips/{trip['id']}",
            json={"end_date": end.isoformat()},
            headers=headers,
        )
        assert r2.status_code == 200, r2.text
        trip = r2.json()
    return trip


def _default_page(resp_json: dict) -> dict | None:
    pages = resp_json.get("pages", [])
    if not pages:
        return None
    return pages[resp_json.get("default_index", 0)]


def _dt(days_from_today: int) -> datetime:
    return datetime.combine(date.today() + timedelta(days=days_from_today), datetime.min.time())


# ── auth + empty ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_today_requires_auth(client):
    r = await client.get("/api/dashboard/today")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_today_empty_when_no_trips(client, auth_headers):
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["pages"] == []
    assert body["default_index"] == 0


@pytest.mark.asyncio
async def test_today_response_schema_keys_present(client, auth_headers):
    r = await client.get("/api/dashboard/today", headers=auth_headers)
    body = r.json()
    assert "pages" in body and "default_index" in body


# ── state classification ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_today_pre_trip_with_future_start(client, auth_headers):
    await make_trip(client, auth_headers, "Future", _dt(10))
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["state"] == "pre_trip"
    assert page["days_until_start"] == 10


@pytest.mark.asyncio
async def test_today_in_trip_when_today_within_range(client, auth_headers):
    await make_trip(client, auth_headers, "Active", _dt(-1), _dt(2))
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["state"] == "in_trip"
    assert page["day_number"] == 2
    assert page["total_days"] == 4


@pytest.mark.asyncio
async def test_today_post_trip(client, auth_headers):
    await make_trip(client, auth_headers, "Past", _dt(-10), _dt(-3))
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["state"] == "post_trip"
    assert page["days_since_end"] == 3


@pytest.mark.asyncio
async def test_today_trip_with_only_start_date_treats_end_as_start(client, auth_headers):
    """end_date=None → fallback to start_date (same-day trip is 'active' when today matches)."""
    await make_trip(client, auth_headers, "Same-day", _dt(0), None)
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["state"] == "in_trip"


@pytest.mark.asyncio
async def test_today_trip_with_no_start_date_skipped(client, auth_headers):
    """start_date is None → the trip is never classified as any state."""
    await make_trip(client, auth_headers, "Orphan", None)
    body = (await client.get("/api/dashboard/today", headers=auth_headers)).json()
    assert body["pages"] == []


@pytest.mark.asyncio
async def test_today_trip_ending_today_is_active(client, auth_headers):
    await make_trip(client, auth_headers, "Ends today", _dt(-3), _dt(0))
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["state"] == "in_trip"


@pytest.mark.asyncio
async def test_today_trip_starting_today_is_active(client, auth_headers):
    await make_trip(client, auth_headers, "Starts today", _dt(0), _dt(2))
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["state"] == "in_trip"


@pytest.mark.asyncio
async def test_today_trip_ended_yesterday_is_past(client, auth_headers):
    await make_trip(client, auth_headers, "Ended yesterday", _dt(-3), _dt(-1))
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["state"] == "post_trip"
    assert page["days_since_end"] == 1


# ── active-page event enrichment ─────────────────────────────────────────────

async def _post_event(client, headers, trip_id, **extra):
    body = {"trip_id": trip_id, "title": "Thing"}
    body.update(extra)
    r = await client.post("/api/events/", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_today_events_filtered_to_today_only(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(-1), _dt(2))
    await _post_event(client, auth_headers, trip["id"], title="Today", day_date=date.today().isoformat())
    await _post_event(client, auth_headers, trip["id"], title="Tomorrow",
                      day_date=(date.today() + timedelta(days=1)).isoformat())

    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    titles = [e["title"] for e in page["today_events"]]
    assert titles == ["Today"]


@pytest.mark.asyncio
async def test_today_events_ordered_by_start_time_nulls_last(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    today_iso = date.today().isoformat()
    today_dt = datetime.combine(date.today(), datetime.min.time())
    await _post_event(client, auth_headers, trip["id"], title="No time", day_date=today_iso)
    await _post_event(client, auth_headers, trip["id"], title="Noon",
                      day_date=today_iso,
                      start_time=(today_dt + timedelta(hours=12)).isoformat())
    await _post_event(client, auth_headers, trip["id"], title="Morning",
                      day_date=today_iso,
                      start_time=(today_dt + timedelta(hours=9)).isoformat())

    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    titles = [e["title"] for e in page["today_events"]]
    assert titles == ["Morning", "Noon", "No time"]


@pytest.mark.asyncio
async def test_today_next_flag_set_on_first_future_event_only(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    today_iso = date.today().isoformat()
    far_future = datetime.now() + timedelta(hours=6)
    farther = datetime.now() + timedelta(hours=9)
    await _post_event(client, auth_headers, trip["id"], title="Next",
                      day_date=today_iso, start_time=far_future.isoformat())
    await _post_event(client, auth_headers, trip["id"], title="Later",
                      day_date=today_iso, start_time=farther.isoformat())

    # Use client_now to fix "now" before Next's start_time
    client_now = (far_future - timedelta(hours=1)).isoformat()
    page = _default_page(
        (await client.get(f"/api/dashboard/today?client_now={client_now}", headers=auth_headers)).json()
    )
    flags = [(e["title"], e["is_next"]) for e in page["today_events"]]
    assert flags == [("Next", True), ("Later", False)]


@pytest.mark.asyncio
async def test_today_ongoing_flag_set_when_now_between_start_end(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    today_iso = date.today().isoformat()
    start = datetime.now() - timedelta(hours=1)
    end = datetime.now() + timedelta(hours=1)
    await _post_event(client, auth_headers, trip["id"], title="Ongoing",
                      day_date=today_iso,
                      start_time=start.isoformat(), end_time=end.isoformat())

    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["today_events"][0]["is_ongoing"] is True


@pytest.mark.asyncio
async def test_today_day_number_from_trip_days(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(-1), _dt(3))
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    # TripDay only auto-created for day 1; day_number should fall back to date delta (2)
    assert page["day_number"] == 2


@pytest.mark.asyncio
async def test_today_client_now_iso_overrides_server_time(client, auth_headers):
    """Forcing client_now far in the past turns an 'active' trip into 'pre_trip'."""
    await make_trip(client, auth_headers, "Upcoming to me", _dt(2), _dt(5))
    long_past = (datetime.now() - timedelta(days=365)).isoformat()
    page = _default_page(
        (await client.get(f"/api/dashboard/today?client_now={long_past}", headers=auth_headers)).json()
    )
    # From last year's POV, the trip is far in the future
    assert page["state"] == "pre_trip"


@pytest.mark.asyncio
async def test_today_client_now_with_Z_suffix_accepted(client, auth_headers):
    await make_trip(client, auth_headers, "Active", _dt(-1), _dt(2))
    now_z = datetime.now().replace(microsecond=0).isoformat() + "Z"
    r = await client.get(f"/api/dashboard/today?client_now={now_z}", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_today_client_now_invalid_falls_back(client, auth_headers):
    await make_trip(client, auth_headers, "Active", _dt(-1), _dt(2))
    r = await client.get("/api/dashboard/today?client_now=not-a-date", headers=auth_headers)
    assert r.status_code == 200
    # Should still classify something
    page = _default_page(r.json())
    assert page["state"] == "in_trip"


# ── multi-trip precedence + caps ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_today_prefers_active_over_upcoming(client, auth_headers):
    await make_trip(client, auth_headers, "Upcoming", _dt(7))
    await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["trip"]["name"] == "Active"


@pytest.mark.asyncio
async def test_today_page_order_is_past_active_upcoming(client, auth_headers):
    await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    await make_trip(client, auth_headers, "Upcoming", _dt(7))
    await make_trip(client, auth_headers, "Past", _dt(-10), _dt(-3))
    body = (await client.get("/api/dashboard/today", headers=auth_headers)).json()
    assert [p["state"] for p in body["pages"]] == ["post_trip", "in_trip", "pre_trip"]


@pytest.mark.asyncio
async def test_today_caps_past_at_2_upcoming_at_3(client, auth_headers):
    for i in range(4):
        await make_trip(client, auth_headers, f"Past-{i}", _dt(-20 - i * 5), _dt(-16 - i * 5))
    for i in range(5):
        await make_trip(client, auth_headers, f"Up-{i}", _dt(5 + i * 5))
    body = (await client.get("/api/dashboard/today", headers=auth_headers)).json()
    past = [p for p in body["pages"] if p["state"] == "post_trip"]
    upcoming = [p for p in body["pages"] if p["state"] == "pre_trip"]
    assert len(past) == 2
    assert len(upcoming) == 3


@pytest.mark.asyncio
async def test_today_default_index_closer_past(client, auth_headers):
    await make_trip(client, auth_headers, "Past", _dt(-5), _dt(-1))
    await make_trip(client, auth_headers, "Upcoming", _dt(10))
    body = (await client.get("/api/dashboard/today", headers=auth_headers)).json()
    assert body["pages"][body["default_index"]]["state"] == "post_trip"


@pytest.mark.asyncio
async def test_today_default_index_closer_upcoming(client, auth_headers):
    await make_trip(client, auth_headers, "Past", _dt(-30), _dt(-20))
    await make_trip(client, auth_headers, "Upcoming", _dt(2))
    body = (await client.get("/api/dashboard/today", headers=auth_headers)).json()
    assert body["pages"][body["default_index"]]["state"] == "pre_trip"


@pytest.mark.asyncio
async def test_today_default_index_points_to_active_when_present(client, auth_headers):
    await make_trip(client, auth_headers, "Past", _dt(-30), _dt(-20))
    await make_trip(client, auth_headers, "Active", _dt(0), _dt(2))
    await make_trip(client, auth_headers, "Upcoming", _dt(10))
    body = (await client.get("/api/dashboard/today", headers=auth_headers)).json()
    assert body["pages"][body["default_index"]]["state"] == "in_trip"


@pytest.mark.asyncio
async def test_today_default_index_zero_when_only_upcoming(client, auth_headers):
    await make_trip(client, auth_headers, "U1", _dt(5))
    await make_trip(client, auth_headers, "U2", _dt(10))
    body = (await client.get("/api/dashboard/today", headers=auth_headers)).json()
    assert body["default_index"] == 0


# ── isolation ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_today_isolated_per_user(client, auth_headers, second_auth_headers):
    await make_trip(client, auth_headers, "Alice's", _dt(5))
    r = await client.get("/api/dashboard/today", headers=second_auth_headers)
    assert r.json()["pages"] == []


@pytest.mark.asyncio
async def test_today_invited_but_not_accepted_excluded(
    client, auth_headers, second_auth_headers
):
    trip = await make_trip(client, auth_headers, "Alice's", _dt(5))
    r = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    bob = (await client.get("/api/dashboard/today", headers=second_auth_headers)).json()
    assert bob["pages"] == []


@pytest.mark.asyncio
async def test_today_only_one_active_trip_shown(client, auth_headers):
    """When two trips are both active, only one is surfaced (soonest start)."""
    await make_trip(client, auth_headers, "A", _dt(-2), _dt(2))
    await make_trip(client, auth_headers, "B", _dt(-1), _dt(3))
    body = (await client.get("/api/dashboard/today", headers=auth_headers)).json()
    actives = [p for p in body["pages"] if p["state"] == "in_trip"]
    assert len(actives) == 1
    assert actives[0]["trip"]["name"] == "A"


# ── day number / total_days from _sync_trip_end_date ──────────────────────────

@pytest.mark.asyncio
async def test_today_total_days_updates_after_adding_day(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": tomorrow}, headers=auth_headers
    )
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["total_days"] >= 2


@pytest.mark.asyncio
async def test_today_total_days_updates_after_deleting_day(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(0), _dt(3))
    d1 = (date.today() + timedelta(days=1)).isoformat()
    d2 = (date.today() + timedelta(days=2)).isoformat()
    await client.post(f"/api/trips/{trip['id']}/days", json={"date": d1}, headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/days", json={"date": d2}, headers=auth_headers)
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    last_day = sorted(days, key=lambda d: d["day_number"])[-1]
    await client.delete(
        f"/api/trips/{trip['id']}/days/{last_day['id']}?items_action=delete",
        headers=auth_headers,
    )
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["total_days"] >= 2


@pytest.mark.asyncio
async def test_today_editing_start_date_earlier_keeps_trip_active(client, auth_headers):
    trip = await make_trip(client, auth_headers, "TodayStart", _dt(0), _dt(2))
    # Add a second day so that after changing start_date to yesterday,
    # end_date = yesterday + 1 = today, keeping the trip active.
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": tomorrow}, headers=auth_headers
    )
    await client.patch(
        f"/api/trips/{trip['id']}",
        json={"start_date": _dt(-1).isoformat()},
        headers=auth_headers,
    )
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["state"] == "in_trip"
    assert page["day_number"] == 2


# ── ongoing + up-next coexistence ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_today_ongoing_and_next_coexist(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    today_iso = date.today().isoformat()
    now = datetime.now()
    ongoing_start = now - timedelta(minutes=30)
    ongoing_end = now + timedelta(minutes=30)
    future_start = now + timedelta(hours=2)
    future_end = now + timedelta(hours=3)
    await _post_event(client, auth_headers, trip["id"], title="Now",
                      day_date=today_iso,
                      start_time=ongoing_start.isoformat(), end_time=ongoing_end.isoformat())
    await _post_event(client, auth_headers, trip["id"], title="Later",
                      day_date=today_iso,
                      start_time=future_start.isoformat(), end_time=future_end.isoformat())
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    flags = {e["title"]: (e["is_ongoing"], e["is_next"]) for e in page["today_events"]}
    assert flags["Now"] == (True, False)
    assert flags["Later"] == (False, True)


@pytest.mark.asyncio
async def test_today_past_event_neither_ongoing_nor_next(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    today_iso = date.today().isoformat()
    past_start = datetime.now() - timedelta(hours=4)
    past_end = datetime.now() - timedelta(hours=3)
    client_now = datetime.now().isoformat()
    await _post_event(client, auth_headers, trip["id"], title="Done",
                      day_date=today_iso,
                      start_time=past_start.isoformat(), end_time=past_end.isoformat())
    page = _default_page(
        (await client.get(f"/api/dashboard/today?client_now={client_now}", headers=auth_headers)).json()
    )
    assert page["today_events"][0]["is_ongoing"] is False
    assert page["today_events"][0]["is_next"] is False


@pytest.mark.asyncio
async def test_today_gap_between_events_only_up_next(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    today_iso = date.today().isoformat()
    today_dt = datetime.combine(date.today(), datetime.min.time())
    await _post_event(client, auth_headers, trip["id"], title="Early",
                      day_date=today_iso,
                      start_time=(today_dt + timedelta(hours=2)).isoformat(),
                      end_time=(today_dt + timedelta(hours=2, minutes=15)).isoformat())
    await _post_event(client, auth_headers, trip["id"], title="Afternoon",
                      day_date=today_iso,
                      start_time=(today_dt + timedelta(hours=15)).isoformat(),
                      end_time=(today_dt + timedelta(hours=15, minutes=15)).isoformat())

    client_now = (today_dt + timedelta(hours=10)).isoformat()
    page = _default_page(
        (await client.get(f"/api/dashboard/today?client_now={client_now}", headers=auth_headers)).json()
    )
    ongoing = [e for e in page["today_events"] if e["is_ongoing"]]
    assert ongoing == []
    nexts = [e for e in page["today_events"] if e["is_next"]]
    assert len(nexts) == 1 and nexts[0]["title"] == "Afternoon"


@pytest.mark.asyncio
async def test_today_all_past_no_flags(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    today_iso = date.today().isoformat()
    today_dt = datetime.combine(date.today(), datetime.min.time())
    await _post_event(client, auth_headers, trip["id"], title="E1",
                      day_date=today_iso,
                      start_time=(today_dt + timedelta(hours=1)).isoformat(),
                      end_time=(today_dt + timedelta(hours=2)).isoformat())
    await _post_event(client, auth_headers, trip["id"], title="E2",
                      day_date=today_iso,
                      start_time=(today_dt + timedelta(hours=3)).isoformat(),
                      end_time=(today_dt + timedelta(hours=4)).isoformat())

    client_now = (today_dt + timedelta(hours=23)).isoformat()
    page = _default_page(
        (await client.get(f"/api/dashboard/today?client_now={client_now}", headers=auth_headers)).json()
    )
    for e in page["today_events"]:
        assert e["is_ongoing"] is False and e["is_next"] is False


@pytest.mark.asyncio
async def test_today_event_without_end_time_not_ongoing(client, auth_headers):
    trip = await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    today_iso = date.today().isoformat()
    start = datetime.now() - timedelta(hours=1)
    await _post_event(client, auth_headers, trip["id"], title="NoEnd",
                      day_date=today_iso, start_time=start.isoformat())
    page = _default_page((await client.get("/api/dashboard/today", headers=auth_headers)).json())
    assert page["today_events"][0]["is_ongoing"] is False


@pytest.mark.asyncio
async def test_today_client_now_6am_skips_2am_picks_2pm(client, auth_headers):
    """Regression: 2AM event must not show as up-next when client_now is 6AM."""
    trip = await make_trip(client, auth_headers, "Active", _dt(0), _dt(1))
    today_iso = date.today().isoformat()
    today_dt = datetime.combine(date.today(), datetime.min.time())
    await _post_event(client, auth_headers, trip["id"], title="Tea",
                      day_date=today_iso,
                      start_time=(today_dt + timedelta(hours=2)).isoformat(),
                      end_time=(today_dt + timedelta(hours=2, minutes=15)).isoformat())
    await _post_event(client, auth_headers, trip["id"], title="Coffee",
                      day_date=today_iso,
                      start_time=(today_dt + timedelta(hours=14)).isoformat(),
                      end_time=(today_dt + timedelta(hours=14, minutes=15)).isoformat())

    client_now = (today_dt + timedelta(hours=6)).isoformat()
    page = _default_page(
        (await client.get(f"/api/dashboard/today?client_now={client_now}", headers=auth_headers)).json()
    )
    nexts = [e for e in page["today_events"] if e["is_next"]]
    assert len(nexts) == 1 and nexts[0]["title"] == "Coffee"
