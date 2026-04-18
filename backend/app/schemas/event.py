from typing import List, Optional
from pydantic import BaseModel, field_validator
from datetime import datetime, date, timezone


def _strip_tz(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert a timezone-aware datetime to a naive (UTC) datetime.

    The DB columns are TIMESTAMP WITHOUT TIME ZONE, but the frontend sends
    ISO strings with a 'Z' suffix which Pydantic parses as tz-aware.
    asyncpg rejects mixing tz-aware and tz-naive values, so we strip the
    tzinfo after converting to UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class EventBase(BaseModel):
    trip_id: int
    title: str
    place_id: Optional[str] = None
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    day_date: Optional[date] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_locked: bool = False
    event_type: Optional[str] = None
    sort_order: int = 0
    added_by: Optional[str] = None

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _normalize_tz(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _strip_tz(v)

class EventCreate(EventBase):
    source_idea_id: Optional[int] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    day_date: Optional[date] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    sort_order: Optional[int] = None

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _normalize_tz(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _strip_tz(v)

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
    def _normalize_tz(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _strip_tz(v)
