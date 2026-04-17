"""Votes on ideas + events: role gating, tally, vote transfer on move-to-bin / bin-to-timeline."""
from datetime import datetime
import pytest
from httpx import AsyncClient


async def create_trip(client, headers, name="Trip"):
    r = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert r.status_code == 200
    return r.json()


async def invite(client, admin_headers, trip_id, email, role):
    r = await client.post(
        f"/api/trips/{trip_id}/invite",
        json={"email": email, "role": role},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def invite_and_accept(client, admin_headers, invitee_headers, trip_id, email, role):
    """Invite invitee and have them accept — returns the TripMember dict."""
    member = await invite(client, admin_headers, trip_id, email, role)
    r = await client.post(
        f"/api/trips/invitations/{member['id']}/accept",
        headers=invitee_headers,
    )
    assert r.status_code == 200, r.text
    return r.json()


async def create_idea(client, headers, trip_id, title="Gelato"):
    r = await client.post(
        f"/api/trips/{trip_id}/ingest",
        json={"text": title},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    ideas = r.json()
    assert ideas
    return ideas[0]


async def create_event(client, headers, trip_id, title="Dinner", source_idea_id=None):
    body = {"trip_id": trip_id, "title": title}
    if source_idea_id is not None:
        body["source_idea_id"] = source_idea_id
    r = await client.post("/api/events/", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── Idea votes ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_vote_on_idea(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await create_idea(client, auth_headers, trip["id"])
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["up"] == 1 and body["down"] == 0 and body["my_vote"] == 1


@pytest.mark.asyncio
async def test_view_only_member_cannot_vote(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await create_idea(client, auth_headers, trip["id"])
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only")

    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_view_with_vote_can_vote(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await create_idea(client, auth_headers, trip["id"])
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote")

    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=second_auth_headers)
    assert r.status_code == 200
    assert r.json()["down"] == 1


@pytest.mark.asyncio
async def test_view_only_can_read_tally(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await create_idea(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    await invite(client, auth_headers, trip["id"], "bob@test.com", "view_only")

    r = await client.get(f"/api/ideas/{idea['id']}/votes", headers=second_auth_headers)
    assert r.status_code == 200
    assert r.json()["up"] == 1


@pytest.mark.asyncio
async def test_zero_value_removes_vote(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await create_idea(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 0}, headers=auth_headers)
    assert r.json()["up"] == 0 and r.json()["my_vote"] == 0


@pytest.mark.asyncio
async def test_vote_is_idempotent_per_user(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await create_idea(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=auth_headers)
    assert r.json()["up"] == 0 and r.json()["down"] == 1


@pytest.mark.asyncio
async def test_invalid_vote_value_is_rejected(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await create_idea(client, auth_headers, trip["id"])
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 2}, headers=auth_headers)
    assert r.status_code == 422


# ── Event votes ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_vote_on_event(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    r = await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["up"] == 1


@pytest.mark.asyncio
async def test_view_only_cannot_vote_on_event(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    await invite(client, auth_headers, trip["id"], "bob@test.com", "view_only")
    r = await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=second_auth_headers)
    assert r.status_code == 403


# ── Vote transfer ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_votes_transfer_idea_to_event(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await create_idea(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)

    ev = await create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    r = await client.get(f"/api/events/{ev['id']}/votes", headers=auth_headers)
    assert r.json()["up"] == 1


@pytest.mark.asyncio
async def test_votes_transfer_event_to_idea_on_move_to_bin(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)

    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    assert r.status_code == 200
    idea_id = r.json()["id"]
    tally = (await client.get(f"/api/ideas/{idea_id}/votes", headers=auth_headers)).json()
    assert tally["up"] == 1
