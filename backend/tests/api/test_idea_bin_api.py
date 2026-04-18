"""Tests for idea bin API endpoints (/api/trips/{id}/ideas, /ingest)."""
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


async def test_ingest_success(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(return_value={
            "name": "Colosseum",
            "place_id": "c1",
            "geometry": {"location": {"lat": 41.89, "lng": 12.49}},
        }),
    ):
        resp = await client.post(
            f"/api/trips/{trip['id']}/ingest",
            json={"text": "Colosseum"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Colosseum"


async def test_ingest_added_by_first_name(client: AsyncClient, auth_headers):
    # Alice Smith → first name "Alice"
    trip = await create_trip(client, auth_headers)
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        resp = await client.post(
            f"/api/trips/{trip['id']}/ingest",
            json={"text": "Something"},
            headers=auth_headers,
        )
    assert resp.json()[0]["added_by"] == "Alice"


async def test_ingest_comma_and_newline(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        resp = await client.post(
            f"/api/trips/{trip['id']}/ingest",
            json={"text": "A, B\nC"},
            headers=auth_headers,
        )
    titles = sorted(i["title"] for i in resp.json())
    assert titles == ["A", "B", "C"]


async def test_ingest_empty(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/ingest",
        json={"text": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_ingest_whitespace_filtered(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        resp = await client.post(
            f"/api/trips/{trip['id']}/ingest",
            json={"text": "  \n , \n   "},
            headers=auth_headers,
        )
    assert resp.json() == []


async def test_ingest_google_maps_failure_falls_back(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        resp = await client.post(
            f"/api/trips/{trip['id']}/ingest",
            json={"text": "Eiffel"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json()[0]["title"] == "Eiffel"
    assert resp.json()[0]["place_id"] is None


async def test_ingest_source_url_persisted(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        resp = await client.post(
            f"/api/trips/{trip['id']}/ingest",
            json={"text": "A", "source_url": "https://example.com/x"},
            headers=auth_headers,
        )
    assert resp.json()[0]["url_source"] == "https://example.com/x"


async def test_ingest_non_member_forbidden(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/ingest",
        json={"text": "X"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


# ── Idea CRUD ────────────────────────────────────────────────────────────────

async def _seed_idea(client, headers, trip_id):
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        resp = await client.post(
            f"/api/trips/{trip_id}/ingest",
            json={"text": "Museum"},
            headers=headers,
        )
    return resp.json()[0]


async def test_get_ideas(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await _seed_idea(client, auth_headers, trip["id"])
    resp = await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_get_ideas_non_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(
        f"/api/trips/{trip['id']}/ideas", headers=second_auth_headers
    )
    assert resp.status_code == 403


async def test_patch_idea_title_and_time_hint(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _seed_idea(client, auth_headers, trip["id"])
    resp = await client.patch(
        f"/api/trips/{trip['id']}/ideas/{idea['id']}",
        json={"title": "Updated", "time_hint": "3pm"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"
    assert resp.json()["time_hint"] == "3pm"


async def test_patch_idea_non_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    idea = await _seed_idea(client, auth_headers, trip["id"])
    resp = await client.patch(
        f"/api/trips/{trip['id']}/ideas/{idea['id']}",
        json={"title": "X"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_patch_idea_wrong_trip(client: AsyncClient, auth_headers):
    trip1 = await create_trip(client, auth_headers, name="T1")
    trip2 = await create_trip(client, auth_headers, name="T2")
    idea = await _seed_idea(client, auth_headers, trip1["id"])
    resp = await client.patch(
        f"/api/trips/{trip2['id']}/ideas/{idea['id']}",
        json={"title": "X"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_delete_idea(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _seed_idea(client, auth_headers, trip["id"])
    resp = await client.delete(
        f"/api/trips/{trip['id']}/ideas/{idea['id']}", headers=auth_headers
    )
    assert resp.status_code == 204
    resp = await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)
    assert resp.json() == []


async def test_delete_idea_nonexistent(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.delete(
        f"/api/trips/{trip['id']}/ideas/9999", headers=auth_headers
    )
    assert resp.status_code == 404


async def test_ingest_then_idea_appears_in_attached_group_library(
    client: AsyncClient, auth_headers
):
    """Ingested ideas must surface in the library of any group the trip is attached to."""
    trip = await create_trip(client, auth_headers)
    g = (await client.post(
        "/api/groups/", json={"name": "Crew"}, headers=auth_headers
    )).json()
    attach = await client.post(
        f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers
    )
    assert attach.status_code in (200, 201, 204)

    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        await client.post(
            f"/api/trips/{trip['id']}/ingest",
            json={"text": "Pantheon"},
            headers=auth_headers,
        )

    lib = await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)
    assert lib.status_code == 200
    titles = [i["title"] for i in lib.json()]
    assert "Pantheon" in titles


# ── Batch vote data in idea bin list ──────────────────────────────────────────

async def test_get_ideas_includes_vote_tallies(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea1 = await _seed_idea(client, auth_headers, trip["id"])
    idea2 = await _seed_idea(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea1['id']}/vote", json={"value": 1}, headers=auth_headers)
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    by_id = {i["id"]: i for i in ideas}
    assert by_id[idea1["id"]]["up"] == 1 and by_id[idea1["id"]]["my_vote"] == 1
    assert by_id[idea2["id"]]["up"] == 0 and by_id[idea2["id"]]["my_vote"] == 0


async def test_get_ideas_my_vote_caller_specific(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com",
        role="view_with_vote",
    )
    idea = await _seed_idea(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=second_auth_headers)

    alice = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    bob = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=second_auth_headers)).json()
    assert alice[0]["my_vote"] == 1
    assert bob[0]["my_vote"] == -1


async def test_get_ideas_empty_bin_returns_empty(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    assert ideas == []
