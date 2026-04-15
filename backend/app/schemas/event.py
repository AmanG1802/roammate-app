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
    start_time: Optional[datetime] = None   # None means TBD
    end_time: Optional[datetime] = None     # None means TBD
    is_locked: bool = False
    event_type: Optional[str] = None
    sort_order: int = 0

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    sort_order: Optional[int] = None

class Event(EventBase):
    id: int

    model_config = {"from_attributes": True}

class RippleRequest(BaseModel):
    delta_minutes: int
    start_from_time: Optional[datetime] = None
