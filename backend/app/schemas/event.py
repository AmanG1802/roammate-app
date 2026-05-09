from typing import List, Optional
from pydantic import BaseModel, field_validator
from datetime import datetime, date

from app.schemas.place import PlaceFields
from app.utils.tz import ensure_utc


class EventBase(PlaceFields):
    trip_id: int
    location_name: Optional[str] = None
    day_date: Optional[date] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_locked: bool = False
    event_type: Optional[str] = None
    sort_order: int = 0
    is_skipped: bool = False

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _ensure_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return ensure_utc(v)

class EventCreate(EventBase):
    source_idea_id: Optional[int] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    day_date: Optional[date] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    sort_order: Optional[int] = None
    time_category: Optional[str] = None
    is_skipped: Optional[bool] = None

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
