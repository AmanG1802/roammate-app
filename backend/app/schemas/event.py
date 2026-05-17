import re
from typing import List, Optional
from pydantic import BaseModel, field_validator
from datetime import datetime

from app.schemas.place import PlaceFields
from app.utils.tz import ensure_utc

_DAY_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_day_date_str(v: Optional[str]) -> Optional[str]:
    if v is not None and not _DAY_DATE_RE.match(v):
        raise ValueError("day_date must be YYYY-MM-DD")
    return v


class EventBase(PlaceFields):
    trip_id: int
    location_name: Optional[str] = None
    day_date: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_locked: bool = False
    event_type: Optional[str] = None
    sort_order: int = 0
    is_skipped: bool = False

    @field_validator("day_date", mode="after")
    @classmethod
    def _check_day_date(cls, v: Optional[str]) -> Optional[str]:
        return _validate_day_date_str(v)

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _ensure_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return ensure_utc(v)

class EventCreate(EventBase):
    source_idea_id: Optional[int] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    day_date: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    sort_order: Optional[int] = None
    time_category: Optional[str] = None
    is_skipped: Optional[bool] = None

    @field_validator("day_date", mode="after")
    @classmethod
    def _check_day_date(cls, v: Optional[str]) -> Optional[str]:
        return _validate_day_date_str(v)

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _ensure_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return ensure_utc(v)

class Event(EventBase):
    id: int
    up: int = 0
    down: int = 0
    my_vote: int = 0

    model_config = {"from_attributes": True}

class RippleRequest(BaseModel):
    delta_minutes: int
    start_from_time: Optional[datetime] = None

    @field_validator("start_from_time", mode="after")
    @classmethod
    def _ensure_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return ensure_utc(v)
