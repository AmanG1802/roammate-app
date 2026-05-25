"""§20 Tutorial & Onboarding — start, step, complete, replay, reset, platform independence,
and canned reply verification.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def test_tutorial_status_default_not_started(client: AsyncClient, auth_headers):
    resp = await client.get("/api/tutorial/status", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "not_started"


async def test_tutorial_start_seeds_trip(client: AsyncClient, auth_headers):
    resp = await client.post("/api/tutorial/start", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["trip_id"] is not None


async def test_tutorial_start_idempotent(client: AsyncClient, auth_headers):
    r1 = await client.post("/api/tutorial/start", headers=auth_headers)
    r2 = await client.post("/api/tutorial/start", headers=auth_headers)
    assert r1.json()["trip_id"] == r2.json()["trip_id"]


async def test_tutorial_step_advances(client: AsyncClient, auth_headers):
    await client.post("/api/tutorial/start", headers=auth_headers)
    resp = await client.patch("/api/tutorial/step", json={"step": 3}, headers=auth_headers)
    assert resp.json()["step"] == 3


async def test_tutorial_skip(client: AsyncClient, auth_headers):
    resp = await client.post("/api/tutorial/skip", headers=auth_headers)
    assert resp.json()["status"] == "skipped"


async def test_tutorial_complete_locks_trip(client: AsyncClient, auth_headers):
    r = await client.post("/api/tutorial/start", headers=auth_headers)
    trip_id = r.json()["trip_id"]
    resp = await client.post("/api/tutorial/complete", headers=auth_headers)
    assert resp.json()["status"] == "completed"
    chat = await client.post(f"/api/trips/{trip_id}/brainstorm/chat", json={"message": "hello"}, headers=auth_headers)
    assert chat.status_code == 423


async def test_tutorial_replay_reseeds(client: AsyncClient, auth_headers):
    await client.post("/api/tutorial/start", headers=auth_headers)
    await client.post("/api/tutorial/complete", headers=auth_headers)
    resp = await client.post("/api/tutorial/replay", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"
    assert resp.json()["trip_id"] is not None


async def test_tutorial_reset_clears_state(client: AsyncClient, auth_headers):
    await client.post("/api/tutorial/start", headers=auth_headers)
    resp = await client.post("/api/tutorial/reset", headers=auth_headers)
    assert resp.json()["status"] == "not_started"


async def test_tutorial_delete_trip(client: AsyncClient, auth_headers):
    await client.post("/api/tutorial/start", headers=auth_headers)
    resp = await client.delete("/api/tutorial/trip", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["trip_id"] is None


async def test_tutorial_platform_independence(client: AsyncClient, auth_headers):
    ios_headers = {**auth_headers, "X-Client-Platform": "ios"}
    web_headers = {**auth_headers, "X-Client-Platform": "web"}
    resp = await client.post("/api/tutorial/start", headers=web_headers)
    assert resp.json()["status"] == "in_progress"
    resp = await client.get("/api/tutorial/status", headers=ios_headers)
    assert resp.json()["status"] == "not_started"


async def test_tutorial_canned_brainstorm_replies(client: AsyncClient, auth_headers):
    r = await client.post("/api/tutorial/start", headers=auth_headers)
    trip_id = r.json()["trip_id"]
    fake = AsyncMock()
    fake.chat.side_effect = AssertionError("LLM must not be called")
    with patch("app.api.endpoints.brainstorm.get_brainstorm_client", return_value=fake):
        resp = await client.post(f"/api/trips/{trip_id}/brainstorm/chat", json={"message": "Hi"}, headers=auth_headers)
    assert resp.status_code == 200
    fake.chat.assert_not_called()


async def test_tutorial_canned_concierge_replies(client: AsyncClient, auth_headers):
    r = await client.post("/api/tutorial/start", headers=auth_headers)
    trip_id = r.json()["trip_id"]
    fake = AsyncMock()
    fake.dispatch.side_effect = AssertionError("Concierge LLM must not be called")
    with patch("app.api.endpoints.concierge.get_concierge_client", return_value=fake):
        resp = await client.post(f"/api/concierge/{trip_id}/chat", json={"message": "Hi"}, headers=auth_headers)
    assert resp.status_code == 200
    fake.dispatch.assert_not_called()
