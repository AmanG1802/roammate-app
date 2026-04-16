from typing import Optional, Any
from pydantic import BaseModel
from datetime import datetime


class NotificationType:
    TRIP_CREATED = "trip_created"
    TRIP_RENAMED = "trip_renamed"
    TRIP_DATE_CHANGED = "trip_date_changed"
    TRIP_DELETED = "trip_deleted"
    INVITE_RECEIVED = "invite_received"
    INVITE_ACCEPTED = "invite_accepted"
    INVITE_DECLINED = "invite_declined"
    MEMBER_REMOVED = "member_removed"
    MEMBER_ROLE_CHANGED = "member_role_changed"
    GROUP_CREATED = "group_created"
    GROUP_INVITE_RECEIVED = "group_invite_received"
    GROUP_INVITE_ACCEPTED = "group_invite_accepted"
    GROUP_MEMBER_REMOVED = "group_member_removed"
    GROUP_TRIP_ATTACHED = "group_trip_attached"
    IDEA_ADDED_TO_GROUP = "idea_added_to_group"


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
