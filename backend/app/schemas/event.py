from typing import List, Optional
from pydantic import BaseModel, field_serializer, field_validator, model_validator
from datetime import date, datetime, time

from app.schemas.place import PlaceFields
from app.utils.tz import ensure_utc


def _format_time(v: Optional[time]) -> Optional[str]:
    """Pin TIME serialization to ``HH:MM:SS`` (no microseconds) so both Swift
    and JS parsers stay simple and lexicographic sort is safe."""
    if v is None:
        return None
    return v.strftime("%H:%M:%S")


def _strip_time_tzinfo(v: Optional[time]) -> Optional[time]:
    """Defensive: reject tz-aware TIME values. Trip-local wall-clock should be
    naive; tz lives on Trip.timezone and is applied at combine time."""
    if v is None:
        return None
    if v.tzinfo is not None:
        raise ValueError("start_time/end_time must be naive TIME (HH:MM:SS); the tz lives on Trip.timezone")
    return v


def _check_no_overnight(start: Optional[time], end: Optional[time]) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError(
            "Overnight events (end_time < start_time) are not supported in v1. "
            "Split the event across two days or set end_time on the same day."
        )


class EventBase(PlaceFields):
    trip_id: int
    location_name: Optional[str] = None
    day_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_locked: bool = False
    event_type: Optional[str] = None
    sort_order: int = 0
    is_skipped: bool = False

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _strip_tz(cls, v: Optional[time]) -> Optional[time]:
        return _strip_time_tzinfo(v)

    @model_validator(mode="after")
    def _no_overnight(self) -> "EventBase":
        _check_no_overnight(self.start_time, self.end_time)
        return self

    @field_serializer("start_time", "end_time")
    def _ser_time(self, v: Optional[time]) -> Optional[str]:
        return _format_time(v)


class EventCreate(EventBase):
    source_idea_id: Optional[int] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    day_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    sort_order: Optional[int] = None
    time_category: Optional[str] = None
    is_skipped: Optional[bool] = None

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _strip_tz(cls, v: Optional[time]) -> Optional[time]:
        return _strip_time_tzinfo(v)

    @model_validator(mode="after")
    def _no_overnight(self) -> "EventUpdate":
        # Only enforces when BOTH bounds are present in this PATCH. The
        # partial case (changing only one bound) is intentionally permitted
        # — the API endpoint checks the merged result against the existing row.
        _check_no_overnight(self.start_time, self.end_time)
        return self

    @field_serializer("start_time", "end_time")
    def _ser_time(self, v: Optional[time]) -> Optional[str]:
        return _format_time(v)


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
