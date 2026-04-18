"""Pydantic validation for group schemas."""
import pytest
from pydantic import ValidationError

from app.schemas.group import (
    GroupCreate, GroupUpdate, GroupInviteRequest, GroupRoleUpdateRequest,
)


def test_group_create_requires_name():
    with pytest.raises(ValidationError):
        GroupCreate()  # type: ignore[call-arg]


def test_group_create_accepts_name():
    g = GroupCreate(name="Crew")
    assert g.name == "Crew"


def test_group_update_name_optional():
    assert GroupUpdate().name is None


def test_group_invite_default_role_member():
    r = GroupInviteRequest(email="x@y.com")
    assert r.role == "member"


def test_group_invite_requires_email():
    with pytest.raises(ValidationError):
        GroupInviteRequest(role="member")  # type: ignore[call-arg]


def test_group_invite_invalid_email():
    with pytest.raises(ValidationError):
        GroupInviteRequest(email="not-an-email")


def test_group_role_update_accepts_any_string():
    """Role validation is enforced at the endpoint (against GROUP_ROLES), not the schema."""
    assert GroupRoleUpdateRequest(role="anything").role == "anything"
