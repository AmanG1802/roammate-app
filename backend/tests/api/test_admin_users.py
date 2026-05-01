"""§7B — Admin users endpoint tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import _register_and_login


async def test_GET_admin_users_returns_total_and_list(
    client: AsyncClient, admin_headers, auth_headers
):
    resp = await client.get("/api/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "users" in data
    assert data["total"] >= 1  # At least Alice exists
    assert isinstance(data["users"], list)


async def test_GET_admin_users_sorted_by_created_desc(
    client: AsyncClient, admin_headers, auth_headers, second_auth_headers
):
    resp = await client.get("/api/admin/users", headers=admin_headers)
    users = resp.json()["users"]
    if len(users) >= 2:
        # Most recent user should be first
        dates = [u["created_at"] for u in users if u["created_at"]]
        assert dates == sorted(dates, reverse=True)


async def test_GET_admin_users_does_not_leak_hashed_password(
    client: AsyncClient, admin_headers, auth_headers
):
    resp = await client.get("/api/admin/users", headers=admin_headers)
    users = resp.json()["users"]
    for user in users:
        assert "hashed_password" not in user
        assert "password" not in user


async def test_GET_admin_users_includes_user_fields(
    client: AsyncClient, admin_headers, auth_headers
):
    resp = await client.get("/api/admin/users", headers=admin_headers)
    users = resp.json()["users"]
    assert len(users) >= 1
    user = users[0]
    assert "id" in user
    assert "name" in user
    assert "email" in user
    assert "created_at" in user
