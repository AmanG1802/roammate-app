"""Group library: search, tag filter, provenance (origin_idea_id), cross-trip copy."""
import pytest
from httpx import AsyncClient


async def create_trip(client, headers, name="Trip"):
    r = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert r.status_code == 200
    return r.json()


async def create_group(client, headers, name="Crew"):
    r = await client.post("/api/groups/", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.json()


async def attach_trip(client, headers, group_id, trip_id):
    r = await client.post(f"/api/groups/{group_id}/trips/{trip_id}", headers=headers)
    assert r.status_code == 200, r.text


async def create_idea(client, headers, trip_id, title):
    r = await client.post(
        f"/api/trips/{trip_id}/ingest",
        json={"text": title},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return r.json()[0]


# ── Tags ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_and_get_idea_tags(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await create_idea(client, auth_headers, trip["id"], "Gelato")

    r = await client.put(
        f"/api/ideas/{idea['id']}/tags",
        json={"tags": ["Food", "FOOD", "dessert"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json() == ["food", "dessert"]

    r2 = await client.get(f"/api/ideas/{idea['id']}/tags", headers=auth_headers)
    assert sorted(r2.json()) == ["dessert", "food"]


@pytest.mark.asyncio
async def test_setting_tags_replaces_old_ones(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await create_idea(client, auth_headers, trip["id"], "Gelato")

    await client.put(f"/api/ideas/{idea['id']}/tags", json={"tags": ["food"]}, headers=auth_headers)
    await client.put(f"/api/ideas/{idea['id']}/tags", json={"tags": ["dessert"]}, headers=auth_headers)
    r = await client.get(f"/api/ideas/{idea['id']}/tags", headers=auth_headers)
    assert r.json() == ["dessert"]


# ── Library search/filter ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_library_search_by_title(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach_trip(client, auth_headers, g["id"], t["id"])
    await create_idea(client, auth_headers, t["id"], "Colosseum")
    await create_idea(client, auth_headers, t["id"], "Trevi Fountain")

    r = await client.get(f"/api/groups/{g['id']}/ideas?q=coli", headers=auth_headers)
    body = r.json()
    titles = {i["title"] for i in body}
    assert "Colosseum" in titles and "Trevi Fountain" not in titles


@pytest.mark.asyncio
async def test_library_filter_by_tag(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach_trip(client, auth_headers, g["id"], t["id"])
    a = await create_idea(client, auth_headers, t["id"], "Gelato")
    b = await create_idea(client, auth_headers, t["id"], "Colosseum")

    await client.put(f"/api/ideas/{a['id']}/tags", json={"tags": ["food"]}, headers=auth_headers)
    await client.put(f"/api/ideas/{b['id']}/tags", json={"tags": ["history"]}, headers=auth_headers)

    r = await client.get(f"/api/groups/{g['id']}/ideas?tag=food", headers=auth_headers)
    body = r.json()
    assert len(body) == 1 and body[0]["title"] == "Gelato"


@pytest.mark.asyncio
async def test_library_top_sort_by_votes(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach_trip(client, auth_headers, g["id"], t["id"])
    low = await create_idea(client, auth_headers, t["id"], "Low")
    high = await create_idea(client, auth_headers, t["id"], "High")

    await client.post(f"/api/ideas/{high['id']}/vote", json={"value": 1}, headers=auth_headers)

    r = await client.get(f"/api/groups/{g['id']}/ideas?sort=top", headers=auth_headers)
    body = r.json()
    assert body[0]["title"] == "High"
    assert body[0]["up"] == 1


@pytest.mark.asyncio
async def test_library_includes_trip_provenance(client, auth_headers):
    g = await create_group(client, auth_headers, name="Rome Squad")
    t = await create_trip(client, auth_headers, name="Rome 2026")
    await attach_trip(client, auth_headers, g["id"], t["id"])
    await create_idea(client, auth_headers, t["id"], "Pantheon")

    r = await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)
    body = r.json()
    assert len(body) == 1
    assert body[0]["trip"] == {"id": t["id"], "name": "Rome 2026"}


# ── Tag summary ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_group_tags_endpoint_returns_counts(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach_trip(client, auth_headers, g["id"], t["id"])
    a = await create_idea(client, auth_headers, t["id"], "A")
    b = await create_idea(client, auth_headers, t["id"], "B")
    await client.put(f"/api/ideas/{a['id']}/tags", json={"tags": ["food"]}, headers=auth_headers)
    await client.put(f"/api/ideas/{b['id']}/tags", json={"tags": ["food", "must-see"]}, headers=auth_headers)

    r = await client.get(f"/api/groups/{g['id']}/tags", headers=auth_headers)
    body = r.json()
    by_tag = {row["tag"]: row["count"] for row in body}
    assert by_tag.get("food") == 2
    assert by_tag.get("must-see") == 1


# ── Provenance / copy ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_copy_idea_sets_origin_and_carries_tags(client, auth_headers):
    src_trip = await create_trip(client, auth_headers, "Rome")
    dst_trip = await create_trip(client, auth_headers, "Florence")
    idea = await create_idea(client, auth_headers, src_trip["id"], "Gelateria")
    await client.put(f"/api/ideas/{idea['id']}/tags", json={"tags": ["food"]}, headers=auth_headers)

    r = await client.post(
        f"/api/ideas/{idea['id']}/copy",
        json={"target_trip_id": dst_trip["id"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    copy = r.json()
    assert copy["trip_id"] == dst_trip["id"]
    assert copy["origin_idea_id"] == idea["id"]

    tags = (await client.get(f"/api/ideas/{copy['id']}/tags", headers=auth_headers)).json()
    assert tags == ["food"]


@pytest.mark.asyncio
async def test_copy_requires_membership_on_target(client, auth_headers, second_auth_headers):
    """Bob tries to copy Alice's idea into his own trip — must 403 because Bob isn't on Alice's trip."""
    alice_trip = await create_trip(client, auth_headers, "Alice")
    idea = await create_idea(client, auth_headers, alice_trip["id"], "Secret Spot")
    bob_trip = await create_trip(client, second_auth_headers, "Bob")

    r = await client.post(
        f"/api/ideas/{idea['id']}/copy",
        json={"target_trip_id": bob_trip["id"]},
        headers=second_auth_headers,
    )
    assert r.status_code == 403
