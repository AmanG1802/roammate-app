from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BrainstormItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    place_id: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    rating: Optional[float] = None
    price_level: Optional[int] = None
    types: Optional[List[str]] = None
    opening_hours: Optional[dict] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    time_hint: Optional[str] = None
    time_category: Optional[str] = None
    url_source: Optional[str] = None


class BrainstormItemCreate(BrainstormItemBase):
    pass


class BrainstormItemOut(BrainstormItemBase):
    id: int
    trip_id: int
    user_id: int
    added_by: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BrainstormMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BrainstormChatRequest(BaseModel):
    message: str


class BrainstormChatResponse(BaseModel):
    assistant_message: BrainstormMessageOut
    history: List[BrainstormMessageOut]


class BrainstormExtractResponse(BaseModel):
    items: List[BrainstormItemOut]


class BrainstormBulkRequest(BaseModel):
    items: List[BrainstormItemBase]


class BrainstormPromoteRequest(BaseModel):
    item_ids: Optional[List[int]] = None


class PlanTripRequest(BaseModel):
    prompt: str


class PlanTripResponse(BaseModel):
    trip_name: str
    start_date: Optional[datetime] = None
    duration_days: int
    items: List[BrainstormItemBase]
