from typing import Optional, List, Literal
from pydantic import BaseModel, field_serializer
from datetime import datetime, date, time


TodayState = Literal["none", "pre_trip", "in_trip", "post_trip"]


class TodayEvent(BaseModel):
    id: int
    title: str
    location_name: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_next: bool = False
    is_ongoing: bool = False
    is_past: bool = False
    model_config = {"from_attributes": True}

    @field_serializer("start_time", "end_time")
    def _ser_time(self, v: Optional[time]) -> Optional[str]:
        return v.strftime("%H:%M:%S") if v is not None else None


class TodayTrip(BaseModel):
    id: int
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    model_config = {"from_attributes": True}


class TodayWidgetPage(BaseModel):
    """One page of the widget carousel — a single trip in context."""
    state: TodayState
    trip: TodayTrip
    days_until_start: Optional[int] = None
    today_date: Optional[date] = None
    today_events: List[TodayEvent] = []
    day_number: Optional[int] = None
    total_days: Optional[int] = None
    days_since_end: Optional[int] = None
    total_events: Optional[int] = None


class TodayWidgetOut(BaseModel):
    pages: List[TodayWidgetPage] = []
    default_index: int = 0
