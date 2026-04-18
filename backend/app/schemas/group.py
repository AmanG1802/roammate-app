from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime


GROUP_ROLES = ("admin", "member")


class UserInGroup(BaseModel):
    id: int
    name: str
    email: str
    model_config = {"from_attributes": True}


class GroupMemberOut(BaseModel):
    id: int
    group_id: int
    user_id: int
    role: str
    status: str = "accepted"
    user: UserInGroup
    model_config = {"from_attributes": True}


class GroupBase(BaseModel):
    name: str


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = None


class GroupOut(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime
    my_role: str
    member_count: int
    trip_count: int
    model_config = {"from_attributes": True}


class GroupDetailOut(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime
    my_role: str
    model_config = {"from_attributes": True}


class GroupInviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class GroupRoleUpdateRequest(BaseModel):
    role: str


class GroupTripSummary(BaseModel):
    id: int
    name: str
    start_date: Optional[datetime] = None
    model_config = {"from_attributes": True}


class GroupInvitationOut(BaseModel):
    """Pending group invitation as seen on the invitee's dashboard."""
    id: int
    group_id: int
    role: str
    group: "GroupSummary"
    inviter: Optional["GroupInviterSummary"] = None
    model_config = {"from_attributes": True}


class GroupSummary(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class GroupInviterSummary(BaseModel):
    name: str
    email: str
    model_config = {"from_attributes": True}


GroupInvitationOut.model_rebuild()
