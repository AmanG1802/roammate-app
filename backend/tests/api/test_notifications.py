"""/api/notifications/* — list, unread-count, mark-read, mark-all-read."""
import pytest
from httpx import AsyncClient


async def create_trip(client, headers, name="T"):
    r = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def create_n_trips(client, headers, n):
    for i in range(n):
        await create_trip(client, headers, f"T{i}")


# ── Auth ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("method,url", [
    ("GET", "/api/notifications/"),
    ("GET", "/api/notifications/unread-count"),
    ("POST", "/api/notifications/1/read"),
    ("POST", "/api/notifications/mark-all-read"),
])
async def test_notification_routes_require_auth(client, method, url):
    r = await client.request(method, url)
    assert r.status_code == 401


# ── Unread count ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unread_count_zero_initially(client, auth_headers):
    r = await client.get("/api/notifications/unread-count", headers=auth_headers)
    assert r.json() == {"unread": 0}


@pytest.mark.asyncio
async def test_unread_count_ignores_read(client, auth_headers):
    await create_trip(client, auth_headers, "X")
    await client.post("/api/notifications/mark-all-read", headers=auth_headers)
    r = await client.get("/api/notifications/unread-count", headers=auth_headers)
    assert r.json() == {"unread": 0}


@pytest.mark.asyncio
async def test_unread_count_per_user_only(
    client, auth_headers, second_auth_headers
):
    await create_trip(client, auth_headers, "X")  # Alice gets trip_created
    r = await client.get("/api/notifications/unread-count", headers=second_auth_headers)
    assert r.json() == {"unread": 0}


# ── List ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_empty_initially(client, auth_headers):
    r = await client.get("/api/notifications/", headers=auth_headers)
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_contains_own_trip_created(client, auth_headers):
    await create_trip(client, auth_headers, "Solo")
    r = (await client.get("/api/notifications/", headers=auth_headers)).json()
    assert any(n["type"] == "trip_created" for n in r)


@pytest.mark.asyncio
async def test_list_ordered_by_created_desc(client, auth_headers):
    await create_trip(client, auth_headers, "A")
    await create_trip(client, auth_headers, "B")
    items = (await client.get("/api/notifications/", headers=auth_headers)).json()
    # B is newer than A
    ids = [n["id"] for n in items]
    assert ids == sorted(ids, reverse=True)


@pytest.mark.asyncio
async def test_list_limit_caps_results(client, auth_headers):
    await create_n_trips(client, auth_headers, 5)
    r = (await client.get("/api/notifications/?limit=2", headers=auth_headers)).json()
    assert len(r) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [0, 101, -1])
async def test_list_limit_validation(client, auth_headers, bad):
    r = await client.get(f"/api/notifications/?limit={bad}", headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_before_id_paginates(client, auth_headers):
    await create_n_trips(client, auth_headers, 3)
    all_ = (await client.get("/api/notifications/", headers=auth_headers)).json()
    cursor = all_[0]["id"]
    page2 = (await client.get(
        f"/api/notifications/?before_id={cursor}", headers=auth_headers
    )).json()
    assert all(n["id"] < cursor for n in page2)
    assert len(page2) == len(all_) - 1


@pytest.mark.asyncio
async def test_list_includes_actor_summary(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers, "Shared")
    await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    bob_inbox = (await client.get("/api/notifications/", headers=second_auth_headers)).json()
    invite = next(n for n in bob_inbox if n["type"] == "invite_received")
    assert invite["actor"]["email"] == "alice@test.com"


@pytest.mark.asyncio
async def test_list_payload_defaults_to_dict(client, auth_headers):
    await create_trip(client, auth_headers, "X")
    r = (await client.get("/api/notifications/", headers=auth_headers)).json()
    for n in r:
        assert isinstance(n["payload"], dict)


@pytest.mark.asyncio
async def test_list_isolated_between_users(
    client, auth_headers, second_auth_headers
):
    await create_trip(client, auth_headers, "Alice Only")
    bob = (await client.get("/api/notifications/", headers=second_auth_headers)).json()
    assert all(n["type"] != "trip_created" for n in bob)


# ── Mark-read ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_read_decrements_unread(client, auth_headers):
    await create_trip(client, auth_headers, "X")
    inbox = (await client.get("/api/notifications/", headers=auth_headers)).json()
    before = (await client.get("/api/notifications/unread-count", headers=auth_headers)).json()["unread"]
    r = await client.post(f"/api/notifications/{inbox[0]['id']}/read", headers=auth_headers)
    assert r.status_code in (200, 204)
    after = (await client.get("/api/notifications/unread-count", headers=auth_headers)).json()["unread"]
    assert after == before - 1


@pytest.mark.asyncio
async def test_mark_read_idempotent(client, auth_headers):
    await create_trip(client, auth_headers, "X")
    inbox = (await client.get("/api/notifications/", headers=auth_headers)).json()
    target = inbox[0]["id"]
    await client.post(f"/api/notifications/{target}/read", headers=auth_headers)
    first_at = (await client.get("/api/notifications/", headers=auth_headers)).json()
    first_read_at = [n for n in first_at if n["id"] == target][0]["read_at"]
    r = await client.post(f"/api/notifications/{target}/read", headers=auth_headers)
    assert r.status_code in (200, 204)
    second = (await client.get("/api/notifications/", headers=auth_headers)).json()
    second_read_at = [n for n in second if n["id"] == target][0]["read_at"]
    assert first_read_at == second_read_at


@pytest.mark.asyncio
async def test_mark_read_nonexistent_404(client, auth_headers):
    r = await client.post("/api/notifications/9999/read", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_mark_read_another_users_404(
    client, auth_headers, second_auth_headers
):
    await create_trip(client, auth_headers, "X")
    inbox = (await client.get("/api/notifications/", headers=auth_headers)).json()
    r = await client.post(
        f"/api/notifications/{inbox[0]['id']}/read", headers=second_auth_headers
    )
    assert r.status_code == 404


# ── Mark-all-read ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_all_read_zeros_unread(client, auth_headers):
    await create_n_trips(client, auth_headers, 3)
    r = await client.post("/api/notifications/mark-all-read", headers=auth_headers)
    assert r.status_code in (200, 204)
    assert (await client.get("/api/notifications/unread-count", headers=auth_headers)).json() == {"unread": 0}


@pytest.mark.asyncio
async def test_mark_all_read_when_empty_ok(client, auth_headers):
    r = await client.post("/api/notifications/mark-all-read", headers=auth_headers)
    assert r.status_code in (200, 204)


@pytest.mark.asyncio
async def test_mark_all_read_leaves_other_users_alone(
    client, auth_headers, second_auth_headers
):
    await create_trip(client, auth_headers, "Alice")
    await create_trip(client, second_auth_headers, "Bob")
    await client.post("/api/notifications/mark-all-read", headers=auth_headers)
    bob_unread = (await client.get("/api/notifications/unread-count", headers=second_auth_headers)).json()
    assert bob_unread["unread"] >= 1


# ── Fan-out spot-checks ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invite_creates_notification_for_invitee(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers, "Shared")
    await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    inbox = (await client.get("/api/notifications/", headers=second_auth_headers)).json()
    invite = [n for n in inbox if n["type"] == "invite_received"]
    assert invite and invite[0]["payload"]["trip_name"] == "Shared"
