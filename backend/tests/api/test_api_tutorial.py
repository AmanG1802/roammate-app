"""API tests for tutorial.py — status, start, step, skip, complete, replay, reset, delete-trip."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock

NO_AUTH = {"Cookie": "", "Authorization": ""}


def _mock_seed():
    """Mock tutorial seed to avoid DB complexity."""
    from app.models.all_models import Trip
    trip = MagicMock(spec=Trip)
    trip.id = 999
    trip.is_tutorial = True
    trip.is_tutorial_completed = False
    return AsyncMock(return_value=trip)


def _mock_find_existing(trip=None):
    return AsyncMock(return_value=trip)


def _mock_delete():
    return AsyncMock(return_value=None)


# ── GET /api/tutorial/status ───────────────────────────────────────────────

async def test_tutorial_get_status_get(client: AsyncClient, auth_headers: dict):
    # Test 1a - GET - 200 OK - Returns tutorial status
    with patch("app.api.endpoints.tutorial.find_existing_tutorial_trip", _mock_find_existing()):
        resp = await client.get("/api/tutorial/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "step" in data
        assert "platform" in data

    # Test 1b - GET - 200 OK - Platform header (iOS)
    with patch("app.api.endpoints.tutorial.find_existing_tutorial_trip", _mock_find_existing()):
        resp = await client.get("/api/tutorial/status", headers={
            **auth_headers, "X-Client-Platform": "ios",
        })
        assert resp.status_code == 200
        assert resp.json()["platform"] == "ios"

    # Test 1c - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/tutorial/status", headers=NO_AUTH)
    assert resp.status_code == 401


# ── POST /api/tutorial/start ──────────────────────────────────────────────

async def test_tutorial_start_post(client: AsyncClient, auth_headers: dict):
    # Test 2a - POST - 200 OK - Start tutorial
    with patch("app.api.endpoints.tutorial.find_existing_tutorial_trip", _mock_find_existing()), \
         patch("app.api.endpoints.tutorial.seed_tutorial_trip", _mock_seed()):
        resp = await client.post("/api/tutorial/start", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"
        assert data["trip_id"] is not None

    # Test 2b - POST - 401 Unauthorized - No auth
    resp = await client.post("/api/tutorial/start", headers=NO_AUTH)
    assert resp.status_code == 401


# ── PATCH /api/tutorial/step ──────────────────────────────────────────────

async def test_tutorial_patch_step_patch(client: AsyncClient, auth_headers: dict):
    # Test 3a - PATCH - 200 OK - Update step
    with patch("app.api.endpoints.tutorial.find_existing_tutorial_trip", _mock_find_existing()):
        resp = await client.patch("/api/tutorial/step", headers=auth_headers, json={"step": 3})
        assert resp.status_code == 200
        assert resp.json()["step"] == 3

    # Test 3b - PATCH - 422 Unprocessable Entity - Step out of range
    resp = await client.patch("/api/tutorial/step", headers=auth_headers, json={"step": -1})
    assert resp.status_code == 422

    # Test 3c - PATCH - 422 Unprocessable Entity - Missing step
    resp = await client.patch("/api/tutorial/step", headers=auth_headers, json={})
    assert resp.status_code == 422


# ── POST /api/tutorial/skip ───────────────────────────────────────────────

async def test_tutorial_skip_post(client: AsyncClient, auth_headers: dict):
    # Test 4a - POST - 200 OK - Skip tutorial
    with patch("app.api.endpoints.tutorial.find_existing_tutorial_trip", _mock_find_existing()):
        resp = await client.post("/api/tutorial/skip", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "skipped"


# ── POST /api/tutorial/complete ────────────────────────────────────────────

async def test_tutorial_complete_post(client: AsyncClient, auth_headers: dict):
    # Test 5a - POST - 200 OK - Complete tutorial
    with patch("app.api.endpoints.tutorial.find_existing_tutorial_trip", _mock_find_existing()):
        resp = await client.post("/api/tutorial/complete", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"


# ── POST /api/tutorial/replay ─────────────────────────────────────────────

async def test_tutorial_replay_post(client: AsyncClient, auth_headers: dict):
    # Test 6a - POST - 200 OK - Replay tutorial
    with patch("app.api.endpoints.tutorial.seed_tutorial_trip", _mock_seed()):
        resp = await client.post("/api/tutorial/replay", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"
        assert resp.json()["step"] == 1


# ── POST /api/tutorial/reset ──────────────────────────────────────────────

async def test_tutorial_reset_post(client: AsyncClient, auth_headers: dict):
    # Test 7a - POST - 200 OK - Reset tutorial
    with patch("app.api.endpoints.tutorial.delete_tutorial_trip", _mock_delete()):
        resp = await client.post("/api/tutorial/reset", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_started"
        assert resp.json()["step"] == 0


# ── DELETE /api/tutorial/trip ──────────────────────────────────────────────

async def test_tutorial_delete_trip_delete(client: AsyncClient, auth_headers: dict):
    # Test 8a - DELETE - 200 OK - Delete tutorial trip
    with patch("app.api.endpoints.tutorial.delete_tutorial_trip", _mock_delete()):
        resp = await client.delete("/api/tutorial/trip", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["trip_id"] is None

    # Test 8b - DELETE - 401 Unauthorized - No auth
    resp = await client.delete("/api/tutorial/trip", headers=NO_AUTH)
    assert resp.status_code == 401
