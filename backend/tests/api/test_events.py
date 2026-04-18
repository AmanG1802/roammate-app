"""Tests for /api/events/ CRUD + move-to-bin."""
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


async def _create_event(client, headers, trip_id, **extra):
    payload = {"trip_id": trip_id, "title": "E"}
    payload.update(extra)
    resp = await client.post("/api/events/", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_event(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(
        client, auth_headers, trip["id"], title="Colosseum", event_type="activity"
    )
    assert event["title"] == "Colosseum"
    assert event["event_type"] == "activity"


async def test_create_event_non_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        "/api/events/",
        json={"trip_id": trip["id"], "title": "X"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_create_event_missing_fields(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/events/", json={"title": "no trip id"}, headers=auth_headers
    )
    assert resp.status_code == 422


async def test_create_event_strips_tz(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(
        client, auth_headers, trip["id"],
        start_time="2026-06-01T14:00:00Z",
        end_time="2026-06-01T15:00:00Z",
    )
    # tz suffix should be gone (stored and returned naive)
    assert "Z" not in event["start_time"]
    assert "+00:00" not in event["start_time"]


async def test_get_events_by_trip(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await _create_event(client, auth_headers, trip["id"], title="A")
    await _create_event(client, auth_headers, trip["id"], title="B")
    resp = await client.get(f"/api/events/?trip_id={trip['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_get_events_non_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(
        f"/api/events/?trip_id={trip['id']}", headers=second_auth_headers
    )
    assert resp.status_code == 403


async def test_get_events_missing_trip_id(client: AsyncClient, auth_headers):
    resp = await client.get("/api/events/", headers=auth_headers)
    assert resp.status_code == 422


async def test_patch_event(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(client, auth_headers, trip["id"], title="Old")
    resp = await client.patch(
        f"/api/events/{event['id']}",
        json={"title": "New", "sort_order": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New"
    assert data["sort_order"] == 5


async def test_patch_event_non_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(client, auth_headers, trip["id"])
    resp = await client.patch(
        f"/api/events/{event['id']}",
        json={"title": "X"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_patch_event_nonexistent(client: AsyncClient, auth_headers):
    resp = await client.patch(
        "/api/events/9999", json={"title": "X"}, headers=auth_headers
    )
    assert resp.status_code == 404


async def test_delete_event(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(client, auth_headers, trip["id"])
    resp = await client.delete(f"/api/events/{event['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_delete_event_nonexistent(client: AsyncClient, auth_headers):
    resp = await client.delete("/api/events/9999", headers=auth_headers)
    assert resp.status_code == 404


async def test_delete_event_non_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(client, auth_headers, trip["id"])
    resp = await client.delete(
        f"/api/events/{event['id']}", headers=second_auth_headers
    )
    assert resp.status_code == 403


# ── Move to bin ───────────────────────────────────────────────────────────────

async def test_move_to_bin(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(
        client, auth_headers, trip["id"],
        title="Dinner", start_time="2026-06-01T19:30:00",
        end_time="2026-06-01T20:30:00",
        place_id="p1", lat=1.0, lng=2.0, added_by="Alice",
    )
    resp = await client.post(
        f"/api/events/{event['id']}/move-to-bin", headers=auth_headers
    )
    assert resp.status_code == 200
    idea = resp.json()
    assert idea["title"] == "Dinner"
    assert idea["time_hint"] == "7:30pm"
    assert idea["place_id"] == "p1"
    assert idea["lat"] == 1.0
    assert idea["added_by"] == "Alice"
    # event is gone
    resp = await client.get(f"/api/events/?trip_id={trip['id']}", headers=auth_headers)
    assert resp.json() == []


async def test_move_to_bin_no_start_time(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(client, auth_headers, trip["id"], title="NoTime")
    resp = await client.post(
        f"/api/events/{event['id']}/move-to-bin", headers=auth_headers
    )
    assert resp.json()["time_hint"] is None


async def test_move_to_bin_non_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(client, auth_headers, trip["id"])
    resp = await client.post(
        f"/api/events/{event['id']}/move-to-bin", headers=second_auth_headers
    )
    assert resp.status_code == 403


async def test_move_to_bin_nonexistent(client: AsyncClient, auth_headers):
    resp = await client.post("/api/events/9999/move-to-bin", headers=auth_headers)
    assert resp.status_code == 404


# ── Batch vote data in responses ──────────────────────────────────────────────

async def test_get_events_includes_vote_tallies(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev1 = await _create_event(client, auth_headers, trip["id"], title="A")
    ev2 = await _create_event(client, auth_headers, trip["id"], title="B")
    await client.post(f"/api/events/{ev1['id']}/vote", json={"value": 1}, headers=auth_headers)
    resp = await client.get(f"/api/events/?trip_id={trip['id']}", headers=auth_headers)
    events = resp.json()
    by_title = {e["title"]: e for e in events}
    assert by_title["A"]["up"] == 1 and by_title["A"]["my_vote"] == 1
    assert by_title["B"]["up"] == 0 and by_title["B"]["my_vote"] == 0


async def test_get_events_my_vote_is_caller_specific(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com",
        role="view_with_vote",
    )
    ev = await _create_event(client, auth_headers, trip["id"], title="X")
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": -1}, headers=second_auth_headers)

    alice_view = (await client.get(f"/api/events/?trip_id={trip['id']}", headers=auth_headers)).json()
    bob_view = (await client.get(f"/api/events/?trip_id={trip['id']}", headers=second_auth_headers)).json()
    assert alice_view[0]["my_vote"] == 1
    assert bob_view[0]["my_vote"] == -1


async def test_get_events_no_votes_returns_zeros(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await _create_event(client, auth_headers, trip["id"], title="Z")
    events = (await client.get(f"/api/events/?trip_id={trip['id']}", headers=auth_headers)).json()
    assert events[0]["up"] == 0 and events[0]["down"] == 0 and events[0]["my_vote"] == 0


async def test_patch_event_response_includes_votes(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"], title="Old")
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    resp = await client.patch(
        f"/api/events/{ev['id']}",
        json={"title": "New"},
        headers=auth_headers,
    )
    data = resp.json()
    assert data["up"] == 1 and data["my_vote"] == 1
