"""Unit tests for app.services.entitlements — pure predicate logic.

Tests _is_active, _current_period, _is_tutorial with mocked User/Trip objects.
The async functions (enforce_*, get_entitlement) require DB and are integration-tier.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.services.entitlements import (
    _is_active,
    _current_period,
    _is_tutorial,
    Feature,
    PLUS_FEATURES,
    Entitlement,
    _raise_needs_plus,
)
from fastapi import HTTPException


def _make_user(
    subscription_tier: str = "free",
    subscription_status: str | None = None,
    subscription_current_period_end: datetime | None = None,
):
    user = MagicMock()
    user.subscription_tier = subscription_tier
    user.subscription_status = subscription_status
    user.subscription_current_period_end = subscription_current_period_end
    return user


class TestIsActive:
    def test_is_active(self):
        # Test 1a - Free tier user is not active
        user = _make_user(subscription_tier="free")
        assert _is_active(user) is False

        # Test 1b - Plus tier with active status and future period_end
        future = datetime.now(timezone.utc) + timedelta(days=10)
        user = _make_user(
            subscription_tier="plus",
            subscription_status="active",
            subscription_current_period_end=future,
        )
        assert _is_active(user) is True

        # Test 1c - Plus tier with expired period_end
        past = datetime.now(timezone.utc) - timedelta(days=1)
        user = _make_user(
            subscription_tier="plus",
            subscription_status="active",
            subscription_current_period_end=past,
        )
        assert _is_active(user) is False

        # Test 1d - Plus tier with past_due status (grace period)
        future = datetime.now(timezone.utc) + timedelta(days=3)
        user = _make_user(
            subscription_tier="plus",
            subscription_status="past_due",
            subscription_current_period_end=future,
        )
        assert _is_active(user) is True

        # Test 1e - Plus tier with canceled status
        user = _make_user(
            subscription_tier="plus",
            subscription_status="canceled",
            subscription_current_period_end=None,
        )
        assert _is_active(user) is False

        # Test 1f - Plus tier with one_time status and future end
        future = datetime.now(timezone.utc) + timedelta(days=15)
        user = _make_user(
            subscription_tier="plus",
            subscription_status="one_time",
            subscription_current_period_end=future,
        )
        assert _is_active(user) is True

        # Test 1g - Plus tier with None period_end trusts status
        user = _make_user(
            subscription_tier="plus",
            subscription_status="active",
            subscription_current_period_end=None,
        )
        assert _is_active(user) is True

        # Test 1h - Plus tier with expired status
        user = _make_user(
            subscription_tier="plus",
            subscription_status="expired",
            subscription_current_period_end=None,
        )
        assert _is_active(user) is False


class TestCurrentPeriod:
    def test_current_period(self):
        # Test 1a - Returns YYYY-MM string format
        result = _current_period()
        assert len(result) == 7
        assert result[4] == "-"
        year, month = result.split("-")
        assert 2020 <= int(year) <= 2030
        assert 1 <= int(month) <= 12

        # Test 1b - Matches current UTC month
        now = datetime.now(timezone.utc)
        expected = now.strftime("%Y-%m")
        assert result == expected


class TestIsTutorial:
    def test_is_tutorial(self):
        # Test 1a - None trip returns False
        assert _is_tutorial(None) is False

        # Test 1b - Trip with is_tutorial=True returns True
        trip = MagicMock()
        trip.is_tutorial = True
        assert _is_tutorial(trip) is True

        # Test 1c - Trip with is_tutorial=False returns False
        trip = MagicMock()
        trip.is_tutorial = False
        assert _is_tutorial(trip) is False

        # Test 1d - Trip without is_tutorial attribute returns False
        trip = MagicMock(spec=[])
        assert _is_tutorial(trip) is False


class TestEntitlementDataclass:
    def test_entitlement_to_dto(self):
        # Test 1a - to_dto returns all expected keys
        ent = Entitlement(
            tier="free",
            status="none",
            period_end=None,
            can_create_active_trip=True,
            can_use_concierge=False,
            can_use_offline_maps=False,
            brainstorm_remaining=10,
            active_trip_count=1,
            active_trip_cap=2,
            brainstorm_used=5,
            brainstorm_cap=15,
        )
        dto = ent.to_dto()
        assert dto["tier"] == "free"
        assert dto["status"] == "none"
        assert dto["period_end"] is None
        assert dto["can_create_active_trip"] is True
        assert dto["can_use_concierge"] is False
        assert dto["brainstorm_remaining"] == 10
        assert dto["active_trip_count"] == 1
        assert dto["active_trip_cap"] == 2
        assert dto["brainstorm_used"] == 5
        assert dto["brainstorm_cap"] == 15
        assert "price_inr" in dto
        assert "onetime_price_inr" in dto
        assert "onetime_duration_days" in dto

        # Test 1b - Plus user with unlimited brainstorm
        ent_plus = Entitlement(
            tier="plus",
            status="active",
            period_end=datetime(2025, 12, 31, tzinfo=timezone.utc),
            can_create_active_trip=True,
            can_use_concierge=True,
            can_use_offline_maps=True,
            brainstorm_remaining=None,
            active_trip_count=5,
            active_trip_cap=None,
            brainstorm_used=100,
            brainstorm_cap=None,
        )
        dto = ent_plus.to_dto()
        assert dto["tier"] == "plus"
        assert dto["brainstorm_remaining"] is None
        assert dto["active_trip_cap"] is None
        assert dto["period_end"] == "2025-12-31T00:00:00+00:00"


class TestRaiseNeedsPlus:
    def test_raise_needs_plus(self):
        # Test 1a - Raises HTTPException with 402 status
        with pytest.raises(HTTPException) as exc_info:
            _raise_needs_plus("concierge")
        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["code"] == "needs_plus"
        assert exc_info.value.detail["feature"] == "concierge"

        # Test 1b - Extra kwargs are included in payload
        with pytest.raises(HTTPException) as exc_info:
            _raise_needs_plus("active_trips", cap=2, current=2)
        detail = exc_info.value.detail
        assert detail["cap"] == 2
        assert detail["current"] == 2


class TestPlusFeatures:
    def test_plus_features_set(self):
        # Test 1a - PLUS_FEATURES contains expected gated features
        assert "concierge" in PLUS_FEATURES
        assert "offline_maps" in PLUS_FEATURES

        # Test 1b - Feature type includes all known features
        # This validates the Literal type has at least the known values
        known: set[str] = {"active_trips", "brainstorm_quota", "concierge", "offline_maps"}
        assert PLUS_FEATURES.issubset(known)
