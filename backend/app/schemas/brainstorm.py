from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.schemas.enrichment import EnrichmentStatus
from app.schemas.place import PlaceFields


class BrainstormItemBase(PlaceFields):
    pass


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
    enrichment: Optional[EnrichmentStatus] = None


class BrainstormBulkRequest(BaseModel):
    items: List[BrainstormItemBase]


class BrainstormPromoteRequest(BaseModel):
    item_ids: Optional[List[int]] = None


class BrainstormSeedMessage(BaseModel):
    role: str
    content: str


class BrainstormSeedRequest(BaseModel):
    messages: List[BrainstormSeedMessage]


class BrainstormSeedResponse(BaseModel):
    seeded: int


class PlanTripRequest(BaseModel):
    prompt: str
    timezone: Optional[str] = None


class PlanTripResponse(BaseModel):
    trip_name: str
    start_date: Optional[datetime] = None
    duration_days: int
    items: List[BrainstormItemBase]
    enrichment: Optional[EnrichmentStatus] = None
    user_output: str = ""
