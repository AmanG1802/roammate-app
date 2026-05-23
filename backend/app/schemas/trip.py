from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_serializer, field_validator, model_validator
from datetime import datetime, date, time

from app.schemas.place import PlaceFields


# ── User embedded in trip member ──────────────────────────────────────────────
class UserInTrip(BaseModel):
    id: int
    name: str
    email: str
    avatar_url: Optional[str] = None
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
class IdeaBinItemBase(PlaceFields):
    # TIME (HH:MM:SS), trip-local wall-clock. Ideas have no day_date; promotion
    # to the timeline attaches it.
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _strip_tz(cls, v: Optional[time]) -> Optional[time]:
        if v is not None and v.tzinfo is not None:
            raise ValueError("start_time/end_time must be naive TIME (HH:MM:SS)")
        return v

    @model_validator(mode="after")
    def _no_overnight(self) -> "IdeaBinItemBase":
        s, e = self.start_time, self.end_time
        if s is not None and e is not None and e < s:
            raise ValueError(
                "Overnight idea times (end < start) are not supported in v1."
            )
        return self

    @field_serializer("start_time", "end_time")
    def _ser_time(self, v: Optional[time]) -> Optional[str]:
        return v.strftime("%H:%M:%S") if v is not None else None

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
    timezone: str = "UTC"
    destination_city: Optional[str] = None
    country_code: Optional[str] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None

    @model_validator(mode="after")
    def _check_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self

    @field_validator("country_code", mode="after")
    @classmethod
    def _upper_country(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().upper()
        if len(v) != 2:
            raise ValueError("country_code must be ISO-3166-1 alpha-2 (2 letters)")
        return v

class TripCreate(TripBase):
    pass

class TripUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    timezone: Optional[str] = None

    @model_validator(mode="after")
    def _check_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self

class Trip(TripBase):
    id: int
    created_at: datetime
    created_by_id: int
    is_tutorial: bool = False
    is_tutorial_completed: bool = False

    model_config = {"from_attributes": True}


class TripWithRole(BaseModel):
    """Trip data with the requesting user's role attached."""
    id: int
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    timezone: str = "UTC"
    created_at: datetime
    created_by_id: int
    my_role: str
    is_tutorial: bool = False
    is_tutorial_completed: bool = False

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
