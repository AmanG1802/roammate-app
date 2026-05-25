"""Unit tests for app.services.auth.tokens — pure token functions.

Tests create_access_token, decode_access_token, and _hash (no DB).
"""
import pytest
from unittest.mock import MagicMock, patch
from jose import jwt, JWTError

from app.services.auth.tokens import (
    create_access_token,
    decode_access_token,
    _hash,
)
from app.core.config import settings
from app.core.security import ALGORITHM


def _make_user(id: int = 1, auth_version: int = 1):
    user = MagicMock()
    user.id = id
    user.auth_version = auth_version
    return user


class TestCreateAccessToken:
    def test_create_access_token(self):
        # Test 1a - Token contains sub claim as string user id
        user = _make_user(id=42, auth_version=3)
        token = create_access_token(user)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "42"

        # Test 1b - Token contains ver claim
        assert payload["ver"] == 3

        # Test 1c - Token contains iat and exp claims
        assert "iat" in payload
        assert "exp" in payload

        # Test 1d - exp is roughly ACCESS_TOKEN_TTL_MIN in the future
        diff = payload["exp"] - payload["iat"]
        expected_seconds = settings.ACCESS_TOKEN_TTL_MIN * 60
        assert abs(diff - expected_seconds) < 5

    def test_create_access_token_none_auth_version(self):
        # Test 1e - None auth_version defaults to 1
        user = _make_user(id=1, auth_version=None)
        token = create_access_token(user)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["ver"] == 1


class TestDecodeAccessToken:
    def test_decode_access_token_valid(self):
        # Test 1a - Valid token decodes successfully
        user = _make_user(id=5, auth_version=2)
        token = create_access_token(user)
        payload = decode_access_token(token)
        assert payload["sub"] == "5"
        assert payload["ver"] == 2

    def test_decode_access_token_invalid(self):
        # Test 1b - Invalid token raises JWTError
        with pytest.raises(JWTError):
            decode_access_token("invalid.token.here")

    def test_decode_access_token_wrong_secret(self):
        # Test 1c - Token signed with different secret fails
        payload = {"sub": "1", "ver": 1, "exp": 9999999999}
        token = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)
        with pytest.raises(JWTError):
            decode_access_token(token)


class TestHash:
    def test_hash(self):
        # Test 1a - Returns a hex string (sha256 = 64 chars)
        result = _hash("test_token")
        assert isinstance(result, str)
        assert len(result) == 64

        # Test 1b - Same input produces same hash
        assert _hash("abc") == _hash("abc")

        # Test 1c - Different inputs produce different hashes
        assert _hash("token_a") != _hash("token_b")

        # Test 1d - Empty string still hashes
        result = _hash("")
        assert len(result) == 64
