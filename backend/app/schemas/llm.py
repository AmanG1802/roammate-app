"""Slim Pydantic models for LLM structured output enforcement.

These are NOT the full BrainstormBinItem — they contain only the fields
the LLM should generate.  Abbreviated keys (t, d, cat, …) cut ~40%
output tokens across a typical 10-item response.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    FOOD = "Food & Dining"
    CULTURE = "Culture & Arts"
    NATURE = "Nature & Outdoors"
    SHOPPING = "Shopping"
    ENTERTAINMENT = "Entertainment"
    SPORTS = "Sports & Adventure"
    RELIGIOUS = "Religious & Spiritual"
    NIGHTLIFE = "Nightlife"
    LANDMARKS = "Landmarks & Viewpoints"
    ACTIVITIES = "Activities & Tours"


class LLMItem(BaseModel):
    """One place / activity / experience the LLM identifies."""

    t: str = Field(description="Title of the place or activity")
    d: str = Field(default="", description="One-line description")
    cat: Category = Field(default=Category.ACTIVITIES, description="Category")
    tc: str = Field(default="afternoon", description="Time category")
    dur: int = Field(default=60, description="Duration in minutes")
    price: int = Field(default=0, ge=0, le=4, description="Price level 0-4")
    tags: list[str] = Field(default_factory=list, description="Type tags")


class LLMExtractResponse(BaseModel):
    """Schema for extract_items structured output."""

    items: list[LLMItem]


class LLMPlanResponse(BaseModel):
    """Schema for plan_trip structured output."""

    trip_name: str
    duration_days: int = Field(ge=1)
    items: list[LLMItem]
