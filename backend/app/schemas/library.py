from typing import List, Optional
from pydantic import BaseModel, field_validator


class TagList(BaseModel):
    tags: List[str]

    @field_validator("tags")
    @classmethod
    def _normalize(cls, v: List[str]) -> List[str]:
        seen: set[str] = set()
        out: list[str] = []
        for t in v:
            if not t:
                continue
            norm = t.strip().lower()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            out.append(norm)
        return out


class TripProvenance(BaseModel):
    id: int
    name: str


class LibraryIdeaOut(BaseModel):
    id: int
    trip_id: int
    title: str
    place_id: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    url_source: Optional[str] = None
    time_hint: Optional[str] = None
    added_by: Optional[str] = None
    origin_idea_id: Optional[int] = None
    tags: List[str] = []
    up: int = 0
    down: int = 0
    my_vote: int = 0
    trip: Optional[TripProvenance] = None
    model_config = {"from_attributes": True}


class TagSummary(BaseModel):
    tag: str
    count: int


class CopyIdeaRequest(BaseModel):
    target_trip_id: int
