"""§5 Trip Days — day CRUD, event bin/delete on day-delete, vote transfer on day-delete."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip


async def _create_event(client, headers, trip_id, title="Ev", **kw):
    body = {"trip_id": trip_id, "title": title, **kw}
    r = await client.post("/api/events", json=body, headers=headers)
    assert r.status_code == 201
    return r.json()


async def test_create_trip_day(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    resp = await client.post(f"/api/trips/{trip['id']}/days", json={"date": "2026-06-02"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["date"] == "2026-06-02"


async def test_list_trip_days_ordered(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    await client.post(f"/api/trips/{trip['id']}/days", json={"date": "2026-06-03"}, headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/days", json={"date": "2026-06-02"}, headers=auth_headers)
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    dates = [d["date"] for d in days]
    assert dates == sorted(dates)


async def test_delete_trip_day_moves_events_to_bin(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    day_date = days[0]["date"]
    ev = await _create_event(client, auth_headers, trip["id"], day_date=day_date)
    await client.delete(f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=bin", headers=auth_headers)
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    assert len(ideas) >= 1


async def test_delete_day_action_delete_permanent_no_idea_items(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    day_date = days[0]["date"]
    await _create_event(client, auth_headers, trip["id"], day_date=day_date)
    await client.delete(f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=delete", headers=auth_headers)
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    assert ideas == []


async def test_delete_trip_day_transfers_votes(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    day_date = days[0]["date"]
    ev = await _create_event(client, auth_headers, trip["id"], day_date=day_date)
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.delete(f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=bin", headers=auth_headers)
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    tally = (await client.get(f"/api/ideas/{ideas[0]['id']}/votes", headers=auth_headers)).json()
    assert tally["up"] == 1


async def test_delete_trip_day_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    resp = await client.delete(f"/api/trips/{trip['id']}/days/{days[0]['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


async def test_day_delete_action_delete_creates_no_idea_votes(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    day_date = days[0]["date"]
    ev = await _create_event(client, auth_headers, trip["id"], day_date=day_date)
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.delete(f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=delete", headers=auth_headers)
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    assert ideas == []
