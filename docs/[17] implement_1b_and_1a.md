---
name: Implement 1b and 1a
overview: Refactor the data model to eliminate dead columns, unify field definitions via a shared mixin, rename Event to TimelineItem, drop time_hint in favour of start_time/end_time on IdeaBinItem, fix all copy/promotion field losses (1b), then surface enrichment failures to the user via a per-item "!" indicator (1a).
todos:
  - id: 1b-mixin
    content: Define PlaceColumnsMixin + PLACE_FIELDS in all_models.py, refactor all 3 models to inherit from it
    status: completed
  - id: 1b-rename
    content: Rename Event -> TimelineItem (model class + __tablename__ to timeline_item), update all import sites
    status: completed
  - id: 1b-drop-dead-cols
    content: Remove opening_hours/phone/website/url_source from models, schemas, endpoints, services, fallbacks
    status: completed
  - id: 1b-drop-time-hint
    content: Remove time_hint everywhere, add start_time/end_time to IdeaBinItem model and schemas
    status: completed
  - id: 1b-fix-copy-logic
    content: Replace _COPY_FIELDS, _ENRICH_FIELDS, and ideas.py ad-hoc list with PLACE_FIELDS import
    status: completed
  - id: 1b-frontend-time
    content: Update frontend store/components/tests to use start_time instead of time_hint
    status: completed
  - id: 1b-tests
    content: Update all affected backend tests, add cross-trip copy and round-trip field survival tests
    status: completed
  - id: 1a-backend-summary
    content: Add EnrichmentSummary, enrich_items_with_summary(), failure reason tagging in base.py
    status: completed
  - id: 1a-schema-endpoint
    content: Add EnrichmentStatus to BrainstormExtractResponse, PlanTripResponse, ConciergeChatResponse, and FindNearbyResponse; update all 4 endpoints
    status: completed
  - id: 1a-frontend-indicator
    content: "Add per-item ! icon with 'Map data unavailable' tooltip on all place cards: BrainstormBin, IdeaBin, DashboardTripPlanner, and ConciergeChatDrawer PlaceCardItem"
    status: completed
  - id: 1a-tests
    content: Add enrichment status tests (backend unit + endpoint integration, including concierge endpoints)
    status: completed
isProject: false
---

# Implement 1b (Model Unification) and 1a (Enrichment Surfacing)

## 1b — Model Unification and Field Persistence

### Part 1: Define PlaceColumnsMixin and PLACE_FIELDS

Create a mixin in [backend/app/models/all_models.py](backend/app/models/all_models.py) (inline, not a separate file — all models already live here).

```python
class PlaceColumnsMixin:
    """Canonical enrichment fields shared by BrainstormBinItem, IdeaBinItem, TimelineItem."""
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    place_id = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    address = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    price_level = Column(Integer, nullable=True)
    types = Column(JSON, nullable=True)
    time_category = Column(String, nullable=True)
    added_by = Column(String, nullable=True)

PLACE_FIELDS: tuple[str, ...] = (
    "title", "description", "category", "place_id", "lat", "lng",
    "address", "photo_url", "rating", "price_level", "types",
    "time_category", "added_by",
)
```

**13 fields.** Removed: `opening_hours`, `phone`, `website`, `url_source`, `time_hint`. Not included: `start_time`/`end_time` (model-specific).

### Part 2: Refactor the three SQLAlchemy models

`**BrainstormBinItem(PlaceColumnsMixin, Base)`** — add-ons: `user_id`, `created_at`

`**IdeaBinItem(PlaceColumnsMixin, Base)**` — add-ons: `origin_idea_id`, `start_time` (NEW), `end_time` (NEW)

`**TimelineItem(PlaceColumnsMixin, Base)**` (rename from `Event`) — add-ons: `location_name`, `day_date`, `start_time`, `end_time`, `is_locked`, `event_type`, `sort_order`, `is_skipped`. Table name changes to `timeline_item`.

### Part 3: Rename Event -> TimelineItem (DB table: `timeline_item`)

Since the DB table name changes from `event` to `timeline_item`, foreign keys and table args in these models must update:

- `EventVote.__tablename__` stays `event_vote` but FK changes to `timeline_item.id`
- Trip relationship `back_populates="events"` renames

**All import sites** — change `Event` to `TimelineItem` (some import as `Event as EventModel`, update the source name):

