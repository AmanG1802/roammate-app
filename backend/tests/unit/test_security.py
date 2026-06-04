"""Unit tests for app.core.security — JWT token creation and password hashing.

Pure crypto operations with no DB or network calls.
"""
import pytest
from datetime import timedelta, datetime, timezone
from unittest.mock import patch
from jose import jwt

from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    ALGORITHM,
)
from app.core.config import settings


class TestCreateAccessToken:
    def test_create_access_token(self):
        # Test 1a - Token contains correct subject claim
        token = create_access_token(subject="user:42")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user:42"

        # Test 1b - Token contains exp claim
        assert "exp" in payload

        # Test 1c - Custom expires_delta is respected
        delta = timedelta(minutes=5)
        token = create_access_token(subject="user:1", expires_delta=delta)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp_dt = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert exp_dt - now < timedelta(minutes=6)
        assert exp_dt - now > timedelta(minutes=4)

        # Test 1d - Default expiry is 8 days when no delta provided
        token = create_access_token(subject="user:99")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp_dt = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = exp_dt - now
        assert timedelta(days=7, hours=23) < diff < timedelta(days=8, hours=1)

        # Test 1e - Integer subject is converted to string
        token = create_access_token(subject=123)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "123"

        # Test 1f - Token uses HS256 algorithm
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "HS256"


class TestVerifyPassword:
    def test_verify_password(self):
        # Test 1a - Correct password returns True
        hashed = get_password_hash("mypassword123")
        assert verify_password("mypassword123", hashed) is True

        # Test 1b - Wrong password returns False
        assert verify_password("wrongpassword", hashed) is False

        # Test 1c - Empty password against a hash returns False
        assert verify_password("", hashed) is False

        # Test 1d - Case-sensitive check
        hashed = get_password_hash("Password")
        assert verify_password("password", hashed) is False
        assert verify_password("PASSWORD", hashed) is False
        assert verify_password("Password", hashed) is True


class TestGetPasswordHash:
    def test_get_password_hash(self):
        # Test 1a - Returns a string
        result = get_password_hash("test")
        assert isinstance(result, str)

        # Test 1b - Hash is not the plaintext
        assert result != "test"

        # Test 1c - Same password produces different hashes (salted)
        h1 = get_password_hash("samepassword")
        h2 = get_password_hash("samepassword")
        assert h1 != h2

        # Test 1d - Hash starts with bcrypt prefix
        assert result.startswith("$2b$") or result.startswith("$2a$")

        # Test 1e - Unicode passwords are handled
        hashed = get_password_hash("pässwörd")
        assert verify_password("pässwörd", hashed) is True
