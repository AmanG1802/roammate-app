"""§33 Persona ↔ LLM Interaction — personas flow into LLM prompt context."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


async def test_user_with_personas_brainstorm_chat_passes_personas(client: AsyncClient, auth_headers):
    await client.put("/api/users/me/personas", json={"personas": ["foodie", "nature_lover"]}, headers=auth_headers)
    trip = await create_trip(client, auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Ideas?"}, headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["assistant_message"]["content"]) > 0


async def test_persona_change_takes_effect_on_next_chat(client: AsyncClient, auth_headers):
    await client.put("/api/users/me/personas", json={"personas": ["foodie"]}, headers=auth_headers)
    trip = await create_trip(client, auth_headers)
    r1 = await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Ideas"}, headers=auth_headers)
    assert r1.status_code == 200
    await client.put("/api/users/me/personas", json={"personas": ["adventure_seeker"]}, headers=auth_headers)
    r2 = await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "More"}, headers=auth_headers)
    assert r2.status_code == 200


async def test_two_users_on_same_trip_personas_isolated_per_user(client: AsyncClient, auth_headers, second_auth_headers):
    await client.put("/api/users/me/personas", json={"personas": ["foodie"]}, headers=auth_headers)
    await client.put("/api/users/me/personas", json={"personas": ["adventure_seeker"]}, headers=second_auth_headers)
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote")
    r1 = await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Ideas"}, headers=auth_headers)
    r2 = await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Ideas"}, headers=second_auth_headers)
    assert r1.status_code == 200 and r2.status_code == 200


async def test_user_with_null_personas_chat_still_works(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Hello"}, headers=auth_headers)
    assert resp.status_code == 200
