"""Vote transfer across entities: idea↔event, move-to-bin, bin-to-timeline roundtrip."""
import pytest


async def create_trip(client, headers, name="T"):
    r = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert r.status_code == 200
    return r.json()


async def invite_and_accept(client, admin_headers, invitee_headers, trip_id, email, role):
    r = await client.post(
        f"/api/trips/{trip_id}/invite",
        json={"email": email, "role": role},
        headers=admin_headers,
    )
    mid = r.json()["id"]
    await client.post(f"/api/trips/invitations/{mid}/accept", headers=invitee_headers)


async def ingest(client, headers, trip_id, title="X"):
    r = await client.post(
        f"/api/trips/{trip_id}/ingest", json={"text": title}, headers=headers
    )
    return r.json()[0]


async def create_event(client, headers, trip_id, title="Dinner", source_idea_id=None):
    body = {"trip_id": trip_id, "title": title}
    if source_idea_id is not None:
        body["source_idea_id"] = source_idea_id
    r = await client.post("/api/events/", json=body, headers=headers)
    assert r.status_code == 201
    return r.json()


# ── idea → event ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_idea_to_event_transfer(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)

    ev = await create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    tally = (await client.get(f"/api/events/{ev['id']}/votes", headers=auth_headers)).json()
    assert tally["up"] == 1


@pytest.mark.asyncio
async def test_idea_to_event_preserves_per_user_values(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote"
    )
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=second_auth_headers)

    ev = await create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    tally = (await client.get(f"/api/events/{ev['id']}/votes", headers=auth_headers)).json()
    assert tally["up"] == 1 and tally["down"] == 1


@pytest.mark.asyncio
async def test_idea_to_event_leaves_source_votes(client, auth_headers):
    """Transferring votes does not delete source IdeaVote rows."""
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    await create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    tally = (await client.get(f"/api/ideas/{idea['id']}/votes", headers=auth_headers)).json()
    assert tally["up"] == 1


@pytest.mark.asyncio
async def test_event_created_without_source_has_no_votes(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    t = (await client.get(f"/api/events/{ev['id']}/votes", headers=auth_headers)).json()
    assert t == {"up": 0, "down": 0, "my_vote": 0}


# ── event → idea (move-to-bin) ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_move_to_bin_transfer(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    idea_id = r.json()["id"]
    t = (await client.get(f"/api/ideas/{idea_id}/votes", headers=auth_headers)).json()
    assert t["up"] == 1


@pytest.mark.asyncio
async def test_move_to_bin_preserves_up_and_down(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote"
    )
    ev = await create_event(client, auth_headers, trip["id"])
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": -1}, headers=second_auth_headers)
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    idea_id = r.json()["id"]
    t = (await client.get(f"/api/ideas/{idea_id}/votes", headers=auth_headers)).json()
    assert t["up"] == 1 and t["down"] == 1


@pytest.mark.asyncio
async def test_move_to_bin_no_votes_clean(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    idea_id = r.json()["id"]
    t = (await client.get(f"/api/ideas/{idea_id}/votes", headers=auth_headers)).json()
    assert t == {"up": 0, "down": 0, "my_vote": 0}


# ── roundtrip ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bin_to_timeline_roundtrip_keeps_votes(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    ev = await create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    new_idea_id = r.json()["id"]
    t = (await client.get(f"/api/ideas/{new_idea_id}/votes", headers=auth_headers)).json()
    assert t["up"] == 1


@pytest.mark.asyncio
async def test_move_to_bin_shows_in_group_library_with_tally(
    client, auth_headers
):
    g = await client.post("/api/groups/", json={"name": "G"}, headers=auth_headers)
    group_id = g.json()["id"]
    trip = await create_trip(client, auth_headers, "Rome")
    await client.post(f"/api/groups/{group_id}/trips/{trip['id']}", headers=auth_headers)
    ev = await create_event(client, auth_headers, trip["id"], title="Spot")
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)

    body = (await client.get(f"/api/groups/{group_id}/ideas", headers=auth_headers)).json()
    assert body[0]["title"] == "Spot"
    assert body[0]["up"] == 1
