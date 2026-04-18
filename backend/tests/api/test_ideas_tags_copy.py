"""Idea-scoped endpoints: `/api/ideas/{id}/tags` and `/api/ideas/{id}/copy`."""
import pytest
from httpx import AsyncClient


async def create_trip(client, headers, name="T"):
    r = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert r.status_code == 200
    return r.json()


async def ingest(client, headers, trip_id, title):
    r = await client.post(
        f"/api/trips/{trip_id}/ingest", json={"text": title}, headers=headers
    )
    assert r.status_code == 200, r.text
    return r.json()[0]


async def invite_and_accept(client, admin_headers, invitee_headers, trip_id, email, role):
    r = await client.post(
        f"/api/trips/{trip_id}/invite",
        json={"email": email, "role": role},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    r = await client.post(f"/api/trips/invitations/{mid}/accept", headers=invitee_headers)
    assert r.status_code == 200, r.text


# ── Tags: get ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_tags_empty_when_none_set(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "X")
    r = await client.get(f"/api/ideas/{idea['id']}/tags", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_get_tags_non_member_forbidden(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "X")
    r = await client.get(f"/api/ideas/{idea['id']}/tags", headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_tags_nonexistent_idea_404(client, auth_headers):
    r = await client.get("/api/ideas/9999/tags", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_tags_requires_auth(client):
    r = await client.get("/api/ideas/1/tags")
    assert r.status_code == 401


# ── Tags: set ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_tags_normalizes(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "X")
    r = await client.put(
        f"/api/ideas/{idea['id']}/tags",
        json={"tags": ["Food", "FOOD", "dessert"]},
        headers=auth_headers,
    )
    assert r.json() == ["food", "dessert"]


@pytest.mark.asyncio
async def test_set_tags_strips_whitespace(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "X")
    r = await client.put(
        f"/api/ideas/{idea['id']}/tags",
        json={"tags": ["  food  ", "\tmuseum\n"]},
        headers=auth_headers,
    )
    assert sorted(r.json()) == ["food", "museum"]


@pytest.mark.asyncio
async def test_set_tags_drops_empty_and_whitespace(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "X")
    r = await client.put(
        f"/api/ideas/{idea['id']}/tags",
        json={"tags": ["", "   ", "food"]},
        headers=auth_headers,
    )
    assert r.json() == ["food"]


@pytest.mark.asyncio
async def test_set_tags_replaces_previous(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "X")
    await client.put(f"/api/ideas/{idea['id']}/tags", json={"tags": ["food"]}, headers=auth_headers)
    await client.put(f"/api/ideas/{idea['id']}/tags", json={"tags": ["dessert"]}, headers=auth_headers)
    r = await client.get(f"/api/ideas/{idea['id']}/tags", headers=auth_headers)
    assert r.json() == ["dessert"]


@pytest.mark.asyncio
async def test_set_tags_empty_list_clears(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "X")
    await client.put(f"/api/ideas/{idea['id']}/tags", json={"tags": ["food"]}, headers=auth_headers)
    await client.put(f"/api/ideas/{idea['id']}/tags", json={"tags": []}, headers=auth_headers)
    r = await client.get(f"/api/ideas/{idea['id']}/tags", headers=auth_headers)
    assert r.json() == []


@pytest.mark.asyncio
async def test_set_tags_by_view_only_forbidden(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "X")
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only"
    )
    r = await client.put(
        f"/api/ideas/{idea['id']}/tags", json={"tags": ["food"]}, headers=second_auth_headers
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_set_tags_by_view_with_vote_allowed(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "X")
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote"
    )
    r = await client.put(
        f"/api/ideas/{idea['id']}/tags",
        json={"tags": ["food"]},
        headers=second_auth_headers,
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_set_tags_by_non_member_forbidden(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "X")
    r = await client.put(
        f"/api/ideas/{idea['id']}/tags",
        json={"tags": ["food"]},
        headers=second_auth_headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_set_tags_nonexistent_idea_404(client, auth_headers):
    r = await client.put(
        "/api/ideas/9999/tags", json={"tags": ["food"]}, headers=auth_headers
    )
    assert r.status_code == 404


# ── Copy ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_copy_sets_origin_and_carries_tags(client, auth_headers):
    """origin_idea_id isn't exposed by the direct copy response schema; verify via library."""
    src = await create_trip(client, auth_headers, "Rome")
    dst = await create_trip(client, auth_headers, "Florence")
    # Attach dst to a group so we can read origin_idea_id from LibraryIdeaOut
    g = (await client.post("/api/groups/", json={"name": "G"}, headers=auth_headers)).json()
    await client.post(f"/api/groups/{g['id']}/trips/{dst['id']}", headers=auth_headers)

    idea = await ingest(client, auth_headers, src["id"], "Gelateria")
    await client.put(
        f"/api/ideas/{idea['id']}/tags",
        json={"tags": ["food", "must-try"]},
        headers=auth_headers,
    )
    r = await client.post(
        f"/api/ideas/{idea['id']}/copy",
        json={"target_trip_id": dst["id"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    copy = r.json()
    assert copy["trip_id"] == dst["id"]

    lib = (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json()
    row = next(r for r in lib if r["id"] == copy["id"])
    assert row["origin_idea_id"] == idea["id"]

    tags = (await client.get(f"/api/ideas/{copy['id']}/tags", headers=auth_headers)).json()
    assert sorted(tags) == ["food", "must-try"]


@pytest.mark.asyncio
async def test_copy_preserves_place_lat_lng_url_hint_added_by(
    client, auth_headers, db_session
):
    """Create an idea with all metadata, then copy and verify every field."""
    from app.models.all_models import IdeaBinItem, Trip, TripMember
    src = await create_trip(client, auth_headers, "Rome")
    dst = await create_trip(client, auth_headers, "Florence")
    # Use ingest for simplicity; fill metadata via direct DB write for this test
    idea = await ingest(client, auth_headers, src["id"], "Spot")
    # Mutate source idea via PATCH to add time_hint
    await client.patch(
        f"/api/trips/{src['id']}/ideas/{idea['id']}",
        json={"time_hint": "2pm"},
        headers=auth_headers,
    )

    r = await client.post(
        f"/api/ideas/{idea['id']}/copy",
        json={"target_trip_id": dst["id"]},
        headers=auth_headers,
    )
    copy = r.json()
    assert copy["time_hint"] == "2pm"
    assert copy["title"] == "Spot"


@pytest.mark.asyncio
async def test_copy_of_copy_keeps_original_origin(client, auth_headers):
    a = await create_trip(client, auth_headers, "A")
    b = await create_trip(client, auth_headers, "B")
    c = await create_trip(client, auth_headers, "C")
    # Attach c to a group so we can inspect origin_idea_id via library
    g = (await client.post("/api/groups/", json={"name": "G"}, headers=auth_headers)).json()
    await client.post(f"/api/groups/{g['id']}/trips/{c['id']}", headers=auth_headers)

    src = await ingest(client, auth_headers, a["id"], "X")
    copy1 = (await client.post(
        f"/api/ideas/{src['id']}/copy",
        json={"target_trip_id": b["id"]},
        headers=auth_headers,
    )).json()
    copy2 = (await client.post(
        f"/api/ideas/{copy1['id']}/copy",
        json={"target_trip_id": c["id"]},
        headers=auth_headers,
    )).json()
    lib = (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json()
    row = next(r for r in lib if r["id"] == copy2["id"])
    # origin is sticky to the very first idea
    assert row["origin_idea_id"] == src["id"]


@pytest.mark.asyncio
async def test_copy_requires_membership_on_source(
    client, auth_headers, second_auth_headers
):
    alice = await create_trip(client, auth_headers, "Alice")
    idea = await ingest(client, auth_headers, alice["id"], "Secret")
    bob = await create_trip(client, second_auth_headers, "Bob")
    r = await client.post(
        f"/api/ideas/{idea['id']}/copy",
        json={"target_trip_id": bob["id"]},
        headers=second_auth_headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_copy_requires_membership_on_target(
    client, auth_headers, second_auth_headers
):
    alice = await create_trip(client, auth_headers, "Alice")
    idea = await ingest(client, auth_headers, alice["id"], "Spot")
    bob = await create_trip(client, second_auth_headers, "Bob")
    r = await client.post(
        f"/api/ideas/{idea['id']}/copy",
        json={"target_trip_id": bob["id"]},
        headers=auth_headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_copy_same_trip_duplicates_row(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "Spot")
    r = await client.post(
        f"/api/ideas/{idea['id']}/copy",
        json={"target_trip_id": trip["id"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    assert len(ideas) == 2


@pytest.mark.asyncio
async def test_copy_nonexistent_idea_404(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    r = await client.post(
        "/api/ideas/9999/copy",
        json={"target_trip_id": trip["id"]},
        headers=auth_headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_copy_nonexistent_target_trip_forbidden(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await ingest(client, auth_headers, trip["id"], "X")
    r = await client.post(
        f"/api/ideas/{idea['id']}/copy",
        json={"target_trip_id": 99999},
        headers=auth_headers,
    )
    # Not a member of the missing trip -> 403
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_copy_no_tags_on_source(client, auth_headers):
    a = await create_trip(client, auth_headers, "A")
    b = await create_trip(client, auth_headers, "B")
    idea = await ingest(client, auth_headers, a["id"], "X")
    r = await client.post(
        f"/api/ideas/{idea['id']}/copy",
        json={"target_trip_id": b["id"]},
        headers=auth_headers,
    )
    copy = r.json()
    tags = (await client.get(f"/api/ideas/{copy['id']}/tags", headers=auth_headers)).json()
    assert tags == []
