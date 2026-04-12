from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class IdeaBinItemBase(BaseModel):
    title: str
    place_id: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    url_source: Optional[str] = None

class IdeaBinItemCreate(IdeaBinItemBase):
    pass

class IdeaBinItem(IdeaBinItemBase):
    id: int
    trip_id: int

    model_config = {"from_attributes": True}

class IngestRequest(BaseModel):
    text: str
    source_url: Optional[str] = None

class TripBase(BaseModel):
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class TripCreate(TripBase):
    pass

class Trip(TripBase):
    id: int
    created_at: datetime
    created_by_id: int

    model_config = {"from_attributes": True}
