from typing import Optional, Any
from pydantic import BaseModel
from datetime import datetime


class NotificationType:
    # ── Trip lifecycle ────────────────────────────────────────────
    TRIP_CREATED        = "trip_created"
    TRIP_RENAMED        = "trip_renamed"
    TRIP_DATE_CHANGED   = "trip_date_changed"
    TRIP_DELETED        = "trip_deleted"
    # ── Invitations & members ─────────────────────────────────────
    INVITE_RECEIVED     = "invite_received"
    INVITE_ACCEPTED     = "invite_accepted"
    INVITE_DECLINED     = "invite_declined"
    MEMBER_REMOVED      = "member_removed"
    MEMBER_ROLE_CHANGED = "member_role_changed"
    # ── Groups ────────────────────────────────────────────────────
    GROUP_CREATED          = "group_created"
    GROUP_INVITE_RECEIVED  = "group_invite_received"
    GROUP_INVITE_ACCEPTED  = "group_invite_accepted"
    GROUP_MEMBER_REMOVED   = "group_member_removed"
    GROUP_TRIP_ATTACHED    = "group_trip_attached"
    IDEA_ADDED_TO_GROUP    = "idea_added_to_group"
    # ── Idea bin & events ─────────────────────────────────────────
    IDEA_BIN_ITEM_ADDED = "idea_bin_item_added"
    BRAINSTORM_PROMOTED = "brainstorm_promoted"
    EVENT_ADDED         = "event_added"
    EVENT_MOVED         = "event_moved"
    EVENT_REMOVED       = "event_removed"
    RIPPLE_FIRED        = "ripple_fired"

    # ── Enabled flags ─────────────────────────────────────────────
    # Flip any value to False to suppress that notification type
    # globally. The emit() service checks this before writing rows.
    ENABLED: dict[str, bool] = {
        "trip_created":         True,
        "trip_renamed":         True,
        "trip_date_changed":    True,
        "trip_deleted":         True,
        "invite_received":      True,
        "invite_accepted":      True,
        "invite_declined":      True,
        "member_removed":       True,
        "member_role_changed":  True,
        "group_created":        True,
        "group_invite_received": True,
        "group_invite_accepted": True,
        "group_member_removed": True,
        "group_trip_attached":  True,
        "idea_added_to_group":  True,
        "idea_bin_item_added":  True,
        "brainstorm_promoted":  True,
        "event_added":          True,
        "event_moved":          True,
        "event_removed":        True,
        "ripple_fired":         True,
    }

    @classmethod
    def is_enabled(cls, notification_type: str) -> bool:
        return cls.ENABLED.get(notification_type, True)


class ActorSummary(BaseModel):
    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: int
    type: str
    payload: dict[str, Any]
    trip_id: Optional[int] = None
    group_id: Optional[int] = None
    actor: Optional[ActorSummary] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class UnreadCountOut(BaseModel):
    unread: int
