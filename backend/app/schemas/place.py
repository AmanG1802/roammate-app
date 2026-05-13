"""Shared place/activity fields used by Event, IdeaBinItem, BrainstormItem, and PlaceCard.

Every item that represents a mappable place or activity should inherit from
``PlaceFields`` so that data survives migrations between bins, timelines, and
the concierge chat without field-mismatch bugs.
"""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel


class PlaceFields(BaseModel):
    """Common enrichment fields from Google Maps and user input."""

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
    time_category: Optional[str] = None
    added_by: Optional[str] = None
