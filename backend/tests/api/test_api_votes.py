"""API tests for votes.py — idea votes, event votes, voter lists."""

import pytest
from httpx import AsyncClient
from tests.conftest import create_trip, invite_and_accept


async def _seed_idea(client, auth_headers, trip_id):
    resp = await client.post(f"/api/trips/{trip_id}/ingest", headers=auth_headers, json={
        "text": "Visit the Louvre Museum",
    })
    assert resp.status_code == 200
    return resp.json()[0]["id"]


async def _create_event(client, auth_headers, trip_id):
    resp = await client.post("/api/events", headers=auth_headers, json={
        "trip_id": trip_id, "title": "Gallery Tour",
        "day_date": "2025-06-01", "start_time": "10:00:00", "end_time": "11:00:00",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


# ── POST /api/ideas/{idea_id}/vote ─────────────────────────────────────────

async def test_vote_on_idea_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Vote Trip", start_date="2025-06-01T00:00:00")
    idea_id = await _seed_idea(client, auth_headers, trip["id"])

    # Test 1a - POST - 200 OK - Upvote idea (admin has vote role)
    resp = await client.post(f"/api/ideas/{idea_id}/vote", headers=auth_headers, json={"value": 1})
    assert resp.status_code == 200
    assert resp.json()["up"] >= 1

    # Test 1b - POST - 200 OK - Change to downvote
    resp = await client.post(f"/api/ideas/{idea_id}/vote", headers=auth_headers, json={"value": -1})
    assert resp.status_code == 200
    assert resp.json()["down"] >= 1

    # Test 1c - POST - 200 OK - Remove vote (value=0)
    resp = await client.post(f"/api/ideas/{idea_id}/vote", headers=auth_headers, json={"value": 0})
    assert resp.status_code == 200

    # Test 1d - POST - 404 Not Found - Non-existent idea
    resp = await client.post("/api/ideas/999999/vote", headers=auth_headers, json={"value": 1})
    assert resp.status_code == 404

    # Test 1e - POST - 403 Forbidden - View-only member cannot vote
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only")
    resp = await client.post(f"/api/ideas/{idea_id}/vote", headers=second_auth_headers, json={"value": 1})
    assert resp.status_code == 403


# ── GET /api/ideas/{idea_id}/votes ─────────────────────────────────────────

async def test_get_idea_votes_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Vote Trip", start_date="2025-06-01T00:00:00")
    idea_id = await _seed_idea(client, auth_headers, trip["id"])

    # Test 2a - GET - 200 OK - Returns tally
    resp = await client.get(f"/api/ideas/{idea_id}/votes", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "up" in data and "down" in data

    # Test 2b - GET - 404 Not Found - Non-existent idea
    resp = await client.get("/api/ideas/999999/votes", headers=auth_headers)
    assert resp.status_code == 404

    # Test 2c - GET - 403 Forbidden - Non-member
    resp = await client.get(f"/api/ideas/{idea_id}/votes", headers=second_auth_headers)
    assert resp.status_code == 403


# ── POST /api/events/{event_id}/vote ───────────────────────────────────────

async def test_vote_on_event_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Vote Trip", start_date="2025-06-01T00:00:00")
    event_id = await _create_event(client, auth_headers, trip["id"])

    # Test 3a - POST - 200 OK - Upvote event
    resp = await client.post(f"/api/events/{event_id}/vote", headers=auth_headers, json={"value": 1})
    assert resp.status_code == 200
    assert resp.json()["up"] >= 1

    # Test 3b - POST - 404 Not Found - Non-existent event
    resp = await client.post("/api/events/999999/vote", headers=auth_headers, json={"value": 1})
    assert resp.status_code == 404

    # Test 3c - POST - 403 Forbidden - View-only cannot vote
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only")
    resp = await client.post(f"/api/events/{event_id}/vote", headers=second_auth_headers, json={"value": 1})
    assert resp.status_code == 403


# ── GET /api/events/{event_id}/votes ───────────────────────────────────────

async def test_get_event_votes_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Vote Trip", start_date="2025-06-01T00:00:00")
    event_id = await _create_event(client, auth_headers, trip["id"])

    # Test 4a - GET - 200 OK - Returns tally
    resp = await client.get(f"/api/events/{event_id}/votes", headers=auth_headers)
    assert resp.status_code == 200
    assert "up" in resp.json()

    # Test 4b - GET - 404 Not Found - Non-existent event
    resp = await client.get("/api/events/999999/votes", headers=auth_headers)
    assert resp.status_code == 404


# ── GET /api/ideas/{idea_id}/voters ────────────────────────────────────────

async def test_get_idea_voters_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Vote Trip", start_date="2025-06-01T00:00:00")
    idea_id = await _seed_idea(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea_id}/vote", headers=auth_headers, json={"value": 1})

    # Test 5a - GET - 200 OK - Returns voter lists
    resp = await client.get(f"/api/ideas/{idea_id}/voters", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "up_voters" in data and "down_voters" in data
    assert len(data["up_voters"]) >= 1

    # Test 5b - GET - 404 Not Found - Non-existent idea
    resp = await client.get("/api/ideas/999999/voters", headers=auth_headers)
    assert resp.status_code == 404


# ── GET /api/events/{event_id}/voters ──────────────────────────────────────

async def test_get_event_voters_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Vote Trip", start_date="2025-06-01T00:00:00")
    event_id = await _create_event(client, auth_headers, trip["id"])
    await client.post(f"/api/events/{event_id}/vote", headers=auth_headers, json={"value": 1})

    # Test 6a - GET - 200 OK - Returns voter lists
    resp = await client.get(f"/api/events/{event_id}/voters", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "up_voters" in data

    # Test 6b - GET - 404 Not Found - Non-existent event
    resp = await client.get("/api/events/999999/voters", headers=auth_headers)
    assert resp.status_code == 404
