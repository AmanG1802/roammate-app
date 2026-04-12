from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class EventBase(BaseModel):
    trip_id: int
    title: str
    place_id: Optional[str] = None
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    start_time: datetime
    end_time: datetime
    is_locked: bool = False
    event_type: Optional[str] = None

class EventCreate(EventBase):
    pass

class Event(EventBase):
    id: int

    model_config = {"from_attributes": True}

class RippleRequest(BaseModel):
    delta_minutes: int
    start_from_time: Optional[datetime] = None
