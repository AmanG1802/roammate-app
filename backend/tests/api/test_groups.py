"""HTTP integration tests for `/api/groups/*` (group CRUD, members, invitations, trips)."""
import pytest
from httpx import AsyncClient


# ── helpers ──────────────────────────────────────────────────────────────────

async def create_trip(client: AsyncClient, headers: dict, name: str = "Trip") -> dict:
    resp = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def create_group(client: AsyncClient, headers: dict, name: str = "Crew") -> dict:
    resp = await client.post("/api/groups/", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def invite_group(client, admin_headers, group_id, email, role="member"):
    return await client.post(
        f"/api/groups/{group_id}/invite",
        json={"email": email, "role": role},
        headers=admin_headers,
    )


async def invite_and_accept_group(
    client, admin_headers, invitee_headers, group_id, email, role="member"
) -> int:
    r = await invite_group(client, admin_headers, group_id, email, role)
    assert r.status_code == 201, r.text
    pending = (await client.get("/api/groups/invitations/pending", headers=invitee_headers)).json()
    mid = [p["id"] for p in pending if p["group_id"] == group_id][0]
    r = await client.post(f"/api/groups/invitations/{mid}/accept", headers=invitee_headers)
    assert r.status_code == 200, r.text
    return mid


# ── Create ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_group_requires_auth(client):
    r = await client.post("/api/groups/", json={"name": "X"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_group_basic(client, auth_headers):
    g = await create_group(client, auth_headers, "Roma Squad")
    assert g["name"] == "Roma Squad"
    assert g["my_role"] == "admin"
    assert "owner_id" in g and "created_at" in g


@pytest.mark.asyncio
async def test_create_group_strips_whitespace(client, auth_headers):
    g = await create_group(client, auth_headers, "   Roma   ")
    assert g["name"] == "Roma"


@pytest.mark.asyncio
async def test_create_group_whitespace_only_rejected(client, auth_headers):
    r = await client.post("/api/groups/", json={"name": "   "}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_group_emits_group_created_notification(client, auth_headers):
    await create_group(client, auth_headers, "Notify Me")
    inbox = (await client.get("/api/notifications/", headers=auth_headers)).json()
    assert any(n["type"] == "group_created" for n in inbox)


@pytest.mark.asyncio
async def test_create_group_adds_creator_as_admin(client, auth_headers):
    g = await create_group(client, auth_headers, "Solo")
    members = (await client.get(f"/api/groups/{g['id']}/members", headers=auth_headers)).json()
    assert len(members) == 1
    assert members[0]["role"] == "admin"
    assert members[0]["status"] == "accepted"


# ── Read / list ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_my_groups(client, auth_headers):
    await create_group(client, auth_headers, "G1")
    await create_group(client, auth_headers, "G2")
    resp = (await client.get("/api/groups/", headers=auth_headers)).json()
    assert len(resp) == 2
    assert all(g["my_role"] == "admin" for g in resp)


@pytest.mark.asyncio
async def test_list_my_groups_counts(client, auth_headers):
    g = await create_group(client, auth_headers, "Counts")
    trip = await create_trip(client, auth_headers, "T")
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    row = (await client.get("/api/groups/", headers=auth_headers)).json()[0]
    assert row["member_count"] == 1
    assert row["trip_count"] == 1


@pytest.mark.asyncio
async def test_list_my_groups_isolation(client, auth_headers, second_auth_headers):
    await create_group(client, auth_headers, "Alice")
    await create_group(client, second_auth_headers, "Bob")
    alice = (await client.get("/api/groups/", headers=auth_headers)).json()
    bob = (await client.get("/api/groups/", headers=second_auth_headers)).json()
    assert len(alice) == 1 and alice[0]["name"] == "Alice"
    assert len(bob) == 1 and bob[0]["name"] == "Bob"


@pytest.mark.asyncio
async def test_get_group_detail_by_member(client, auth_headers):
    g = await create_group(client, auth_headers)
    r = await client.get(f"/api/groups/{g['id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["my_role"] == "admin"


@pytest.mark.asyncio
async def test_get_group_detail_by_non_member_forbidden(
    client, auth_headers, second_auth_headers
):
    g = await create_group(client, auth_headers, "Private")
    r = await client.get(f"/api/groups/{g['id']}", headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_group_by_invited_but_not_accepted_forbidden(
    client, auth_headers, second_auth_headers
):
    g = await create_group(client, auth_headers)
    await invite_group(client, auth_headers, g["id"], "bob@test.com")
    r = await client.get(f"/api/groups/{g['id']}", headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_group_unknown_is_forbidden(client, auth_headers):
    # _require_group_member returns 403 even for missing group
    r = await client.get("/api/groups/9999", headers=auth_headers)
    assert r.status_code == 403


# ── Update ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_group_name_by_admin(client, auth_headers):
    g = await create_group(client, auth_headers, "Old")
    r = await client.patch(f"/api/groups/{g['id']}", json={"name": "New"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "New"


@pytest.mark.asyncio
async def test_patch_group_by_non_admin_forbidden(
    client, auth_headers, second_auth_headers
):
    g = await create_group(client, auth_headers)
    await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    r = await client.patch(f"/api/groups/{g['id']}", json={"name": "N"}, headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_patch_group_by_non_member_forbidden(
    client, auth_headers, second_auth_headers
):
    g = await create_group(client, auth_headers)
    r = await client.patch(f"/api/groups/{g['id']}", json={"name": "N"}, headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_patch_group_empty_name_is_noop(client, auth_headers):
    g = await create_group(client, auth_headers, "Keep")
    r = await client.patch(f"/api/groups/{g['id']}", json={"name": "   "}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Keep"


# ── Delete ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_group_by_admin(client, auth_headers):
    g = await create_group(client, auth_headers, "Doomed")
    r = await client.delete(f"/api/groups/{g['id']}", headers=auth_headers)
    assert r.status_code == 204
    # Post-delete, the admin can no longer see it
    r = await client.get(f"/api/groups/{g['id']}", headers=auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_group_by_non_admin_forbidden(
    client, auth_headers, second_auth_headers
):
    g = await create_group(client, auth_headers)
    await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    r = await client.delete(f"/api/groups/{g['id']}", headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_group_detaches_trips(client, auth_headers):
    g = await create_group(client, auth_headers, "Temp")
    trip = await create_trip(client, auth_headers, "Survivor")
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    await client.delete(f"/api/groups/{g['id']}", headers=auth_headers)
    # Trip still exists
    detail = await client.get(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert detail.status_code == 200


# ── Invitations ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invite_creates_pending(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    r = await invite_group(client, auth_headers, g["id"], "bob@test.com")
    assert r.status_code == 201
    pending = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    assert len(pending) == 1
    assert pending[0]["group"]["name"] == "Crew"
    assert pending[0]["role"] == "member"
    assert pending[0]["inviter"]["email"] == "alice@test.com"


@pytest.mark.asyncio
async def test_pending_empty(client, second_auth_headers):
    r = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    assert r == []


@pytest.mark.asyncio
async def test_invite_unknown_email_404(client, auth_headers):
    g = await create_group(client, auth_headers)
    r = await invite_group(client, auth_headers, g["id"], "nobody@nowhere.com")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_invite_already_member_409(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    r = await invite_group(client, auth_headers, g["id"], "bob@test.com")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_invite_already_invited_409(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    await invite_group(client, auth_headers, g["id"], "bob@test.com")
    r = await invite_group(client, auth_headers, g["id"], "bob@test.com")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_invite_invalid_role_422(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    r = await invite_group(client, auth_headers, g["id"], "bob@test.com", role="supreme")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_invite_default_role_member(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    r = await client.post(
        f"/api/groups/{g['id']}/invite",
        json={"email": "bob@test.com"},  # no role
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["role"] == "member"


@pytest.mark.asyncio
async def test_invite_by_non_admin_403(
    client, auth_headers, second_auth_headers, third_auth_headers
):
    g = await create_group(client, auth_headers)
    await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    r = await invite_group(client, second_auth_headers, g["id"], "carol@test.com")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_invite_by_non_member_403(
    client, auth_headers, second_auth_headers, third_auth_headers
):
    g = await create_group(client, auth_headers)
    r = await invite_group(client, second_auth_headers, g["id"], "carol@test.com")
    assert r.status_code == 403


# ── Accept / decline ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_accept_invitation_succeeds(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    await invite_group(client, auth_headers, g["id"], "bob@test.com")
    pending = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    r = await client.post(
        f"/api/groups/invitations/{pending[0]['id']}/accept",
        headers=second_auth_headers,
    )
    assert r.status_code == 200
    bob_groups = (await client.get("/api/groups/", headers=second_auth_headers)).json()
    assert any(x["name"] == "Crew" for x in bob_groups)


@pytest.mark.asyncio
async def test_accept_nonexistent_404(client, auth_headers):
    r = await client.post("/api/groups/invitations/9999/accept", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_accept_foreign_invitation_404(
    client, auth_headers, second_auth_headers, third_auth_headers
):
    g = await create_group(client, auth_headers)
    await invite_group(client, auth_headers, g["id"], "bob@test.com")
    pending = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    # Carol tries to accept Bob's invite
    r = await client.post(
        f"/api/groups/invitations/{pending[0]['id']}/accept",
        headers=third_auth_headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_accept_already_accepted_404(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    mid = await invite_and_accept_group(
        client, auth_headers, second_auth_headers, g["id"], "bob@test.com"
    )
    r = await client.post(f"/api/groups/invitations/{mid}/accept", headers=second_auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_accept_fanout_notifications(
    client, auth_headers, second_auth_headers, third_auth_headers
):
    g = await create_group(client, auth_headers)
    await invite_and_accept_group(
        client, auth_headers, third_auth_headers, g["id"], "carol@test.com"
    )
    # Now bob accepts — alice + carol should get joined-user notification, bob gets self.
    await invite_group(client, auth_headers, g["id"], "bob@test.com")
    pending = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    await client.post(
        f"/api/groups/invitations/{pending[0]['id']}/accept",
        headers=second_auth_headers,
    )

    bob_inbox = (await client.get("/api/notifications/", headers=second_auth_headers)).json()
    assert any(n["type"] == "group_invite_accepted" and n["payload"].get("self") for n in bob_inbox)
    alice_inbox = (await client.get("/api/notifications/", headers=auth_headers)).json()
    assert any(
        n["type"] == "group_invite_accepted" and n["payload"].get("joined_user_name")
        for n in alice_inbox
    )


@pytest.mark.asyncio
async def test_decline_invitation(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    await invite_group(client, auth_headers, g["id"], "bob@test.com")
    pending = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    r = await client.delete(
        f"/api/groups/invitations/{pending[0]['id']}/decline",
        headers=second_auth_headers,
    )
    assert r.status_code == 204
    remaining = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    assert remaining == []


@pytest.mark.asyncio
async def test_decline_nonexistent_404(client, auth_headers):
    r = await client.delete("/api/groups/invitations/9999/decline", headers=auth_headers)
    assert r.status_code == 404


# ── Members list ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_group_members_by_member(client, auth_headers):
    g = await create_group(client, auth_headers)
    r = await client.get(f"/api/groups/{g['id']}/members", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_list_group_members_by_non_member_403(
    client, auth_headers, second_auth_headers
):
    g = await create_group(client, auth_headers)
    r = await client.get(f"/api/groups/{g['id']}/members", headers=second_auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_members_includes_invited(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    await invite_group(client, auth_headers, g["id"], "bob@test.com")
    members = (await client.get(f"/api/groups/{g['id']}/members", headers=auth_headers)).json()
    statuses = sorted(m["status"] for m in members)
    assert statuses == ["accepted", "invited"]


# ── Role changes ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_member_role_by_admin(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    mid = await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    r = await client.patch(
        f"/api/groups/{g['id']}/members/{mid}/role",
        json={"role": "admin"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_update_member_role_by_non_admin_403(
    client, auth_headers, second_auth_headers, third_auth_headers
):
    g = await create_group(client, auth_headers)
    mid_bob = await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    await invite_and_accept_group(client, auth_headers, third_auth_headers, g["id"], "carol@test.com")
    r = await client.patch(
        f"/api/groups/{g['id']}/members/{mid_bob}/role",
        json={"role": "admin"},
        headers=third_auth_headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_update_member_role_invalid_422(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    mid = await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    r = await client.patch(
        f"/api/groups/{g['id']}/members/{mid}/role",
        json={"role": "supreme"},
        headers=auth_headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_role_nonexistent_member_404(client, auth_headers):
    g = await create_group(client, auth_headers)
    r = await client.patch(
        f"/api/groups/{g['id']}/members/9999/role",
        json={"role": "admin"},
        headers=auth_headers,
    )
    assert r.status_code == 404


# ── Remove member ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_remove_member_by_admin(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    mid = await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    r = await client.delete(f"/api/groups/{g['id']}/members/{mid}", headers=auth_headers)
    assert r.status_code == 204
    # Bob no longer sees the group
    bob_groups = (await client.get("/api/groups/", headers=second_auth_headers)).json()
    assert all(x["id"] != g["id"] for x in bob_groups)


@pytest.mark.asyncio
async def test_remove_member_by_non_admin_403(
    client, auth_headers, second_auth_headers, third_auth_headers
):
    g = await create_group(client, auth_headers)
    mid_bob = await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    await invite_and_accept_group(client, auth_headers, third_auth_headers, g["id"], "carol@test.com")
    r = await client.delete(
        f"/api/groups/{g['id']}/members/{mid_bob}", headers=third_auth_headers
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_remove_self_400(client, auth_headers):
    g = await create_group(client, auth_headers)
    my_mid = (await client.get(f"/api/groups/{g['id']}/members", headers=auth_headers)).json()[0]["id"]
    r = await client.delete(f"/api/groups/{g['id']}/members/{my_mid}", headers=auth_headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_remove_nonexistent_member_404(client, auth_headers):
    g = await create_group(client, auth_headers)
    r = await client.delete(f"/api/groups/{g['id']}/members/9999", headers=auth_headers)
    assert r.status_code == 404


# ── Trip attach / detach ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_attach_trip_as_admin(client, auth_headers):
    g = await create_group(client, auth_headers)
    trip = await create_trip(client, auth_headers, "T")
    r = await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    assert r.status_code == 200
    listed = (await client.get(f"/api/groups/{g['id']}/trips", headers=auth_headers)).json()
    assert any(t["id"] == trip["id"] for t in listed)


@pytest.mark.asyncio
async def test_attach_trip_is_idempotent(client, auth_headers):
    g = await create_group(client, auth_headers)
    trip = await create_trip(client, auth_headers, "T")
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    r = await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_attach_trip_requires_trip_admin(client, auth_headers, second_auth_headers):
    bob_group = await create_group(client, second_auth_headers, "Bob's")
    alice_trip = await create_trip(client, auth_headers, "Alice T")
    r = await client.post(
        f"/api/groups/{bob_group['id']}/trips/{alice_trip['id']}",
        headers=second_auth_headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_attach_trip_by_non_group_admin_403(
    client, auth_headers, second_auth_headers
):
    g = await create_group(client, auth_headers)
    await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    bob_trip = await create_trip(client, second_auth_headers, "Bob T")
    r = await client.post(
        f"/api/groups/{g['id']}/trips/{bob_trip['id']}", headers=second_auth_headers
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_detach_trip(client, auth_headers):
    g = await create_group(client, auth_headers)
    trip = await create_trip(client, auth_headers, "T")
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    r = await client.delete(
        f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers
    )
    assert r.status_code == 204
    listed = (await client.get(f"/api/groups/{g['id']}/trips", headers=auth_headers)).json()
    assert listed == []


@pytest.mark.asyncio
async def test_detach_trip_not_attached_404(client, auth_headers):
    g = await create_group(client, auth_headers)
    trip = await create_trip(client, auth_headers, "Loose")
    r = await client.delete(
        f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_detach_by_non_group_admin_403(client, auth_headers, second_auth_headers):
    g = await create_group(client, auth_headers)
    trip = await create_trip(client, auth_headers, "T")
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    r = await client.delete(
        f"/api/groups/{g['id']}/trips/{trip['id']}", headers=second_auth_headers
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_attach_trip_notifies_other_group_members(
    client, auth_headers, second_auth_headers
):
    g = await create_group(client, auth_headers)
    await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    trip = await create_trip(client, auth_headers, "Shared Trip")
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    bob_inbox = (await client.get("/api/notifications/", headers=second_auth_headers)).json()
    assert any(n["type"] == "group_trip_attached" for n in bob_inbox)


@pytest.mark.asyncio
async def test_remove_member_notifies_self_and_remaining(
    client, auth_headers, second_auth_headers, third_auth_headers
):
    g = await create_group(client, auth_headers)
    mid_bob = await invite_and_accept_group(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    await invite_and_accept_group(client, auth_headers, third_auth_headers, g["id"], "carol@test.com")
    await client.delete(f"/api/groups/{g['id']}/members/{mid_bob}", headers=auth_headers)
    bob_inbox = (await client.get("/api/notifications/", headers=second_auth_headers)).json()
    assert any(n["type"] == "group_member_removed" and n["payload"].get("self")
               for n in bob_inbox)
    carol_inbox = (await client.get("/api/notifications/", headers=third_auth_headers)).json()
    assert any(n["type"] == "group_member_removed" and n["payload"].get("removed_user_name")
               for n in carol_inbox)


# ── Auth sweep ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("method,url", [
    ("GET", "/api/groups/"),
    ("POST", "/api/groups/"),
    ("GET", "/api/groups/invitations/pending"),
    ("GET", "/api/groups/1"),
    ("PATCH", "/api/groups/1"),
    ("DELETE", "/api/groups/1"),
    ("GET", "/api/groups/1/members"),
    ("POST", "/api/groups/1/invite"),
    ("GET", "/api/groups/1/trips"),
])
async def test_group_routes_require_auth(client, method, url):
    r = await client.request(method, url, json={} if method in {"POST", "PATCH"} else None)
    assert r.status_code == 401