- [backend/app/api/endpoints/events.py](backend/app/api/endpoints/events.py)
- [backend/app/api/endpoints/trips.py](backend/app/api/endpoints/trips.py)
- [backend/app/api/endpoints/maps.py](backend/app/api/endpoints/maps.py)
- [backend/app/api/endpoints/concierge.py](backend/app/api/endpoints/concierge.py)
- [backend/app/api/endpoints/dashboard.py](backend/app/api/endpoints/dashboard.py)
- [backend/app/services/concierge_executor.py](backend/app/services/concierge_executor.py)
- [backend/app/services/ripple_engine.py](backend/app/services/ripple_engine.py)
- [backend/app/services/smart_ripple.py](backend/app/services/smart_ripple.py)
- [backend/app/main.py](backend/app/main.py)
- [backend/tests/services/test_ripple_engine.py](backend/tests/services/test_ripple_engine.py)

**Pydantic schemas stay as `EventBase`/`Event`** — no rename there per your decision. Keep API route `/api/events/` unchanged.

### Part 4: Drop dead columns (opening_hours, phone, website, url_source)

Remove from **models** (all three via mixin removal — they just won't be in PlaceColumnsMixin).

Remove from **Pydantic schemas**:

- [backend/app/schemas/brainstorm.py](backend/app/schemas/brainstorm.py) — `BrainstormItemBase`: drop `opening_hours`, `phone`, `website`, `url_source`, `time_hint`
- [backend/app/schemas/trip.py](backend/app/schemas/trip.py) — `IdeaBinItemBase`: drop `opening_hours`, `phone`, `website`, `url_source`, `time_hint`; add `start_time`, `end_time`
- [backend/app/schemas/event.py](backend/app/schemas/event.py) — `EventBase`: drop `opening_hours`, `phone`, `website`
- [backend/app/schemas/place.py](backend/app/schemas/place.py) — no changes needed (already clean)
- [backend/app/schemas/library.py](backend/app/schemas/library.py) — `LibraryIdeaOut`: drop `url_source`, `time_hint`; add `start_time`, `end_time`

Remove from **endpoint code**:

- [backend/app/api/endpoints/events.py](backend/app/api/endpoints/events.py) — remove from `_ENRICH_FIELDS` (replaced by `PLACE_FIELDS` import), remove from 4 manual `Event(...)` construction sites (lines ~26-37, ~74-95, ~279-285, ~381-393)
- [backend/app/api/endpoints/brainstorm.py](backend/app/api/endpoints/brainstorm.py) — replace `_COPY_FIELDS` with `PLACE_FIELDS` import, fix enrichment subset at line ~287 to use `PLACE_FIELDS`, remove `TIME_CATEGORY_DEFAULTS` / `time_hint` backfill at line ~297
- [backend/app/api/endpoints/ideas.py](backend/app/api/endpoints/ideas.py) — `copy_idea_to_trip()`: replace ad-hoc field list with `PLACE_FIELDS` loop + `start_time`/`end_time` + `origin_idea_id`
- [backend/app/api/endpoints/trips.py](backend/app/api/endpoints/trips.py) — remove from 2 manual construction sites (lines ~489-494, ~937-941)
- [backend/app/api/endpoints/groups.py](backend/app/api/endpoints/groups.py) — remove references

Remove from **services**:

- [backend/app/services/llm/services/v1/roammate_v1.py](backend/app/services/llm/services/v1/roammate_v1.py) — remove `opening_hours`, `phone`, `website`, `url_source` from default dict (line ~69-75), remove `time_hint` / `TIME_CATEGORY_DEFAULTS` (line ~63)
- [backend/app/services/llm/fallbacks.py](backend/app/services/llm/fallbacks.py) — remove 4 fields from all ~20 fallback item dicts
- [backend/app/services/llm/pre_processor.py](backend/app/services/llm/pre_processor.py) — remove `_TIME_RE`, `_extract_time_hints()`, `time_hints` from `PreExtracted`
- [backend/app/services/idea_bin.py](backend/app/services/idea_bin.py) — remove `_TIME_RE`, `_extract_time_hint()`, `_strip_time_hint()`, remove `url_source=` and `time_hint=` from `IdeaBinItem()` constructors

### Part 5: Drop time_hint, add start_time/end_time to IdeaBinItem

**Backend**: Add `start_time` and `end_time` columns to `IdeaBinItem` (DateTime(timezone=True), nullable). Already covered in Part 2.

**Frontend** — significant changes:

- [frontend/lib/store.ts](frontend/lib/store.ts):
  - `Idea` type: replace `time_hint?: string | null` with `start_time?: Date | null` and `end_time?: Date | null`
  - `moveEventToIdea()`: carry `start_time`/`end_time` directly from the event to the idea (no `formatTimeHint` conversion)
  - `moveIdeaToTimeline()`: carry `start_time` directly (no `parseTimeString` needed)
  - Remove `formatTimeHint()` helper
- [frontend/components/trip/Timeline.tsx](frontend/components/trip/Timeline.tsx):
  - Idea drop handler: pass `idea.start_time` directly instead of `parseTimeString(idea.time_hint)`
  - Remove `parseTimeString` import/usage
- [frontend/components/trip/IdeaBin.tsx](frontend/components/trip/IdeaBin.tsx):
  - Remove `extractTimeHint()`, `stripTimeHint()`, `hintToTimeValue()`, `timeValueToHint()` helpers
  - Clock badge: display formatted `idea.start_time` instead of `idea.time_hint`
  - `handleSaveTime`: write `start_time` to backend instead of `time_hint`
  - Fallback ingest (comma-split): don't extract time hints — just create bare items
- [frontend/components/trip/BrainstormBin.tsx](frontend/components/trip/BrainstormBin.tsx):
  - Remove `time_hint` from the item type; display `time_category` only (or `start_time` if present)
- [frontend/components/groups/GroupsPanel.tsx](frontend/components/groups/GroupsPanel.tsx): remove `time_hint` from type
- [frontend/app/trips/page.tsx](frontend/app/trips/page.tsx): replace `time_hint` mapping with `start_time`/`end_time`

**Frontend tests** to update:

- [frontend/tests/IdeaBin.test.tsx](frontend/tests/IdeaBin.test.tsx) — rewrite time_hint tests to use start_time
- [frontend/tests/store.test.ts](frontend/tests/store.test.ts) — rewrite time_hint round-trip tests to use start_time
- [frontend/tests/Timeline.test.tsx](frontend/tests/Timeline.test.tsx) — rewrite time_hint drop tests to use start_time

### Part 6: Fix copy/promotion logic (the core 1b fix)

All three copy paths import `PLACE_FIELDS` from `all_models` and iterate:

```python
from app.models.all_models import PLACE_FIELDS

# Pattern used in all three sites:
fields = {f: getattr(src, f) for f in PLACE_FIELDS}
```

- **brainstorm.py** `_COPY_FIELDS` -> `PLACE_FIELDS`
- **events.py** `_ENRICH_FIELDS` -> `PLACE_FIELDS`
- **ideas.py** `copy_idea_to_trip()` ad-hoc list -> `PLACE_FIELDS` + `start_time`, `end_time`, `origin_idea_id`

### Part 7: Tests

**Backend tests** to update (remove dead field references, adapt to rename):

- [backend/tests/api/test_brainstorm_api.py](backend/tests/api/test_brainstorm_api.py)
- [backend/tests/api/test_brainstorm_gaps.py](backend/tests/api/test_brainstorm_gaps.py)
- [backend/tests/api/test_events.py](backend/tests/api/test_events.py)
- [backend/tests/api/test_idea_bin_api.py](backend/tests/api/test_idea_bin_api.py)
- [backend/tests/api/test_trip_days.py](backend/tests/api/test_trip_days.py)
- [backend/tests/api/test_llm_plan_trip.py](backend/tests/api/test_llm_plan_trip.py)
- [backend/tests/cross/test_brainstorm_concurrency.py](backend/tests/cross/test_brainstorm_concurrency.py)
- [backend/tests/cross/test_brainstorm_lifecycle.py](backend/tests/cross/test_brainstorm_lifecycle.py)
- [backend/tests/services/test_google_maps_service.py](backend/tests/services/test_google_maps_service.py)
- [backend/tests/services/test_llm_client.py](backend/tests/services/test_llm_client.py)
- [backend/tests/services/test_ripple_engine.py](backend/tests/services/test_ripple_engine.py)
- [backend/tests/services/test_idea_bin_service.py](backend/tests/services/test_idea_bin_service.py)

**New tests** to add:

- `test_idea_cross_trip_copy.py` — copy enriched idea, assert all 13 PLACE_FIELDS + start_time/end_time survive
- `test_event_round_trip.py` — idea -> timeline item -> bin -> timeline item, assert all fields survive

---

## 1a — Surface Enrichment Failures to the User

### Backend

**Step 1: `EnrichmentSummary` dataclass** in [backend/app/services/google_maps/base.py](backend/app/services/google_maps/base.py):

```python
from pydantic import BaseModel
from typing import Literal, Optional

class EnrichmentSummary(BaseModel):
    status: Literal["full", "partial", "none"]
    total: int
    enriched: int
    skipped: int
    reason: Optional[Literal[
        "quota_exceeded", "missing_api_key", "breaker_open",
        "network_error", "upstream_error"
    ]] = None
```

**Step 2: New `enrich_items_with_summary()` method** in `base.py`, sibling to `enrich_items()`. Delegates to the existing `enrich_items()` logic but:

- Captures the reason for failures by inspecting exception types in `enrich_item()` (new `_last_failure_reason` instance attribute, set in the except block):
  - `httpx.HTTPStatusError` with 429 or `OVER_QUERY_LIMIT` -> `"quota_exceeded"`
  - No API key detected at batch start -> `"missing_api_key"`
  - Breaker open -> `"breaker_open"`
  - `httpx.NetworkError` / timeout -> `"network_error"`
  - Else -> `"upstream_error"`
- Returns `(items, EnrichmentSummary)` tuple
- Keep `enrich_items()` unchanged (calls `enrich_items_with_summary` internally, discards summary)

**Step 3: Shared `EnrichmentStatus` schema** — define once, reuse in all responses.

Put in [backend/app/schemas/enrichment.py](backend/app/schemas/enrichment.py) (new file):

```python
from typing import Literal, Optional
from pydantic import BaseModel

class EnrichmentStatus(BaseModel):
    status: Literal["full", "partial", "none"]
    total: int
    enriched: int
    skipped: int
    reason: Optional[str] = None
```

**Step 4: Add `enrichment: Optional[EnrichmentStatus] = None` to four response schemas:**

- [backend/app/schemas/brainstorm.py](backend/app/schemas/brainstorm.py) — `BrainstormExtractResponse` and `PlanTripResponse`
- [backend/app/schemas/concierge.py](backend/app/schemas/concierge.py) — `ConciergeChatResponse` (for future LLM-extract-then-enrich intents like "find historical places") and `FindNearbyResponse` (for when `nearby_search` degrades)

When `status == "full"`, omit (set to None / don't include) to keep payloads small.

**Step 5: Update four endpoints to capture and return enrichment status:**

- [backend/app/api/endpoints/brainstorm.py](backend/app/api/endpoints/brainstorm.py) line ~184 (extract): call `enrich_items_with_summary()` instead of `enrich_items()`, attach summary to `BrainstormExtractResponse`
- [backend/app/api/endpoints/llm.py](backend/app/api/endpoints/llm.py) line ~27 (plan-trip): same change, attach to `PlanTripResponse`
- [backend/app/api/endpoints/concierge.py](backend/app/api/endpoints/concierge.py) `find_nearby` endpoint (line ~269): the endpoint calls `maps_service.nearby_search()` which can return 0 results or partial results. Build an `EnrichmentStatus` from the results (count how many have `place_id`), attach to `FindNearbyResponse`
- [backend/app/api/endpoints/concierge.py](backend/app/api/endpoints/concierge.py) `concierge_chat` endpoint (line ~173): not wired to enrichment today, but add the field to the response schema so it's ready. For now, always `None`. When we add LLM-extract-then-enrich intents (e.g. "find historical places near me"), the handler will populate it.

### Frontend

**Step 6: Per-item "!" indicator on all place cards** — defensive, applied everywhere.

An item is considered unenriched when `place_id` is null/missing (the definitive signal).

Tooltip text on hover: **"Map data unavailable"** (short and non-technical).

Apply to these four card rendering sites:

- [frontend/components/trip/BrainstormBin.tsx](frontend/components/trip/BrainstormBin.tsx): On each card in the grid and in the expanded detail drawer, if `!item.place_id`, render a small amber `AlertTriangle` icon (lucide, ~14px) in the top-right corner with `title="Map data unavailable"`.

- [frontend/components/trip/IdeaBin.tsx](frontend/components/trip/IdeaBin.tsx): Same pattern on idea cards.

- [frontend/components/dashboard/DashboardTripPlanner.tsx](frontend/components/dashboard/DashboardTripPlanner.tsx): On plan-trip preview item cards.

- [frontend/components/trip/ConciergeChatDrawer.tsx](frontend/components/trip/ConciergeChatDrawer.tsx): On `PlaceCardItem` (line ~103-162). Today `place_id` is always present from nearby_search results, but defensively: if `!place.place_id`, show the "!" icon in the top-right of the card image area (or title area if no image).

**Step 7: Batch-level enrichment status display** (optional, lightweight).

When an API response includes `enrichment` with `status !== "full"`:

- **DashboardTripPlanner**: small amber text line below the preview items: `"{skipped} of {total} places couldn't be loaded."` No reason detail — keep it simple.
- **BrainstormBin**: after extract completes, if response has `enrichment.status === "partial"` or `"none"`, show a subtle amber text line at the top of the brainstorm results.
- **ConciergeChatDrawer**: when `find-nearby` response has `enrichment.status !== "full"`, append a subtle amber note under the place cards: `"Some places couldn't be loaded."`.

### Tests

- `backend/tests/test_enrichment_status.py`: mock breaker open / mock 429 / drop API key -> assert correct `EnrichmentSummary` returned from `enrich_items_with_summary()`
- `backend/tests/api/test_brainstorm_api.py`: extend extract test to check `enrichment` field in response
- `backend/tests/api/test_llm_plan_trip.py`: extend plan-trip test to check `enrichment` field
- `backend/tests/api/test_concierge.py`: extend find-nearby test to check `enrichment` field in `FindNearbyResponse`

