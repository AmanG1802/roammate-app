"""§8E — Admin × User lifecycle full-loop tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, _register_and_login


async def test_user_register_login_chat_admin_summary_full_loop(
    client: AsyncClient, admin_headers
):
    """Full lifecycle: register → login → chat → admin can see user in list."""
    headers = await _register_and_login(client, "lifecycle@test.com", "LifeUser")
    trip = await create_trip(client, headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Bangkok suggestions"},
        headers=headers,
    )

    # Admin can see this user in the users list
    resp = await client.get("/api/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()["users"]]
    assert "lifecycle@test.com" in emails


async def test_user_delete_then_admin_summary_marks_rows_unattributed(
    client: AsyncClient, admin_headers
):
    """After user deletion, admin users endpoint no longer shows them."""
    headers = await _register_and_login(client, "tobedeleted@test.com", "Doomed")
    await client.delete("/api/users/me", headers=headers)

    resp = await client.get("/api/admin/users", headers=admin_headers)
    emails = [u["email"] for u in resp.json()["users"]]
    assert "tobedeleted@test.com" not in emails
