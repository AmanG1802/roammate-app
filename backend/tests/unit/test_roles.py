"""Unit tests for app.services.roles — role constants and gating logic.

Tests the VOTE_ROLES and ADMIN_ONLY constants. The async functions
(get_trip_member, require_trip_member, etc.) require DB access.
"""
import pytest
from app.services.roles import VOTE_ROLES, ADMIN_ONLY


class TestRoleConstants:
    def test_vote_roles(self):
        # Test 1a - VOTE_ROLES contains expected roles
        assert "admin" in VOTE_ROLES
        assert "view_with_vote" in VOTE_ROLES

        # Test 1b - view_only is NOT in VOTE_ROLES
        assert "view_only" not in VOTE_ROLES

        # Test 1c - VOTE_ROLES is a set
        assert isinstance(VOTE_ROLES, set)

    def test_admin_only(self):
        # Test 1a - ADMIN_ONLY contains only "admin"
        assert "admin" in ADMIN_ONLY
        assert len(ADMIN_ONLY) == 1

        # Test 1b - Non-admin roles are excluded
        assert "view_only" not in ADMIN_ONLY
        assert "view_with_vote" not in ADMIN_ONLY

        # Test 1c - ADMIN_ONLY is a set
        assert isinstance(ADMIN_ONLY, set)

    def test_admin_is_superset(self):
        # Test 1a - admin role grants both admin-only AND vote capabilities
        assert ADMIN_ONLY.issubset(VOTE_ROLES)
