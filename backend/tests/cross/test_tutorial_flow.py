"""End-to-end tutorial onboarding flow.

Asserts:
  * /tutorial/start seeds an idempotent tutorial trip and flips status.
  * Brainstorm + Concierge chat short-circuit to canned replies — no LLM
    client call, no quota increment.
  * /tutorial/complete locks the trip read-only (chat returns 423).
  * /tutorial/replay re-seeds; /tutorial/trip DELETE cleans up.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_tutorial_flow(client: AsyncClient, auth_headers: dict):
    # ── start ────────────────────────────────────────────────────────────
    resp = await client.post("/api/tutorial/start", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["step"] >= 1
    trip_id = body["trip_id"]
    assert trip_id is not None

    # Trip shows up in /trips/ with is_tutorial flag.
    resp = await client.get("/api/trips/", headers=auth_headers)
    assert resp.status_code == 200
    trips = resp.json()
    tutorial_trips = [t for t in trips if t.get("is_tutorial")]
    assert len(tutorial_trips) == 1
    assert tutorial_trips[0]["id"] == trip_id

    # Status endpoint reflects the same state.
    resp = await client.get("/api/tutorial/status", headers=auth_headers)
    assert resp.json()["trip_id"] == trip_id

    # ── brainstorm chat: canned, no LLM ─────────────────────────────────
    fake_client = AsyncMock()
    fake_client.chat.side_effect = AssertionError("LLM must not be called for tutorial")
    with patch(
        "app.api.endpoints.brainstorm.get_brainstorm_client",
        return_value=fake_client,
    ):
        resp = await client.post(
            f"/api/trips/{trip_id}/brainstorm/chat",
            json={"message": "Anything fun near Times Square?"},
            headers=auth_headers,
        )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["assistant_message"]["content"]
    fake_client.chat.assert_not_called()

    # ── concierge chat: canned, free tier OK ────────────────────────────
    fake_concierge = AsyncMock()
    fake_concierge.dispatch.side_effect = AssertionError("Concierge LLM must not be called")
    with patch(
        "app.api.endpoints.concierge.get_concierge_client",
        return_value=fake_concierge,
    ):
        resp = await client.post(
            f"/api/concierge/{trip_id}/chat",
            json={"message": "What's the move tonight?"},
            headers=auth_headers,
        )
    assert resp.status_code == 200, resp.text
    fake_concierge.dispatch.assert_not_called()

    # ── progress step ────────────────────────────────────────────────────
    resp = await client.patch(
        "/api/tutorial/step", json={"step": 5}, headers=auth_headers
    )
    assert resp.json()["step"] == 5

    # ── complete locks the trip ─────────────────────────────────────────
    resp = await client.post("/api/tutorial/complete", headers=auth_headers)
    assert resp.json()["status"] == "completed"

    resp = await client.post(
        f"/api/trips/{trip_id}/brainstorm/chat",
        json={"message": "hello"},
        headers=auth_headers,
    )
    assert resp.status_code == 423, resp.text

    # ── replay re-seeds a fresh trip ────────────────────────────────────
    resp = await client.post("/api/tutorial/replay", headers=auth_headers)
    assert resp.status_code == 200
    new_trip_id = resp.json()["trip_id"]
    assert new_trip_id is not None
    assert resp.json()["status"] == "in_progress"

    # ── delete cleans up ─────────────────────────────────────────────────
    resp = await client.delete("/api/tutorial/trip", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["trip_id"] is None


@pytest.mark.asyncio
async def test_tutorial_status_per_platform(client: AsyncClient, auth_headers: dict):
    """Tutorial state is tracked independently for web vs ios."""
    ios_headers = {**auth_headers, "X-Client-Platform": "ios"}
    web_headers = {**auth_headers, "X-Client-Platform": "web"}

    # Start on web.
    resp = await client.post("/api/tutorial/start", headers=web_headers)
    assert resp.json()["status"] == "in_progress"
    assert resp.json()["platform"] == "web"

    # iOS still reports not_started.
    resp = await client.get("/api/tutorial/status", headers=ios_headers)
    assert resp.json()["status"] == "not_started"
    assert resp.json()["platform"] == "ios"
    # …but trip_id is shared.
    assert resp.json()["trip_id"] is not None
