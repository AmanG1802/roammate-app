"""Vote endpoints: role gating, tally, edits, voter lists, validation."""
import pytest
from httpx import AsyncClient


async def create_trip(client, headers, name="T"):
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
    m = await invite(client, admin_headers, trip_id, email, role)
    r = await client.post(f"/api/trips/invitations/{m['id']}/accept", headers=invitee_headers)
    assert r.status_code == 200


async def ingest(client, headers, trip_id, title="Gelato"):
    r = await client.post(
        f"/api/trips/{trip_id}/ingest", json={"text": title}, headers=headers
    )
    assert r.status_code == 200, r.text
    return r.json()[0]


async def create_event(client, headers, trip_id, title="Dinner", source_idea_id=None):
    body = {"trip_id": trip_id, "title": title}
    if source_idea_id is not None:
        body["source_idea_id"] = source_idea_id
    r = await client.post("/api/events/", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── Idea votes: role gating ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_vote_on_idea(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body == {"up": 1, "down": 0, "my_vote": 1}


@pytest.mark.asyncio
async def test_view_only_cannot_vote_on_idea(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only")
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_view_with_vote_can_vote(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote")
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=second_auth_headers)
    assert r.status_code == 200
    assert r.json()["down"] == 1


@pytest.mark.asyncio
async def test_non_member_cannot_vote(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_vote_requires_auth(client):
    r = await client.post("/api/ideas/1/vote", json={"value": 1})
    assert r.status_code == 401


# ── Idea votes: edits ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_zero_value_removes_vote(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 0}, headers=auth_headers)
    assert r.json() == {"up": 0, "down": 0, "my_vote": 0}


@pytest.mark.asyncio
async def test_zero_value_when_no_existing_vote_is_noop(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 0}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"up": 0, "down": 0, "my_vote": 0}


@pytest.mark.asyncio
async def test_upvote_then_downvote_flips(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=auth_headers)
    assert r.json() == {"up": 0, "down": 1, "my_vote": -1}


@pytest.mark.asyncio
async def test_revote_same_value_noop(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    assert r.json()["up"] == 1


# ── Idea votes: tally reads ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_view_only_can_read_tally(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only"
    )
    r = await client.get(f"/api/ideas/{idea['id']}/votes", headers=second_auth_headers)
    assert r.status_code == 200
    assert r.json()["up"] == 1
    assert r.json()["my_vote"] == 0


@pytest.mark.asyncio
async def test_get_idea_votes_non_member_forbidden(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    r = await client.get(f"/api/ideas/{idea['id']}/votes", headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_idea_votes_nonexistent_404(client, auth_headers):
    r = await client.get("/api/ideas/9999/votes", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_tally_reflects_multi_user(
    client, auth_headers, second_auth_headers, third_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote")
    await invite_and_accept(client, auth_headers, third_auth_headers, trip["id"], "carol@test.com", "view_with_vote")
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=second_auth_headers)
    # Carol abstains
    r = await client.get(f"/api/ideas/{idea['id']}/votes", headers=third_auth_headers)
    assert r.json() == {"up": 1, "down": 1, "my_vote": 0}


# ── Validation ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [2, -2, 10, 1.5, "up"])
async def test_invalid_vote_value_422(client, auth_headers, bad):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    r = await client.post(
        f"/api/ideas/{idea['id']}/vote", json={"value": bad}, headers=auth_headers
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_vote_value_missing_field_422(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    r = await client.post(
        f"/api/ideas/{idea['id']}/vote", json={}, headers=auth_headers
    )
    assert r.status_code == 422


# ── Event votes ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_vote_on_event(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    r = await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["up"] == 1


@pytest.mark.asyncio
async def test_view_only_cannot_vote_on_event(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only")
    r = await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_event_votes_non_member_403(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    r = await client.get(f"/api/events/{ev['id']}/votes", headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_event_votes_nonexistent_404(client, auth_headers):
    r = await client.get("/api/events/9999/votes", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_event_vote_nonexistent_404(client, auth_headers):
    r = await client.post(
        "/api/events/9999/vote", json={"value": 1}, headers=auth_headers
    )
    assert r.status_code == 404


# ── Voter lists ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_idea_voters_split_up_down(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote")
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=second_auth_headers)
    r = (await client.get(f"/api/ideas/{idea['id']}/voters", headers=auth_headers)).json()
    up_names = {v["name"] for v in r["up_voters"]}
    down_names = {v["name"] for v in r["down_voters"]}
    assert "Alice Smith" in up_names
    assert "Bob Jones" in down_names


@pytest.mark.asyncio
async def test_idea_voters_read_by_view_only(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only")
    r = await client.get(f"/api/ideas/{idea['id']}/voters", headers=second_auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_idea_voters_non_member_403(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    r = await client.get(f"/api/ideas/{idea['id']}/voters", headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_idea_voters_nonexistent_404(client, auth_headers):
    r = await client.get("/api/ideas/9999/voters", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_event_voters_split(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote")
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": -1}, headers=second_auth_headers)
    r = (await client.get(f"/api/events/{ev['id']}/voters", headers=auth_headers)).json()
    assert len(r["up_voters"]) == 1 and len(r["down_voters"]) == 1


@pytest.mark.asyncio
async def test_event_voters_non_member_403(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    r = await client.get(f"/api/events/{ev['id']}/voters", headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_event_voters_nonexistent_404(client, auth_headers):
    r = await client.get("/api/events/9999/voters", headers=auth_headers)
    assert r.status_code == 404


# ── Voter list edge cases ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_idea_voters_empty_when_no_votes(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    r = (await client.get(f"/api/ideas/{idea['id']}/voters", headers=auth_headers)).json()
    assert r["up_voters"] == [] and r["down_voters"] == []


@pytest.mark.asyncio
async def test_idea_voters_updates_after_vote_removal(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = (await client.get(f"/api/ideas/{idea['id']}/voters", headers=auth_headers)).json()
    assert len(r["up_voters"]) == 1
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 0}, headers=auth_headers)
    r = (await client.get(f"/api/ideas/{idea['id']}/voters", headers=auth_headers)).json()
    assert r["up_voters"] == [] and r["down_voters"] == []


@pytest.mark.asyncio
async def test_event_voters_after_transfer_from_idea(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    ev = await create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    r = (await client.get(f"/api/events/{ev['id']}/voters", headers=auth_headers)).json()
    assert len(r["up_voters"]) == 1
    assert r["up_voters"][0]["name"] == "Alice Smith"


@pytest.mark.asyncio
async def test_event_voters_empty_when_no_votes(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    r = (await client.get(f"/api/events/{ev['id']}/voters", headers=auth_headers)).json()
    assert r["up_voters"] == [] and r["down_voters"] == []
