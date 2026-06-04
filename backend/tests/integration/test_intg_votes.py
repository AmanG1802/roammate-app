"""§10 Votes — upvote, downvote, toggle, role gating, and tally queries."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


async def _ingest(client, headers, trip_id):
    r = await client.post(f"/api/trips/{trip_id}/ingest", json={"text": "Spot"}, headers=headers)
    return r.json()[0]


async def _create_event(client, headers, trip_id, title="Dinner"):
    r = await client.post("/api/events", json={"trip_id": trip_id, "title": title}, headers=headers)
    assert r.status_code == 201
    return r.json()


# ── Idea votes ────────────────────────────────────────────────────────────────

async def test_vote_on_idea_upvote(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"])
    resp = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["up"] == 1


async def test_vote_on_idea_downvote(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"])
    resp = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["down"] == 1


async def test_vote_on_idea_toggle_off(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    resp = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 0}, headers=auth_headers)
    assert resp.json()["up"] == 0


async def test_vote_on_idea_change_vote(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    resp = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=auth_headers)
    assert resp.json()["down"] == 1 and resp.json()["up"] == 0


async def test_vote_on_idea_view_only_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only")
    idea = await _ingest(client, auth_headers, trip["id"])
    resp = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=second_auth_headers)
    assert resp.status_code == 403


async def test_vote_on_idea_view_with_vote_allowed(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote")
    idea = await _ingest(client, auth_headers, trip["id"])
    resp = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=second_auth_headers)
    assert resp.status_code == 200


async def test_vote_on_idea_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"])
    resp = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=second_auth_headers)
    assert resp.status_code == 403


async def test_get_idea_vote_tally(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    resp = await client.get(f"/api/ideas/{idea['id']}/votes", headers=auth_headers)
    assert resp.json()["up"] == 1 and resp.json()["my_vote"] == 1


# ── Event votes ───────────────────────────────────────────────────────────────

async def test_vote_on_event(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    resp = await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    assert resp.status_code == 200


async def test_get_event_vote_tally(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    resp = await client.get(f"/api/events/{ev['id']}/votes", headers=auth_headers)
    assert resp.json()["up"] == 1
