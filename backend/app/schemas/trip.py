from typing import List, Optional
from pydantic import BaseModel, EmailStr, model_validator
from datetime import datetime, date


# ── User embedded in trip member ──────────────────────────────────────────────
class UserInTrip(BaseModel):
    id: int
    name: str
    email: str
    model_config = {"from_attributes": True}


# ── Trip Member ────────────────────────────────────────────────────────────────
class TripMemberOut(BaseModel):
    id: int
    trip_id: int
    user_id: int
    role: str
    status: str = "accepted"
    user: UserInTrip
    model_config = {"from_attributes": True}


VALID_ROLES = ("admin", "view_only", "view_with_vote")


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "view_only"


class RoleUpdateRequest(BaseModel):
    role: str


# ── Invitation (enriched view for the invitee's dashboard) ────────────────────
class TripSummary(BaseModel):
    id: int
    name: str
    start_date: Optional[datetime] = None
    model_config = {"from_attributes": True}


class InviterSummary(BaseModel):
    name: str
    email: str
    model_config = {"from_attributes": True}


class InvitationOut(BaseModel):
    """Pending invitation as seen on the invitee's dashboard."""
    id: int
    trip_id: int
    role: str
    trip: TripSummary
    inviter: Optional[InviterSummary] = None
    model_config = {"from_attributes": True}


# ── Idea Bin ───────────────────────────────────────────────────────────────────
class IdeaBinItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    place_id: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    rating: Optional[float] = None
    price_level: Optional[int] = None
    types: Optional[List[str]] = None
    opening_hours: Optional[dict] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    url_source: Optional[str] = None
    time_hint: Optional[str] = None
    time_category: Optional[str] = None
    added_by: Optional[str] = None

class IdeaBinItemCreate(IdeaBinItemBase):
    pass

class IdeaBinItem(IdeaBinItemBase):
    id: int
    trip_id: int
    up: int = 0
    down: int = 0
    my_vote: int = 0

    model_config = {"from_attributes": True}

class IngestRequest(BaseModel):
    text: str
    source_url: Optional[str] = None

class TripBase(BaseModel):
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @model_validator(mode="after")
    def _check_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self

class TripCreate(TripBase):
    pass

class TripUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @model_validator(mode="after")
    def _check_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self

class Trip(TripBase):
    id: int
    created_at: datetime
    created_by_id: int

    model_config = {"from_attributes": True}


class TripWithRole(BaseModel):
    """Trip data with the requesting user's role attached."""
    id: int
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    created_by_id: int
    my_role: str

    model_config = {"from_attributes": True}


# ── Trip Days ─────────────────────────────────────────────────────────────────
class TripDayCreate(BaseModel):
    date: date

class TripDayOut(BaseModel):
    id: int
    trip_id: int
    date: date
    day_number: int
    model_config = {"from_attributes": True}
