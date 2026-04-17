"""Unit tests for app.core.security: password hashing and JWT."""
from datetime import timedelta
import time
from jose import jwt
import pytest

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    ALGORITHM,
)
from app.core.config import settings


def test_hash_verify_roundtrip():
    h = get_password_hash("secret123")
    assert verify_password("secret123", h)


def test_verify_wrong_password():
    h = get_password_hash("secret123")
    assert not verify_password("wrong", h)


def test_hashes_have_different_salts():
    h1 = get_password_hash("pw")
    h2 = get_password_hash("pw")
    assert h1 != h2


def test_token_contains_sub_and_exp():
    token = create_access_token(subject=42)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "42"
    assert "exp" in payload


def test_token_custom_expiry():
    token = create_access_token(subject=1, expires_delta=timedelta(seconds=60))
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    # expires within ~60s from now
    assert payload["exp"] - int(time.time()) <= 61


def test_token_wrong_secret_fails():
    token = create_access_token(subject=1)
    with pytest.raises(Exception):
        jwt.decode(token, "wrong-secret", algorithms=[ALGORITHM])
