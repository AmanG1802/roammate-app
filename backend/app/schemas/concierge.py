"""Pydantic schemas for the Concierge intent dispatcher.

Covers: LLM structured output (ConciergeResponse), per-intent param shapes,
and request/response models for all /concierge/* API endpoints.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.enrichment import EnrichmentStatus
from app.schemas.place import PlaceFields


# ── Intent enum ──────────────────────────────────────────────────────────────

class ConciergeIntent(str, Enum):
    shift_timeline = "shift_timeline"
    move_event = "move_event"
    add_event = "add_event"
    skip_event = "skip_event"
    explain_plan = "explain_plan"
    find_nearby = "find_nearby"
    chat_only = "chat_only"


# ── LLM structured output ───────────────────────────────────────────────────

class ConciergeResponse(BaseModel):
    """Schema the LLM must return as JSON.

    ``params_json`` is a stringified JSON blob so the schema stays compatible
    across OpenAI (strict mode forbids open dicts), Gemini (rejects
    additionalProperties), and Claude.
    """
    intent: ConciergeIntent
    user_message: str = Field(description="Formatted explanation for the chat UI")
    params_json: str = Field(
        default="{}",
        description='Stringified JSON object with intent-specific parameters, e.g. {"delta_minutes": 15}',
    )
    requires_confirmation: bool = True


# ── Per-intent param shapes (for documentation / validation) ─────────────────

class ShiftTimelineParams(BaseModel):
    delta_minutes: int
    start_from_event_id: Optional[int] = None

class MoveEventParams(BaseModel):
    # Time/day fields are intentionally Optional[str] (not typed time/date):
    # the concierge LLM emits loose human forms ("4pm", "16:00", "tomorrow")
    # which a downstream normalizer rewrites to canonical TIME/DATE before
    # hitting the event endpoints. Tightening here would 422 on natural
    # emissions. Validation belongs at the normalizer boundary.
    event_id: int
    new_start_time: Optional[str] = None
    new_day_date: Optional[str] = None

class AddEventParams(BaseModel):
    # See MoveEventParams: strings are accepted in loose forms; downstream
    # normalizer rewrites to canonical HH:MM:SS / YYYY-MM-DD before persisting.
    title: str
    day_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    category: Optional[str] = None
    place_id: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class SkipEventParams(BaseModel):
    event_id: int

class ExplainPlanParams(BaseModel):
    scope: str = "today"
    question: Optional[str] = None

class FindNearbyParams(BaseModel):
    query: str


# ── API request / response schemas ──────────────────────────────────────────

class ConciergeChatRequest(BaseModel):
    message: str

# ── Dry-run preview (3.5 / 3.6) ──────────────────────────────────────────────

class PreviewChange(BaseModel):
    """One event's projected before/after for the action-card timeline diff."""
    event_id: int
    title: str
    day_date: Optional[str] = None
    old_start: Optional[str] = None
    new_start: Optional[str] = None
    old_end: Optional[str] = None
    new_end: Optional[str] = None

class PreviewWarning(BaseModel):
    kind: str  # "overlap" | "travel" | "cross_midnight" | "opening_hours"
    message: str
    event_id: Optional[int] = None

class ConciergePreview(BaseModel):
    """Real projected impact of a pending write, computed via a dry-run ripple
    inside a rolled-back SAVEPOINT at dispatch time."""
    summary: str
    changes: list[PreviewChange] = Field(default_factory=list)
    warnings: list[PreviewWarning] = Field(default_factory=list)


class ConciergeChatResponse(BaseModel):
    intent: ConciergeIntent
    user_message: str
    params: dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = True
    message_type: str = "text"  # "text" | "action_card" | "place_card" | "error"
    enrichment: Optional[EnrichmentStatus] = None
    preview: Optional[ConciergePreview] = None


# ── Shared trip-wide thread (3.1) ────────────────────────────────────────────

class ConciergeMessageOut(BaseModel):
    id: int
    role: str               # "user" | "assistant" | "system"
    content: str
    message_type: str = "text"
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

class ConciergeThreadResponse(BaseModel):
    messages: list[ConciergeMessageOut] = Field(default_factory=list)
    # Whether the caller may post / confirm actions (Plus AND trip editor).
    can_write: bool = False


class PlaceCard(PlaceFields):
    """Nearby search result card — inherits all shared place fields plus travel info."""
    place_id: str  # override Optional→required for search results
    lat: float     # override Optional→required for search results
    lng: float     # override Optional→required for search results
    travel_time_s: Optional[int] = None
    distance_m: Optional[int] = None

class FindNearbyRequest(BaseModel):
    query: str
    lat: float
    lng: float
    category: Optional[str] = None
    limit: int = 3

class FindNearbyResponse(BaseModel):
    places: list[PlaceCard]
    enrichment: Optional[EnrichmentStatus] = None


class SkipEventRequest(BaseModel):
    event_id: int


class ExecuteRequest(BaseModel):
    intent: str
    params: dict[str, Any] = Field(default_factory=dict)

class ExecuteResponse(BaseModel):
    success: bool
    message: str
    updated_events: Optional[list[dict[str, Any]]] = None
    new_event: Optional[dict[str, Any]] = None


class UndoResponse(BaseModel):
    success: bool
    message: str
    # Events restored to their prior state (for the client to re-render).
    updated_events: Optional[list[dict[str, Any]]] = None
    # The id of the action that was undone, if any.
    undone_action_id: Optional[int] = None


class WhatsNextResponse(BaseModel):
    current_event: Optional[dict[str, Any]] = None
    next_event: Optional[dict[str, Any]] = None
    time_until_next: Optional[str] = None
    travel_time_to_next: Optional[int] = None


class TodaySummaryEvent(BaseModel):
    event: dict[str, Any]
    status: str  # "upcoming" | "ongoing" | "completed" | "skipped"

class TodaySummaryResponse(BaseModel):
    date: str
    total_events: int
    completed: int
    upcoming: int
    skipped: int
    events: list[TodaySummaryEvent]
