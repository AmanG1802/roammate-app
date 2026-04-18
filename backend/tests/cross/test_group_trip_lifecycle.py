"""End-to-end group workflows that stretch multiple endpoints together."""
import pytest


async def register(client, email, name):
    await client.post(
        "/api/users/register",
        json={"email": email, "password": "password123", "name": name},
    )
    r = await client.post(
        "/api/users/login",
        json={"email": email, "password": "password123"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def mk_trip(client, headers, name="T"):
    r = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert r.status_code == 200
    return r.json()


async def mk_group(client, headers, name="G"):
    r = await client.post("/api/groups/", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.json()


async def invite_to_group_and_accept(client, admin, invitee, group_id, email, role="member"):
    r = await client.post(
        f"/api/groups/{group_id}/invite",
        json={"email": email, "role": role},
        headers=admin,
    )
    assert r.status_code == 201
    pending = (await client.get("/api/groups/invitations/pending", headers=invitee)).json()
    mid = [p["id"] for p in pending if p["group_id"] == group_id][0]
    await client.post(f"/api/groups/invitations/{mid}/accept", headers=invitee)
    return mid


@pytest.mark.asyncio
async def test_full_group_lifecycle(client, auth_headers, second_auth_headers):
    # Alice creates group
    g = await mk_group(client, auth_headers, "Rome Crew")
    # Invite bob as member
    mid_bob = await invite_to_group_and_accept(
        client, auth_headers, second_auth_headers, g["id"], "bob@test.com"
    )
    # Alice attaches her trip
    trip = await mk_trip(client, auth_headers, "Rome 2026")
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    # Bob (group member) can see the trip
    group_trips = (await client.get(f"/api/groups/{g['id']}/trips", headers=second_auth_headers)).json()
    assert any(t["id"] == trip["id"] for t in group_trips)

    # Alice ingests an idea; it shows up in group library for Bob too
    await client.post(
        f"/api/trips/{trip['id']}/ingest",
        json={"text": "Pantheon"},
        headers=auth_headers,
    )
    lib_bob = (await client.get(f"/api/groups/{g['id']}/ideas", headers=second_auth_headers)).json()
    assert any(i["title"] == "Pantheon" for i in lib_bob)

    # Promote Bob to admin
    r = await client.patch(
        f"/api/groups/{g['id']}/members/{mid_bob}/role",
        json={"role": "admin"},
        headers=auth_headers,
    )
    assert r.status_code == 200

    # Now Bob can also invite — but not detach Alice's trip since he isn't a trip admin.
    # Yet current detach policy only requires group admin:
    r = await client.delete(
        f"/api/groups/{g['id']}/trips/{trip['id']}", headers=second_auth_headers
    )
    assert r.status_code == 204

    # Library no longer shows Rome ideas since trip is detached
    lib = (await client.get(f"/api/groups/{g['id']}/ideas", headers=second_auth_headers)).json()
    assert lib == []

    # Alice deletes the group; trip survives
    r = await client.delete(f"/api/groups/{g['id']}", headers=auth_headers)
    assert r.status_code == 204
    detail = await client.get(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_detach_removes_ideas_from_library(client, auth_headers):
    g = await mk_group(client, auth_headers)
    trip = await mk_trip(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/ingest", json={"text": "Pantheon"}, headers=auth_headers)
    assert (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json()

    await client.delete(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    assert (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json() == []


@pytest.mark.asyncio
async def test_trip_delete_while_attached(client, auth_headers):
    g = await mk_group(client, auth_headers)
    trip = await mk_trip(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    await client.delete(f"/api/trips/{trip['id']}", headers=auth_headers)
    trips_in_group = (await client.get(f"/api/groups/{g['id']}/trips", headers=auth_headers)).json()
    assert all(t["id"] != trip["id"] for t in trips_in_group)


@pytest.mark.asyncio
async def test_group_idor(client, auth_headers, second_auth_headers):
    """User in group A cannot read group B's data."""
    a = await mk_group(client, auth_headers, "A")
    b = await mk_group(client, second_auth_headers, "B")
    for path in ["", "/members", "/ideas", "/tags", "/trips"]:
        r = await client.get(f"/api/groups/{b['id']}{path}", headers=auth_headers)
        assert r.status_code == 403, f"expected 403 on {path}"


@pytest.mark.asyncio
async def test_removed_member_loses_read_access(
    client, auth_headers, second_auth_headers
):
    g = await mk_group(client, auth_headers)
    mid = await invite_to_group_and_accept(
        client, auth_headers, second_auth_headers, g["id"], "bob@test.com"
    )
    # data in group
    trip = await mk_trip(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/ingest", json={"text": "X"}, headers=auth_headers)
    # remove bob
    await client.delete(f"/api/groups/{g['id']}/members/{mid}", headers=auth_headers)
    # Bob can no longer see the group library
    r = await client.get(f"/api/groups/{g['id']}/ideas", headers=second_auth_headers)
    assert r.status_code == 403
    # But Alice's data still intact
    r = await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)
    assert len(r.json()) == 1
