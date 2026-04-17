"""Integration-level tests for get_current_user via /api/users/me."""
from datetime import timedelta
from jose import jwt
from httpx import AsyncClient

from app.core.security import create_access_token, ALGORITHM
from app.core.config import settings


async def test_wrong_signature_rejected(client: AsyncClient, auth_headers):
    bad = jwt.encode({"sub": "1", "exp": 9999999999}, "wrong", algorithm=ALGORITHM)
    resp = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {bad}"}
    )
    assert resp.status_code == 401


async def test_missing_sub_rejected(client: AsyncClient):
    token = jwt.encode(
        {"exp": 9999999999}, settings.SECRET_KEY, algorithm=ALGORITHM
    )
    resp = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


async def test_wrong_algorithm_rejected(client: AsyncClient):
    # HS512 instead of HS256 → decoding with HS256 will fail
    token = jwt.encode(
        {"sub": "1", "exp": 9999999999}, settings.SECRET_KEY, algorithm="HS512"
    )
    resp = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401
