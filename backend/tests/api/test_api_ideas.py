"""API tests for ideas.py — idea tags and cross-trip copy."""

import pytest
from httpx import AsyncClient
from tests.conftest import create_trip, invite_and_accept


async def _seed_idea(client, auth_headers, trip_id):
    """Ingest text to create at least one idea bin item, return its ID."""
    resp = await client.post(f"/api/trips/{trip_id}/ingest", headers=auth_headers, json={
        "text": "Visit the Colosseum",
    })
    assert resp.status_code == 200
    ideas = resp.json()
    assert len(ideas) >= 1
    return ideas[0]["id"]


# ── GET /api/ideas/{idea_id}/tags ──────────────────────────────────────────

async def test_list_idea_tags_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    idea_id = await _seed_idea(client, auth_headers, trip["id"])

    # Test 1a - GET - 200 OK - No tags initially
    resp = await client.get(f"/api/ideas/{idea_id}/tags", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Test 1b - GET - 404 Not Found - Non-existent idea
    resp = await client.get("/api/ideas/999999/tags", headers=auth_headers)
    assert resp.status_code == 404

    # Test 1c - GET - 403 Forbidden - Non-member
    resp = await client.get(f"/api/ideas/{idea_id}/tags", headers=second_auth_headers)
    assert resp.status_code == 403


# ── PUT /api/ideas/{idea_id}/tags ──────────────────────────────────────────

async def test_set_idea_tags_put(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    idea_id = await _seed_idea(client, auth_headers, trip["id"])

    # Test 2a - PUT - 200 OK - Set tags
    resp = await client.put(f"/api/ideas/{idea_id}/tags", headers=auth_headers, json={
        "tags": ["culture", "history"],
    })
    assert resp.status_code == 200
    assert set(resp.json()) == {"culture", "history"}

    # Test 2b - PUT - 200 OK - Replace tags entirely
    resp = await client.put(f"/api/ideas/{idea_id}/tags", headers=auth_headers, json={
        "tags": ["food"],
    })
    assert resp.status_code == 200
    assert resp.json() == ["food"]

    # Test 2c - PUT - 404 Not Found - Non-existent idea
    resp = await client.put("/api/ideas/999999/tags", headers=auth_headers, json={"tags": ["x"]})
    assert resp.status_code == 404

    # Test 2d - PUT - 403 Forbidden - View-only member cannot set tags
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only")
    resp = await client.put(f"/api/ideas/{idea_id}/tags", headers=second_auth_headers, json={"tags": ["hack"]})
    assert resp.status_code == 403


# ── POST /api/ideas/{idea_id}/copy ─────────────────────────────────────────

async def test_copy_idea_to_trip_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip1 = await create_trip(client, auth_headers, name="Trip 1")
    trip2 = await create_trip(client, auth_headers, name="Trip 2")
    idea_id = await _seed_idea(client, auth_headers, trip1["id"])

    # Test 3a - POST - 200 OK - Copy idea to another trip
    resp = await client.post(f"/api/ideas/{idea_id}/copy", headers=auth_headers, json={
        "target_trip_id": trip2["id"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["trip_id"] == trip2["id"]
    assert data.get("origin_idea_id") is not None

    # Test 3b - POST - 404 Not Found - Non-existent idea
    resp = await client.post("/api/ideas/999999/copy", headers=auth_headers, json={
        "target_trip_id": trip2["id"],
    })
    assert resp.status_code == 404

    # Test 3c - POST - 403 Forbidden - Non-member of target trip
    resp = await client.post(f"/api/ideas/{idea_id}/copy", headers=second_auth_headers, json={
        "target_trip_id": trip2["id"],
    })
    assert resp.status_code == 403
