"""Integration tests for groups: create, invite, accept/decline, attach trip."""
import pytest
from httpx import AsyncClient


async def create_trip(client: AsyncClient, headers: dict, name: str = "Trip") -> dict:
    resp = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert resp.status_code == 200
    return resp.json()


async def create_group(client: AsyncClient, headers: dict, name: str = "Crew") -> dict:
    resp = await client.post("/api/groups/", json={"name": name}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_create_group(client, auth_headers):
    g = await create_group(client, auth_headers, "Roma Squad")
    assert g["name"] == "Roma Squad"
    assert g["my_role"] == "admin"


@pytest.mark.asyncio
async def test_list_my_groups(client, auth_headers):
    await create_group(client, auth_headers, "G1")
    await create_group(client, auth_headers, "G2")
    resp = await client.get("/api/groups/", headers=auth_headers)
    assert resp.status_code == 200
    groups = resp.json()
    assert len(groups) == 2
    assert all(g["my_role"] == "admin" for g in groups)
    assert all(g["member_count"] == 1 for g in groups)


@pytest.mark.asyncio
async def test_group_isolation_between_users(client, auth_headers, second_auth_headers):
    await create_group(client, auth_headers, "Alice Crew")
    await create_group(client, second_auth_headers, "Bob Crew")
    alice = (await client.get("/api/groups/", headers=auth_headers)).json()
    bob = (await client.get("/api/groups/", headers=second_auth_headers)).json()
    assert len(alice) == 1 and alice[0]["name"] == "Alice Crew"
    assert len(bob) == 1 and bob[0]["name"] == "Bob Crew"


@pytest.mark.asyncio
async def test_invite_to_group_creates_pending_invitation(
    client, auth_headers, second_auth_headers
):
    g = await create_group(client, auth_headers, "Invitees")
    r = await client.post(
        f"/api/groups/{g['id']}/invite",
        json={"email": "bob@test.com", "role": "member"},
        headers=auth_headers,
    )
    assert r.status_code == 201

    pending = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    assert len(pending) == 1
    assert pending[0]["group"]["name"] == "Invitees"
    assert pending[0]["role"] == "member"


@pytest.mark.asyncio
async def test_accept_group_invitation(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers, "Accept Crew")
    await client.post(
        f"/api/groups/{g['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    pending = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    member_id = pending[0]["id"]

    r = await client.post(f"/api/groups/invitations/{member_id}/accept", headers=second_auth_headers)
    assert r.status_code == 200

    bob_groups = (await client.get("/api/groups/", headers=second_auth_headers)).json()
    assert any(grp["name"] == "Accept Crew" for grp in bob_groups)


@pytest.mark.asyncio
async def test_decline_group_invitation(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers, "Decline Crew")
    await client.post(
        f"/api/groups/{g['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    pending = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    member_id = pending[0]["id"]

    r = await client.delete(f"/api/groups/invitations/{member_id}/decline", headers=second_auth_headers)
    assert r.status_code == 204

    pending_after = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    assert pending_after == []
    bob_groups = (await client.get("/api/groups/", headers=second_auth_headers)).json()
    assert all(grp["name"] != "Decline Crew" for grp in bob_groups)


@pytest.mark.asyncio
async def test_non_admin_cannot_invite(client, auth_headers, second_auth_headers):
    """Bob accepts membership as a 'member', then tries to invite — should 403."""
    g = await create_group(client, auth_headers, "Hierarchy")
    await client.post(
        f"/api/groups/{g['id']}/invite",
        json={"email": "bob@test.com", "role": "member"},
        headers=auth_headers,
    )
    pending = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    await client.post(f"/api/groups/invitations/{pending[0]['id']}/accept", headers=second_auth_headers)

    r = await client.post(
        f"/api/groups/{g['id']}/invite",
        json={"email": "alice@test.com"},
        headers=second_auth_headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_attach_trip_requires_trip_admin(client, auth_headers, second_auth_headers):
    """Bob is group admin (his own group), but the trip belongs to Alice — attach must 403."""
    bob_group = await create_group(client, second_auth_headers, "Bob Group")
    alice_trip = await create_trip(client, auth_headers, "Alice Trip")

    r = await client.post(
        f"/api/groups/{bob_group['id']}/trips/{alice_trip['id']}",
        headers=second_auth_headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_attach_trip_as_admin_succeeds(client, auth_headers):
    g = await create_group(client, auth_headers, "Trips Crew")
    trip = await create_trip(client, auth_headers, "My Trip")

    r = await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    assert r.status_code == 200

    listed = (await client.get(f"/api/groups/{g['id']}/trips", headers=auth_headers)).json()
    assert any(t["id"] == trip["id"] for t in listed)


@pytest.mark.asyncio
async def test_non_member_cannot_view_group(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers, "Private")
    r = await client.get(f"/api/groups/{g['id']}", headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_group_detaches_trips(client, auth_headers):
    g = await create_group(client, auth_headers, "Disposable")
    trip = await create_trip(client, auth_headers, "Survivor Trip")
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)

    r = await client.delete(f"/api/groups/{g['id']}", headers=auth_headers)
    assert r.status_code == 204

    # Trip still exists for Alice
    detail = await client.get(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert detail.status_code == 200
