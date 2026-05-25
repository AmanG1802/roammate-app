"""API tests for notifications.py — list, unread-count, mark-read, mark-all-read."""

import pytest
from httpx import AsyncClient
from tests.conftest import create_trip

NO_AUTH = {"Cookie": "", "Authorization": ""}


# ── GET /api/notifications ─────────────────────────────────────────────────

async def test_list_notifications_get(client: AsyncClient, auth_headers: dict):
    # Test 1a - GET - 200 OK - Empty notifications initially
    resp = await client.get("/api/notifications", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # Test 1b - GET - 200 OK - Returns notifications after trip creation
    await create_trip(client, auth_headers, name="Notif Trip")
    resp = await client.get("/api/notifications", headers=auth_headers)
    assert resp.status_code == 200
    notes = resp.json()
    assert len(notes) >= 1

    # Test 1c - GET - 200 OK - Pagination with limit
    resp = await client.get("/api/notifications?limit=1", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) <= 1

    # Test 1d - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/notifications", headers=NO_AUTH)
    assert resp.status_code == 401


# ── GET /api/notifications/unread-count ────────────────────────────────────

async def test_unread_count_get(client: AsyncClient, auth_headers: dict):
    # Test 2a - GET - 200 OK - Returns unread count
    resp = await client.get("/api/notifications/unread-count", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "unread" in data
    assert isinstance(data["unread"], int)

    # Test 2b - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/notifications/unread-count", headers=NO_AUTH)
    assert resp.status_code == 401


# ── POST /api/notifications/{notification_id}/read ─────────────────────────

async def test_mark_read_post(client: AsyncClient, auth_headers: dict):
    await create_trip(client, auth_headers, name="Notif Trip")
    resp = await client.get("/api/notifications", headers=auth_headers)
    notes = resp.json()

    if notes:
        nid = notes[0]["id"]

        # Test 3a - POST - 204 No Content - Mark notification as read
        resp = await client.post(f"/api/notifications/{nid}/read", headers=auth_headers)
        assert resp.status_code == 204

        # Test 3b - POST - 204 No Content - Idempotent re-mark
        resp = await client.post(f"/api/notifications/{nid}/read", headers=auth_headers)
        assert resp.status_code == 204

    # Test 3c - POST - 404 Not Found - Invalid notification id
    resp = await client.post("/api/notifications/999999/read", headers=auth_headers)
    assert resp.status_code == 404


# ── POST /api/notifications/mark-all-read ──────────────────────────────────

async def test_mark_all_read_post(client: AsyncClient, auth_headers: dict):
    await create_trip(client, auth_headers, name="Notif Trip 1")
    await create_trip(client, auth_headers, name="Notif Trip 2")

    # Test 4a - POST - 204 No Content - Mark all as read
    resp = await client.post("/api/notifications/mark-all-read", headers=auth_headers)
    assert resp.status_code == 204

    # Verify unread count is 0
    resp = await client.get("/api/notifications/unread-count", headers=auth_headers)
    assert resp.json()["unread"] == 0

    # Test 4b - POST - 204 No Content - Idempotent when no unreads
    resp = await client.post("/api/notifications/mark-all-read", headers=auth_headers)
    assert resp.status_code == 204
