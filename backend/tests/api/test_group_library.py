"""Group idea-library + tag-summary endpoints."""
import pytest
from httpx import AsyncClient


async def create_trip(client, headers, name="T"):
    r = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert r.status_code == 200
    return r.json()


async def create_group(client, headers, name="Crew"):
    r = await client.post("/api/groups/", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.json()


async def attach(client, headers, group_id, trip_id):
    r = await client.post(f"/api/groups/{group_id}/trips/{trip_id}", headers=headers)
    assert r.status_code == 200, r.text


async def ingest(client, headers, trip_id, title):
    r = await client.post(
        f"/api/trips/{trip_id}/ingest", json={"text": title}, headers=headers
    )
    assert r.status_code == 200, r.text
    return r.json()[0]


async def set_tags(client, headers, idea_id, tags):
    r = await client.put(
        f"/api/ideas/{idea_id}/tags", json={"tags": tags}, headers=headers
    )
    assert r.status_code == 200, r.text


# ── Aggregation ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_library_aggregates_across_multiple_trips(client, auth_headers):
    g = await create_group(client, auth_headers)
    t1 = await create_trip(client, auth_headers, "Rome")
    t2 = await create_trip(client, auth_headers, "Florence")
    await attach(client, auth_headers, g["id"], t1["id"])
    await attach(client, auth_headers, g["id"], t2["id"])
    await ingest(client, auth_headers, t1["id"], "Colosseum")
    await ingest(client, auth_headers, t2["id"], "Duomo")

    body = (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json()
    assert {i["title"] for i in body} == {"Colosseum", "Duomo"}


@pytest.mark.asyncio
async def test_library_excludes_unattached_trips(client, auth_headers):
    g = await create_group(client, auth_headers)
    attached = await create_trip(client, auth_headers, "In")
    detached = await create_trip(client, auth_headers, "Out")
    await attach(client, auth_headers, g["id"], attached["id"])
    await ingest(client, auth_headers, attached["id"], "Keep")
    await ingest(client, auth_headers, detached["id"], "Drop")

    body = (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json()
    assert [i["title"] for i in body] == ["Keep"]


@pytest.mark.asyncio
async def test_library_non_member_forbidden(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    r = await client.get(f"/api/groups/{g['id']}/ideas", headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_library_empty_when_group_has_no_trips(client, auth_headers):
    g = await create_group(client, auth_headers)
    r = await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)
    assert r.json() == []


@pytest.mark.asyncio
async def test_library_requires_auth(client):
    r = await client.get("/api/groups/1/ideas")
    assert r.status_code == 401


# ── Query params ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_library_search_by_title(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach(client, auth_headers, g["id"], t["id"])
    await ingest(client, auth_headers, t["id"], "Colosseum")
    await ingest(client, auth_headers, t["id"], "Trevi")

    r = (await client.get(f"/api/groups/{g['id']}/ideas?q=colo", headers=auth_headers)).json()
    titles = {i["title"] for i in r}
    assert "Colosseum" in titles and "Trevi" not in titles


@pytest.mark.asyncio
async def test_library_search_case_insensitive(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach(client, auth_headers, g["id"], t["id"])
    await ingest(client, auth_headers, t["id"], "Pantheon")
    r = (await client.get(f"/api/groups/{g['id']}/ideas?q=PANTH", headers=auth_headers)).json()
    assert [i["title"] for i in r] == ["Pantheon"]


@pytest.mark.asyncio
async def test_library_search_no_match(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach(client, auth_headers, g["id"], t["id"])
    await ingest(client, auth_headers, t["id"], "Thing")
    r = (await client.get(f"/api/groups/{g['id']}/ideas?q=zzz", headers=auth_headers)).json()
    assert r == []


@pytest.mark.asyncio
async def test_library_filter_by_tag(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach(client, auth_headers, g["id"], t["id"])
    a = await ingest(client, auth_headers, t["id"], "Gelato")
    b = await ingest(client, auth_headers, t["id"], "Colosseum")
    await set_tags(client, auth_headers, a["id"], ["food"])
    await set_tags(client, auth_headers, b["id"], ["history"])
    r = (await client.get(f"/api/groups/{g['id']}/ideas?tag=food", headers=auth_headers)).json()
    assert [i["title"] for i in r] == ["Gelato"]


@pytest.mark.asyncio
async def test_library_filter_by_trip_id(client, auth_headers):
    g = await create_group(client, auth_headers)
    t1 = await create_trip(client, auth_headers, "A")
    t2 = await create_trip(client, auth_headers, "B")
    await attach(client, auth_headers, g["id"], t1["id"])
    await attach(client, auth_headers, g["id"], t2["id"])
    await ingest(client, auth_headers, t1["id"], "InA")
    await ingest(client, auth_headers, t2["id"], "InB")
    r = (await client.get(
        f"/api/groups/{g['id']}/ideas?trip_id={t1['id']}", headers=auth_headers
    )).json()
    assert [i["title"] for i in r] == ["InA"]


@pytest.mark.asyncio
async def test_library_filter_by_trip_id_outside_group_empty(
    client, auth_headers
):
    g = await create_group(client, auth_headers)
    in_grp = await create_trip(client, auth_headers, "In")
    out_grp = await create_trip(client, auth_headers, "Out")
    await attach(client, auth_headers, g["id"], in_grp["id"])
    await ingest(client, auth_headers, out_grp["id"], "Hidden")
    r = (await client.get(
        f"/api/groups/{g['id']}/ideas?trip_id={out_grp['id']}", headers=auth_headers
    )).json()
    assert r == []


@pytest.mark.asyncio
async def test_library_combined_q_and_tag(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach(client, auth_headers, g["id"], t["id"])
    a = await ingest(client, auth_headers, t["id"], "Gelato Shop")
    b = await ingest(client, auth_headers, t["id"], "Gelato Museum")
    await set_tags(client, auth_headers, a["id"], ["food"])
    await set_tags(client, auth_headers, b["id"], ["museum"])
    r = (await client.get(
        f"/api/groups/{g['id']}/ideas?q=gelato&tag=food", headers=auth_headers
    )).json()
    assert [i["title"] for i in r] == ["Gelato Shop"]


# ── Sort ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_library_sort_recent_default(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach(client, auth_headers, g["id"], t["id"])
    await ingest(client, auth_headers, t["id"], "First")
    await ingest(client, auth_headers, t["id"], "Second")
    r = (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json()
    assert [i["title"] for i in r] == ["Second", "First"]


@pytest.mark.asyncio
async def test_library_sort_top(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach(client, auth_headers, g["id"], t["id"])
    low = await ingest(client, auth_headers, t["id"], "Low")
    high = await ingest(client, auth_headers, t["id"], "High")
    await client.post(f"/api/ideas/{high['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = (await client.get(f"/api/groups/{g['id']}/ideas?sort=top", headers=auth_headers)).json()
    assert r[0]["title"] == "High"
    assert r[0]["up"] == 1


@pytest.mark.asyncio
async def test_library_sort_title_alphabetical(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach(client, auth_headers, g["id"], t["id"])
    await ingest(client, auth_headers, t["id"], "Banana")
    await ingest(client, auth_headers, t["id"], "Apple")
    r = (await client.get(f"/api/groups/{g['id']}/ideas?sort=title", headers=auth_headers)).json()
    assert [i["title"] for i in r] == ["Apple", "Banana"]


@pytest.mark.asyncio
async def test_library_unknown_sort_falls_back_to_recent(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach(client, auth_headers, g["id"], t["id"])
    await ingest(client, auth_headers, t["id"], "First")
    await ingest(client, auth_headers, t["id"], "Second")
    r = (await client.get(f"/api/groups/{g['id']}/ideas?sort=bogus", headers=auth_headers)).json()
    assert [i["title"] for i in r] == ["Second", "First"]


# ── Tally fields ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_library_row_fields(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers, "Rome")
    await attach(client, auth_headers, g["id"], t["id"])
    a = await ingest(client, auth_headers, t["id"], "Gelato")
    await set_tags(client, auth_headers, a["id"], ["food"])
    await client.post(f"/api/ideas/{a['id']}/vote", json={"value": 1}, headers=auth_headers)

    row = (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json()[0]
    assert row["up"] == 1
    assert row["down"] == 0
    assert row["my_vote"] == 1
    assert row["tags"] == ["food"]
    assert row["trip"] == {"id": t["id"], "name": "Rome"}


@pytest.mark.asyncio
async def test_library_my_vote_per_caller(
    client, auth_headers, second_auth_headers
):
    g = await create_group(client, auth_headers)
    await _accept_into_group(client, auth_headers, second_auth_headers, g["id"])
    t = await create_trip(client, auth_headers, "T")
    await attach(client, auth_headers, g["id"], t["id"])
    # Bob is a trip viewer (view_with_vote) so he can vote
    r = await client.post(
        f"/api/trips/{t['id']}/invite",
        json={"email": "bob@test.com", "role": "view_with_vote"},
        headers=auth_headers,
    )
    mid = r.json()["id"]
    await client.post(f"/api/trips/invitations/{mid}/accept", headers=second_auth_headers)

    idea = await ingest(client, auth_headers, t["id"], "Gelato")
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=second_auth_headers)

    alice_row = (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json()[0]
    bob_row = (await client.get(f"/api/groups/{g['id']}/ideas", headers=second_auth_headers)).json()[0]
    assert alice_row["my_vote"] == 1
    assert bob_row["my_vote"] == -1
    assert alice_row["up"] == bob_row["up"] == 1
    assert alice_row["down"] == bob_row["down"] == 1


async def _accept_into_group(client, admin_headers, invitee_headers, group_id):
    r = await client.post(
        f"/api/groups/{group_id}/invite",
        json={"email": "bob@test.com"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    pending = (await client.get("/api/groups/invitations/pending", headers=invitee_headers)).json()
    mid = [p["id"] for p in pending if p["group_id"] == group_id][0]
    await client.post(f"/api/groups/invitations/{mid}/accept", headers=invitee_headers)


# ── Tag summary ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_group_tags_empty_when_no_ideas(client, auth_headers):
    g = await create_group(client, auth_headers)
    r = (await client.get(f"/api/groups/{g['id']}/tags", headers=auth_headers)).json()
    assert r == []


@pytest.mark.asyncio
async def test_group_tags_sorted_by_count_desc(client, auth_headers):
    g = await create_group(client, auth_headers)
    t = await create_trip(client, auth_headers)
    await attach(client, auth_headers, g["id"], t["id"])
    a = await ingest(client, auth_headers, t["id"], "A")
    b = await ingest(client, auth_headers, t["id"], "B")
    await set_tags(client, auth_headers, a["id"], ["food"])
    await set_tags(client, auth_headers, b["id"], ["food", "must-see"])
    r = (await client.get(f"/api/groups/{g['id']}/tags", headers=auth_headers)).json()
    assert r[0] == {"tag": "food", "count": 2}
    assert {"tag": "must-see", "count": 1} in r


@pytest.mark.asyncio
async def test_group_tags_non_member_forbidden(
    client, auth_headers, second_auth_headers
):
    g = await create_group(client, auth_headers)
    r = await client.get(f"/api/groups/{g['id']}/tags", headers=second_auth_headers)
    assert r.status_code == 403
