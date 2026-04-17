from typing import Optional, List, Literal
from pydantic import BaseModel
from datetime import datetime, date


TodayState = Literal["none", "pre_trip", "in_trip", "post_trip"]


class TodayEvent(BaseModel):
    id: int
    title: str
    location_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_next: bool = False
    model_config = {"from_attributes": True}


class TodayTrip(BaseModel):
    id: int
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    model_config = {"from_attributes": True}


class TodayWidgetOut(BaseModel):
    state: TodayState
    trip: Optional[TodayTrip] = None
    # pre_trip
    days_until_start: Optional[int] = None
    # in_trip
    today_date: Optional[date] = None
    today_events: List[TodayEvent] = []
    day_number: Optional[int] = None
    total_days: Optional[int] = None
    # post_trip
    days_since_end: Optional[int] = None
    total_events: Optional[int] = None
