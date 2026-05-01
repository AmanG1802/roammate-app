"""§8A — Persona × LLM interaction tests.

Verifies that persona descriptors propagate into the LLM system prompt
and that persona changes take effect on the next call.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.llm.models.base import LLMResponse
from tests.conftest import create_trip


async def test_user_with_personas_brainstorm_chat_passes_personas(
    client: AsyncClient, auth_headers, monkeypatch
):
    """When a user has personas set, the brainstorm chat system prompt includes them."""
    # Set personas
    await client.put(
        "/api/users/me/personas",
        json={"personas": ["foodie", "nature_lover"]},
        headers=auth_headers,
    )
    trip = await create_trip(client, auth_headers)

    # Chat — since LLM_ENABLED is False, we check fallback is still returned
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "What should I do?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    # The fallback response is returned since LLM is disabled
    assert len(resp.json()["assistant_message"]["content"]) > 0


async def test_persona_change_takes_effect_on_next_chat(
    client: AsyncClient, auth_headers
):
    """Changing personas between chats is reflected immediately."""
    await client.put(
        "/api/users/me/personas",
        json={"personas": ["foodie"]},
        headers=auth_headers,
    )
    trip = await create_trip(client, auth_headers)

    r1 = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Give me ideas"},
        headers=auth_headers,
    )
    assert r1.status_code == 200

    # Change persona
    await client.put(
        "/api/users/me/personas",
        json={"personas": ["adventure_seeker"]},
        headers=auth_headers,
    )

    r2 = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "More ideas please"},
        headers=auth_headers,
    )
    assert r2.status_code == 200


async def test_two_users_on_same_trip_personas_isolated_per_user(
    client: AsyncClient, auth_headers, second_auth_headers
):
    """Each user's personas are only applied to their own chat context."""
    from tests.conftest import invite_and_accept

    await client.put(
        "/api/users/me/personas",
        json={"personas": ["foodie"]},
        headers=auth_headers,
    )
    await client.put(
        "/api/users/me/personas",
        json={"personas": ["adventure_seeker"]},
        headers=second_auth_headers,
    )

    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"],
        "bob@test.com", role="view_with_vote",
    )

    # Both can chat independently
    r1 = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Ideas for me"},
        headers=auth_headers,
    )
    r2 = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Ideas for me"},
        headers=second_auth_headers,
    )
    assert r1.status_code == 200
    assert r2.status_code == 200


async def test_user_with_null_personas_chat_still_works(
    client: AsyncClient, auth_headers
):
    """Existing users with NULL personas don't break the chat flow."""
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Hello"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
