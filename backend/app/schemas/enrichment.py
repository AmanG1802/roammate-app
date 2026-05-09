"""Shared enrichment-status schema returned alongside enriched item lists."""
from typing import Literal, Optional
from pydantic import BaseModel


class EnrichmentStatus(BaseModel):
    status: Literal["full", "partial", "none"]
    total: int
    enriched: int
    skipped: int
    reason: Optional[str] = None
