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
    """Schema for extract_items structured output.

    The LLM returns both a short natural-language ``user_output`` (echoed
    back to the user as a friendly confirmation) and a flat
    ``map_output`` list of itinerary candidates.  Only ``map_output`` is
    persisted — ``user_output`` is for the chat UI.
    """

    user_output: str = Field(default="", description="Short confirmation text for the user")
    map_output: list[LLMItem] = Field(default_factory=list)


class LLMPlanResponse(BaseModel):
    """Schema for plan_trip structured output.

    ``user_output`` is a short narrative blurb shown in the planner;
    ``trip_name`` and ``duration_days`` are top-level fields used by the
    create-trip flow; ``map_output`` is the iterable list of itinerary
    items that downstream code enriches via Google Maps.
    """

    user_output: str = Field(default="", description="Narrative blurb for the user")
    trip_name: str
    duration_days: int = Field(ge=1)
    map_output: list[LLMItem] = Field(default_factory=list)
