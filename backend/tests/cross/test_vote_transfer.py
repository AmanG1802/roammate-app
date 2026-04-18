"""Vote transfer across entities: idea↔event, move-to-bin, bin-to-timeline roundtrip."""
import pytest


async def create_trip(client, headers, name="T", **extra):
    body = {"name": name, **extra}
    r = await client.post("/api/trips/", json=body, headers=headers)
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


# ── create_event response includes inline vote tallies ────────────────────────

@pytest.mark.asyncio
async def test_create_event_response_includes_transferred_votes(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)

    ev = await create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    assert ev["up"] == 1
    assert ev["down"] == 0
    assert ev["my_vote"] == 1


@pytest.mark.asyncio
async def test_create_event_response_zero_votes_without_source(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    assert ev["up"] == 0 and ev["down"] == 0 and ev["my_vote"] == 0


# ── move-to-bin response includes inline vote tallies ─────────────────────────

@pytest.mark.asyncio
async def test_move_to_bin_response_includes_votes(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"])
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    idea = r.json()
    assert idea["up"] == 1 and idea["down"] == 0 and idea["my_vote"] == 1


@pytest.mark.asyncio
async def test_move_to_bin_my_vote_reflects_caller(
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
    assert r.json()["my_vote"] == 1


# ── day-delete vote transfer ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_day_delete_bin_preserves_single_vote(client, auth_headers):
    trip = await create_trip(client, auth_headers, "T", start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    day_date = days[0]["date"]
    ev = await create_event(client, auth_headers, trip["id"], title="Beach")
    await client.patch(
        f"/api/events/{ev['id']}",
        json={"day_date": day_date},
        headers=auth_headers,
    )
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.delete(
        f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=bin",
        headers=auth_headers,
    )
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    assert len(ideas) == 1
    t = (await client.get(f"/api/ideas/{ideas[0]['id']}/votes", headers=auth_headers)).json()
    assert t["up"] == 1


@pytest.mark.asyncio
async def test_day_delete_bin_preserves_multi_user_votes(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers, "T", start_date="2026-06-01T00:00:00")
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote"
    )
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    day_date = days[0]["date"]
    ev = await create_event(client, auth_headers, trip["id"], title="Market")
    await client.patch(
        f"/api/events/{ev['id']}",
        json={"day_date": day_date},
        headers=auth_headers,
    )
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": -1}, headers=second_auth_headers)
    await client.delete(
        f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=bin",
        headers=auth_headers,
    )
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    t = (await client.get(f"/api/ideas/{ideas[0]['id']}/votes", headers=auth_headers)).json()
    assert t["up"] == 1 and t["down"] == 1


@pytest.mark.asyncio
async def test_day_delete_action_delete_no_idea_votes(client, auth_headers):
    trip = await create_trip(client, auth_headers, "T", start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    day_date = days[0]["date"]
    ev = await create_event(client, auth_headers, trip["id"], title="Temple")
    await client.patch(
        f"/api/events/{ev['id']}",
        json={"day_date": day_date},
        headers=auth_headers,
    )
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.delete(
        f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=delete",
        headers=auth_headers,
    )
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    assert ideas == []


@pytest.mark.asyncio
async def test_day_delete_bin_zero_votes_clean(client, auth_headers):
    trip = await create_trip(client, auth_headers, "T", start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    day_date = days[0]["date"]
    ev = await create_event(client, auth_headers, trip["id"], title="Park")
    await client.patch(
        f"/api/events/{ev['id']}",
        json={"day_date": day_date},
        headers=auth_headers,
    )
    await client.delete(
        f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=bin",
        headers=auth_headers,
    )
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    t = (await client.get(f"/api/ideas/{ideas[0]['id']}/votes", headers=auth_headers)).json()
    assert t == {"up": 0, "down": 0, "my_vote": 0}


# ── extended roundtrips ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_timeline_to_bin_roundtrip_votes_on_idea(client, auth_headers):
    """Event→bin preserves votes on the resulting idea; re-creating the event
    is not tested here because SQLite (without FK pragma) leaves orphaned
    EventVote rows that collide on ROWID reuse.  The idea→event leg is
    already covered by test_bin_to_timeline_roundtrip_keeps_votes."""
    trip = await create_trip(client, auth_headers)
    ev = await create_event(client, auth_headers, trip["id"], title="Cafe")
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    new_idea_id = r.json()["id"]
    t = (await client.get(f"/api/ideas/{new_idea_id}/votes", headers=auth_headers)).json()
    assert t["up"] == 1


@pytest.mark.asyncio
async def test_day_delete_bin_roundtrip_votes_on_idea(client, auth_headers):
    """Day-delete→bin preserves votes on the resulting idea.  Re-creating the
    event is not tested because SQLite (no FK pragma) leaves orphaned
    EventVote rows that collide on ROWID reuse."""
    trip = await create_trip(client, auth_headers, "T", start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    day_date = days[0]["date"]
    ev = await create_event(client, auth_headers, trip["id"], title="Falls")
    await client.patch(
        f"/api/events/{ev['id']}",
        json={"day_date": day_date},
        headers=auth_headers,
    )
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.delete(
        f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=bin",
        headers=auth_headers,
    )
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    t = (await client.get(f"/api/ideas/{ideas[0]['id']}/votes", headers=auth_headers)).json()
    assert t["up"] == 1
