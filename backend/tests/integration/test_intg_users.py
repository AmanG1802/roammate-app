"""§19 Users & Personas — profile CRUD, persona catalog, and persona selection."""
from __future__ import annotations

import pytest
from unittest.mock import patch
from httpx import AsyncClient


async def test_get_profile(client: AsyncClient, auth_headers):
    resp = await client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@test.com"


async def test_update_profile(client: AsyncClient, auth_headers):
    resp = await client.put("/api/users/me", json={"name": "Alice Updated"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alice Updated"


async def test_update_profile_partial(client: AsyncClient, auth_headers):
    await client.put("/api/users/me", json={"name": "Orig", "travel_blurb": "Love it"}, headers=auth_headers)
    resp = await client.put("/api/users/me", json={"name": "NewName"}, headers=auth_headers)
    assert resp.json()["name"] == "NewName"


async def test_delete_account(client: AsyncClient, auth_headers):
    resp = await client.delete("/api/users/me", headers=auth_headers)
    assert resp.status_code in (200, 204)


async def test_persona_catalog_endpoint(client: AsyncClient, auth_headers):
    resp = await client.get("/api/users/personas/catalog", headers=auth_headers)
    assert resp.status_code == 200
    catalog = resp.json()
    assert len(catalog) >= 1
    assert "label" in catalog[0]


async def test_get_user_personas(client: AsyncClient, auth_headers):
    resp = await client.get("/api/users/me/personas", headers=auth_headers)
    assert resp.status_code == 200


async def test_set_user_personas(client: AsyncClient, auth_headers):
    resp = await client.put("/api/users/me/personas", json={"personas": ["foodie", "nature_lover"]}, headers=auth_headers)
    assert resp.status_code == 200


# ── Field validation ──────────────────────────────────────────────────────────

async def test_travel_blurb_too_long_rejected(client: AsyncClient, auth_headers):
    resp = await client.put("/api/users/me", json={"travel_blurb": "x" * 281}, headers=auth_headers)
    assert resp.status_code == 422
    assert "travel_blurb" in resp.json()["detail"].lower()


async def test_travel_blurb_max_length_accepted(client: AsyncClient, auth_headers):
    resp = await client.put("/api/users/me", json={"travel_blurb": "x" * 280}, headers=auth_headers)
    assert resp.status_code == 200


async def test_invalid_timezone_rejected(client: AsyncClient, auth_headers):
    resp = await client.put("/api/users/me", json={"timezone": "Mars/Olympus_Mons"}, headers=auth_headers)
    assert resp.status_code == 422
    assert "timezone" in resp.json()["detail"].lower()


async def test_valid_timezone_accepted(client: AsyncClient, auth_headers):
    resp = await client.put("/api/users/me", json={"timezone": "Asia/Kolkata"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["timezone"] == "Asia/Kolkata"


async def test_invalid_currency_rejected(client: AsyncClient, auth_headers):
    resp = await client.put("/api/users/me", json={"currency": "XYZ"}, headers=auth_headers)
    assert resp.status_code == 422
    assert "currency" in resp.json()["detail"].lower()


async def test_valid_currency_accepted(client: AsyncClient, auth_headers):
    resp = await client.put("/api/users/me", json={"currency": "USD"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["currency"] == "USD"


# ── Email notifications ───────────────────────────────────────────────────────

async def test_password_change_sends_email(client: AsyncClient, auth_headers):
    with patch("app.api.endpoints.users.send_password_changed_notice") as mock_send:
        resp = await client.put(
            "/api/users/me",
            json={"current_password": "password123", "password": "newpassword123"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == "alice@test.com"  # email address


async def test_password_change_wrong_current_no_email(client: AsyncClient, auth_headers):
    with patch("app.api.endpoints.users.send_password_changed_notice") as mock_send:
        resp = await client.put(
            "/api/users/me",
            json={"current_password": "wrongpass", "password": "newpassword123"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        mock_send.assert_not_called()


async def test_delete_account_sends_email(client: AsyncClient, auth_headers):
    with patch("app.api.endpoints.users.send_account_deleted_notice") as mock_send:
        resp = await client.delete("/api/users/me", headers=auth_headers)
        assert resp.status_code in (200, 204)
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == "alice@test.com"  # email captured before deletion
