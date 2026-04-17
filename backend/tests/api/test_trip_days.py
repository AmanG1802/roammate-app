"""Tests for /api/trips/{id}/days/*."""
from httpx import AsyncClient
from tests.conftest import create_trip, invite_and_accept


async def test_get_days_ordered(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": "2026-06-03"}, headers=auth_headers
    )
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": "2026-06-02"}, headers=auth_headers
    )
    days = (
        await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)
    ).json()
    dates = [d["date"] for d in days]
    assert dates == sorted(dates)


async def test_get_days_non_member_forbidden(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(
        f"/api/trips/{trip['id']}/days", headers=second_auth_headers
    )
    assert resp.status_code == 403


async def test_add_day_increments_number(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    resp = await client.post(
        f"/api/trips/{trip['id']}/days",
        json={"date": "2026-06-02"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["day_number"] == 2


async def test_add_day_by_non_admin_forbidden(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com",
        role="view_only",
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/days",
        json={"date": "2026-06-01"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_add_day_duplicate_date(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    resp = await client.post(
        f"/api/trips/{trip['id']}/days",
        json={"date": "2026-06-01"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


async def test_first_day_when_no_start_date(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/days",
        json={"date": "2026-06-01"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["day_number"] == 1


async def test_delete_day_items_action_bin(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    # create event on day 1
    await client.post(
        "/api/events/",
        json={
            "trip_id": trip["id"],
            "title": "Colosseum",
            "day_date": "2026-06-01",
            "start_time": "2026-06-01T14:00:00",
            "end_time": "2026-06-01T15:00:00",
        },
        headers=auth_headers,
    )
    days = (
        await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)
    ).json()
    day_id = days[0]["id"]
    resp = await client.delete(
        f"/api/trips/{trip['id']}/days/{day_id}?items_action=bin",
        headers=auth_headers,
    )
    assert resp.status_code == 204
    ideas = (
        await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)
    ).json()
    assert len(ideas) == 1
    assert ideas[0]["title"] == "Colosseum"
    assert ideas[0]["time_hint"] == "2pm"


async def test_delete_day_items_action_delete(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    await client.post(
        "/api/events/",
        json={"trip_id": trip["id"], "title": "X", "day_date": "2026-06-01"},
        headers=auth_headers,
    )
    days = (
        await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)
    ).json()
    resp = await client.delete(
        f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=delete",
        headers=auth_headers,
    )
    assert resp.status_code == 204
    ideas = (
        await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)
    ).json()
    assert ideas == []
    events = (
        await client.get(f"/api/events/?trip_id={trip['id']}", headers=auth_headers)
    ).json()
    assert events == []


async def test_delete_day_left_shifts_subsequent(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": "2026-06-02"}, headers=auth_headers
    )
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": "2026-06-03"}, headers=auth_headers
    )
    days = (
        await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)
    ).json()
    # delete day 2 (middle)
    middle = [d for d in days if d["day_number"] == 2][0]
    resp = await client.delete(
        f"/api/trips/{trip['id']}/days/{middle['id']}?items_action=delete",
        headers=auth_headers,
    )
    assert resp.status_code == 204
    remaining = (
        await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)
    ).json()
    assert [d["day_number"] for d in sorted(remaining, key=lambda x: x["day_number"])] == [1, 2]
    # day originally 3 should now be date 2026-06-02
    day2 = [d for d in remaining if d["day_number"] == 2][0]
    assert day2["date"] == "2026-06-02"


async def test_delete_day_left_shifts_event_dates(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": "2026-06-02"}, headers=auth_headers
    )
    await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": "2026-06-03"}, headers=auth_headers
    )
    # event on day 3
    await client.post(
        "/api/events/",
        json={"trip_id": trip["id"], "title": "Gallery", "day_date": "2026-06-03"},
        headers=auth_headers,
    )
    days = (
        await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)
    ).json()
    day1 = [d for d in days if d["day_number"] == 1][0]
    await client.delete(
        f"/api/trips/{trip['id']}/days/{day1['id']}?items_action=delete",
        headers=auth_headers,
    )
    events = (
        await client.get(f"/api/events/?trip_id={trip['id']}", headers=auth_headers)
    ).json()
    assert events[0]["day_date"] == "2026-06-02"


async def test_delete_day_nonexistent(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.delete(
        f"/api/trips/{trip['id']}/days/9999", headers=auth_headers
    )
    assert resp.status_code == 404


async def test_delete_day_by_non_admin(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com",
        role="view_only",
    )
    days = (
        await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)
    ).json()
    resp = await client.delete(
        f"/api/trips/{trip['id']}/days/{days[0]['id']}",
        headers=second_auth_headers,
    )
    assert resp.status_code == 403
