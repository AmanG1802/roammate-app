"""Unit tests for app.schemas.notification — NotificationType flags and is_enabled."""
import pytest
from app.schemas.notification import NotificationType


class TestNotificationType:
    def test_is_enabled_known_types(self):
        # Test 1a - All defined types are enabled by default
        for type_name, enabled in NotificationType.ENABLED.items():
            assert enabled is True, f"{type_name} should be enabled"

    def test_is_enabled_returns_true_for_known(self):
        # Test 1b - is_enabled returns True for known enabled types
        assert NotificationType.is_enabled("trip_created") is True
        assert NotificationType.is_enabled("invite_received") is True
        assert NotificationType.is_enabled("ripple_fired") is True

    def test_is_enabled_unknown_type_defaults_true(self):
        # Test 1c - Unknown type defaults to True (permissive)
        assert NotificationType.is_enabled("totally_unknown_type") is True

    def test_type_constants_match_enabled_keys(self):
        # Test 1d - All type constants have a matching ENABLED entry
        type_attrs = [
            v for k, v in vars(NotificationType).items()
            if isinstance(v, str) and not k.startswith("_") and k != "ENABLED"
        ]
        for type_val in type_attrs:
            assert type_val in NotificationType.ENABLED, (
                f"Type constant {type_val} missing from ENABLED dict"
            )

    def test_enabled_count(self):
        # Test 1e - All notification types registered (at least 20)
        assert len(NotificationType.ENABLED) >= 20
