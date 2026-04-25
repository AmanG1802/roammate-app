# LLM Integration Plan — V1 Pitfalls & V2 Design

## Overview

This document covers the full plan for LLM integration in Roammate: what V1 built, the bugs and design gaps found in V1, and the phased implementation plan to fix them and complete the missing features (concierge, token management, rate limiting, V2 service strategy).

**Core requirements driving all decisions:**
1. Provider-agnostic — swap OpenAI → Claude → Gemini via `.env`, no code changes
2. Configurable models — each operation (chat, extract, plan) uses its own model
3. Token-optimized — minimize tokens on every call
4. Token limit per chat — rolling window, configurable cap
5. No hallucinations — LLM extracts intent/names only; Google Places provides all real data

---

## What V1 Built (Current State)

### Architecture: 3-Layer Stack

```
Endpoints (brainstorm.py, llm.py)
    └── Clients (BrainstormChatClient, DashboardClient, ConciergeChatClient)
            └── Services (RoammateServiceV1)
                    └── Models (OpenAIModel | ClaudeModel | GeminiModel)
```

| Component | File | Status |
|-----------|------|--------|
| 3-provider abstraction (OpenAI/Claude/Gemini) | `services/llm/models/` | ✅ |
| RoammateServiceV1 (chat, extract_items, plan_trip) | `services/llm/services/v1/roammate_v1.py` | ✅ |
| Zero-LLM pre-processor (city, dates, budget, vibes) | `services/llm/pre_processor.py` | ✅ |
| Google Places enricher (find + details, 2 calls/item) | `services/llm/place_enricher.py` | ✅ |
| Levenshtein + place_id dedup engine | `services/llm/dedup.py` | ✅ |
| Token usage structured logging | `services/llm/token_tracker.py` | ✅ |
| 4 prompt templates (chat, extract, plan, concierge) | `services/llm/services/v1/prompts/` | ✅ |
| Abbreviated LLM schemas (t, d, cat, tc, dur, price, tags) | `schemas/llm.py` | ✅ |
| Registry factory (provider/model from config) | `services/llm/registry.py` | ✅ |
| Backward-compat shim | `services/llm_client.py` | ✅ |
| Brainstorm endpoints wired to LLM pipeline | `api/endpoints/brainstorm.py` | ✅ |

**Not yet built:**
- `/concierge/chat` endpoint (client class exists, endpoint missing)
- Mutating concierge intents (shift, move, remove events)
- `is_draft` on Event model
- Rate limiting (slowapi not installed)
- Token-based history trimming (V1 uses count: last 6 messages)
- Per-operation model selection (V1 uses one model for everything)

### Token Optimization Already in V1

| Technique | Where | Saving |
|-----------|-------|--------|
| Zero-LLM pre-processor | `pre_processor.py` | ~30-40% input tokens |
| Abbreviated LLM schema keys (`t`, `d`, `cat`) | `schemas/llm.py` | ~40% output tokens |
| Last-6-messages history trim | `roammate_v1.py` | Caps history cost |
| Google Places enrichment deferred to commit time | `place_enricher.py` | No API calls during chat |
| `LLM_MAX_TOKENS_EXTRACT`, `LLM_MAX_TOKENS_PLAN` caps | `config.py` | Hard per-call ceiling |

### What the Pre-Processor Extracts (Zero LLM Cost)

Before every LLM call, `pre_extract(text)` runs regex/dateutil extraction:
- City and country (from ~55-entry lookup table)
- Trip duration ("3 days", "a week")
- Group size ("4 of us", "solo", "couple")
- Budget tier ("budget", "luxury", "mid-range")
- Vibes/preferences (food, culture, nature, nightlife, etc.)
- Start dates via `dateutil.parser`

Result is injected into the system prompt as a compact `{context_block}` — replacing what the LLM would otherwise need to re-parse from raw prose.

### Prompt Templates

| File | Used by | Purpose |
|------|---------|---------|
| `brainstorm_chat_v1.txt` | `/brainstorm/chat` | Conversational travel ideation |
| `brainstorm_extract_v1.txt` | `/brainstorm/extract` | Extract structured items from chat history |
| `plan_trip_v1.txt` | `/llm/plan-trip` | Generate a trip plan from a prompt |
| `concierge_v1.txt` | (not yet wired) | In-trip conversational assistant |

---

## V1 Bugs

### Bug 1 — Retry swallows auth errors on first attempt

**File**: `services/llm/models/base.py:76`

```python
# CURRENT — retries everything on attempt 0, including 401 AuthenticationError
if status not in RETRYABLE_STATUS_CODES and attempt > 0:
    raise

# FIX — always check status code
if status not in RETRYABLE_STATUS_CODES:
    raise
```

**Impact**: Wrong API key silently retries 3 times before surfacing. Hides config errors, wastes time.

---

### Bug 2 — Pydantic v2 validation bypassed on LLM parse

**File**: `services/llm/services/v1/roammate_v1.py:200`

```python
# CURRENT — bypasses nested field validation (Category enum, price range)
parsed = LLMExtractResponse(**data)

# FIX — full Pydantic v2 validation including nested LLMItem fields
parsed = LLMExtractResponse.model_validate(data)
parsed = LLMPlanResponse.model_validate(data)
```

**Impact**: Invalid LLM output (bad category value, price out of 0-4 range) passes through silently.

---

### Bug 3 — OpenAI json_schema missing `strict` mode

**File**: `services/llm/models/openai_model.py:48`

```python
# CURRENT — schema is advisory; model can still produce non-conforming JSON
"json_schema": {"name": "response", "schema": schema}

# FIX — enforce strict schema adherence server-side
"json_schema": {"name": "response", "schema": schema, "strict": True}
```

**Impact**: Without strict mode, the model occasionally omits required fields or uses wrong types, causing parse failures that silently fall back to Bangkok data.

---

## V1 Design Gaps

### Gap 1 — New service instance created per request

**File**: `services/llm/registry.py:60-69`

```python
# CURRENT — new objects allocated on every request
def get_brainstorm_client() -> BrainstormChatClient:
    return BrainstormChatClient(build_service())
```

Every request creates `BrainstormChatClient` → `RoammateServiceV1` → `OpenAIModel`. `AsyncOpenAI` is lazy-initialized inside `OpenAIModel`, but since the model is new per request, that init happens every time — no connection pool reuse.

**Fix**: Application-scoped singleton initialized at startup in `services/llm/app_state.py`.

---

### Gap 2 — History trimming is count-based, not token-based

**File**: `services/llm/services/v1/roammate_v1.py:77-84`

```python
HISTORY_TRIM_COUNT = 6
# Keeps last 6 messages regardless of length
```

A user writing 500-word messages passes 6 × ~500 words ≈ 3,000 tokens of history before their new message. Violates requirement #4 (configurable token limit).

**Fix**: `tiktoken`-based rolling window — cap by tokens, not message count.

---

### Gap 3 — Single model for all operations (cost waste)

**File**: `services/llm/registry.py:40-50`

```python
# CURRENT — one LLM_MODEL for chat, extract, AND plan_trip
return model_cls(api_key=api_key, model=settings.LLM_MODEL)
```

`gpt-4o` is ~10x more expensive than `gpt-4o-mini`. Brainstorm chat does not need gpt-4o.

**Fix**: Separate config keys `LLM_CHAT_MODEL` (default: `gpt-4o-mini`) and `LLM_PLAN_MODEL` (default: `gpt-4o`).

---

### Gap 4 — Place enrichment is sequential

**File**: `services/llm/place_enricher.py:116-143`

```python
for item in items:
    candidate = await _find_place(client, title)   # wait ~150ms
    details = await _get_details(client, pid)      # wait ~150ms
```

10 items × 2 calls × ~150ms = **~3 seconds**. With `asyncio.gather`, this drops to ~150ms total.

---

### Gap 5 — Two Places API calls per item (avoidable cost)

`findPlaceFromText` → `getPlaceDetails` = 2 billable calls per item. The Places API v1 (`places.googleapis.com/v1/places:searchText`) returns all required fields (geometry, rating, hours, photos, types) in a single POST.

**Fix**: Migrate to Places API v1 — 50% cost reduction on enrichment.

---

### Gap 6 — No rate limiting

`slowapi` is not installed. No per-user or per-IP limits on any LLM endpoint. A single user can spam `/brainstorm/chat` indefinitely, burning API quota.

---

### Gap 7 — Token usage only logged, never persisted

`token_tracker.py` writes structured log lines to stdout only. No DB record means no per-user quotas, no cost reporting, no alerting on spend spikes.

---

### Gap 8 — Pre-processor city lookup is small and rigid (~55 cities)

"NYC", "New York City", "the Big Apple" all fail to match "new york". Only major tourist cities covered. Common abbreviations have no alias map.

**Fix in V2**: Expand to ~5K cities from a CSV + add alias map.

---

### Gap 9 — Concierge endpoint not wired (highest-value missing feature)

`ConciergeChatClient` exists. `concierge_v1.txt` prompt exists. The `/concierge/chat` HTTP endpoint does **not** exist. No intent classification schema, no dispatcher, no event mutations.

---

## Implementation Plan

### Phase 0 — Bug Fixes (PR: `fix/llm-v1-bugs`)

Three targeted fixes, one PR, zero new files:

| # | File | Change |
|---|------|--------|
| 0a | `services/llm/models/base.py:76` | Remove `and attempt > 0` from retry condition |
| 0b | `services/llm/services/v1/roammate_v1.py:199-201` | `(**data)` → `.model_validate(data)` for extract + plan_trip |
| 0c | `services/llm/models/openai_model.py:48` | Add `"strict": True` to json_schema format |

**Verification**: `pytest backend/tests/ -v` must stay fully green.

---

### Phase 1 — Singleton Registry + Per-Operation Models (PR: `feat/llm-singleton-models`)

**New file**: `services/llm/app_state.py`

```python
"""Application-scoped LLM instances — initialized once at startup."""
_brainstorm_service: BaseLLMService | None = None
_plan_service: BaseLLMService | None = None

def init_llm_services() -> None:
    """Call from main.py lifespan on startup."""
    global _brainstorm_service, _plan_service
    _brainstorm_service = build_service(model_override=settings.LLM_CHAT_MODEL)
    _plan_service = build_service(model_override=settings.LLM_PLAN_MODEL)

def get_brainstorm_service() -> BaseLLMService: ...
def get_plan_service() -> BaseLLMService: ...
```

**Modify** `registry.py` — add `model_override: str | None = None` parameter to `build_model()` and `build_service()`.

**Modify** `main.py` — wire `init_llm_services()` into FastAPI `lifespan` context manager on startup.

**New config keys** in `core/config.py`:
```python
LLM_CHAT_MODEL: str = "gpt-4o-mini"   # brainstorm chat + extract (~10x cheaper)
LLM_PLAN_MODEL: str = "gpt-4o"        # plan_trip (needs multi-step reasoning)
```

---

### Phase 2 — Token-Based History Trimming (PR: `feat/token-trim`)

**New file**: `services/llm/token_utils.py`

```python
import tiktoken

def trim_history_by_tokens(
    history: list[dict],
    system_prompt: str,
    model: str,
    max_context_tokens: int,      # settings.LLM_CHAT_MAX_CONTEXT_TOKENS
    reserved_output_tokens: int,  # settings.LLM_CHAT_RESERVED_OUTPUT
) -> list[dict]:
    """Walk history newest-to-oldest. Keep messages that fit within token budget.
    Full history always stays in DB — only the slice sent to the LLM shrinks."""
    budget = max_context_tokens - reserved_output_tokens
    budget -= count_tokens(system_prompt, model)
    kept = []
    for msg in reversed(history):
        tokens = count_tokens(msg["content"], model)
        if budget - tokens < 0 and kept:
            break
        budget -= tokens
        kept.insert(0, msg)
    return kept
```

**Modify** `roammate_v1.py` — replace `_trim_history(history)` with `trim_history_by_tokens(history, system_prompt, model, ...)` in `chat()`.

**New config keys**:
```python
LLM_CHAT_MAX_CONTEXT_TOKENS: int = 6000
LLM_CHAT_RESERVED_OUTPUT: int = 512
```

Add `tiktoken` to `requirements.txt`.

---

### Phase 3 — Parallel Enrichment + Places API v1 (PR: `feat/parallel-enrichment`)

**Rewrite `place_enricher.py`** entirely:

```python
_PLACES_V1_URL = "https://places.googleapis.com/v1/places:searchText"
_PLACES_V1_FIELDS = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.rating,places.priceLevel,"
    "places.regularOpeningHours,places.internationalPhoneNumber,"
    "places.websiteUri,places.photos,places.types"
)

async def _enrich_one(client: httpx.AsyncClient, item: dict) -> dict:
    """Single Places API v1 call per item. Returns item unchanged on failure."""
    if item.get("place_id"):
        return item
    title = item.get("title", "")
    if not title:
        return item
    try:
        place = await _search_place_v1(client, title)
        if place:
            _apply_v1_details(item, place)
    except Exception:
        log.warning("Enrichment failed for %r", title, exc_info=True)
    return item

async def enrich_items(items: list[dict]) -> list[dict]:
    """Parallel enrichment — all items enriched concurrently."""
    if not settings.GOOGLE_MAPS_API_KEY:
        return items
    async with httpx.AsyncClient() as client:
        return list(await asyncio.gather(*[_enrich_one(client, item) for item in items]))
```

**Impact**: 10 items: ~3s sequential → ~150ms parallel. 20 API calls → 10 API calls.

---

### Phase 4 — Rate Limiting (PR: `feat/rate-limiting`)

Add `slowapi` to `requirements.txt`.

**Modify `main.py`**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

Decorate all LLM endpoints: `@limiter.limit(settings.RATE_LIMIT_X)`.

**New config keys**:
```python
RATE_LIMIT_BRAINSTORM_CHAT: str = "30/minute"
RATE_LIMIT_BRAINSTORM_EXTRACT: str = "10/minute"
RATE_LIMIT_PLAN_TRIP: str = "5/minute"
RATE_LIMIT_CONCIERGE: str = "30/minute"
```

Redis is already available at `settings.REDIS_URL` — slowapi uses it for distributed rate counting across workers.

---

### Phase 5 — Token Usage Persistence (PR: `feat/token-persistence`)

**New DB model** in `models/all_models.py`:

```python
class LLMUsage(Base):
    __tablename__ = "llm_usage"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id"), nullable=True, index=True)
    operation = Column(String, nullable=False)   # chat | extract | plan_trip | concierge
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

`auto_migrate.py` adds this table on next startup — no Alembic script needed.

**Modify `token_tracker.py`** — add `track_and_persist(response, *, operation, db, user_id, trip_id)` that logs AND writes a `LLMUsage` row within the caller's transaction.

---

### Phase 6 — Concierge Endpoint (PR: `feat/concierge-endpoint`)

The highest-value missing feature. Architecture:

```
POST /api/concierge/chat
  → require_trip_member()
  → load today's events → pack_day_context()
  → classify_intent(message, context_snapshot)    ← LLM: returns typed JSON
  → TypeAdapter(ConciergeIntent).validate_python(raw_json)
  → dispatch(intent, trip_id, user, db)
      → require_trip_admin() for all mutating intents
      → _verify_event(db, event_id, trip_id)        ← ALWAYS before any mutation
      → call existing service (ripple_engine, event CRUD, etc.)
      → notification_service.emit() for every mutation
  → track_and_persist() token usage
  → return ConciergeResponse(reply, intent_type, mutations_applied)
```

#### Intent Taxonomy (`schemas/concierge.py` — new file)

| `intent_type` | Fields | Mutation | Role required |
|--------------|--------|----------|--------------|
| `shift_timeline` | day_index, delta_minutes | Yes | admin |
| `move_event` | event_id, new_start_time | Yes | admin |
| `remove_event` | event_id | Yes | admin |
| `add_event` | title, place_hint, time_hint, day_index | Yes | admin |
| `get_suggestions` | query, anchor_event_id | No | member |
| `unknown` | raw_message | No | member |

Implemented as a Pydantic discriminated union on `intent_type`.

#### Anti-hallucination and prompt injection defense

- **Event ID safety**: Every `event_id` from LLM output is verified via `_verify_event(db, eid, trip_id)` before any mutation. A hallucinated or injected ID that doesn't belong to this trip returns 404.
- **Prompt injection**: Classification and action are separated. The LLM only outputs a typed JSON intent — it has no capability to execute actions directly. Role gating in the dispatcher is the second line of defense.

#### New files

| File | Purpose |
|------|---------|
| `schemas/concierge.py` | `ConciergeIntent` discriminated union, `ConciergeRequest`, `ConciergeResponse` |
| `services/llm/concierge_dispatcher.py` | Maps each intent to existing service calls |
| `api/endpoints/concierge.py` | `POST /api/concierge/chat` |
| `services/llm/services/v1/prompts/concierge_classify_v1.txt` | Intent classification prompt |

#### `is_draft` on Event model

Add to `Event` in `models/all_models.py`:
```python
is_draft = Column(Boolean, default=False, nullable=True)
```

`auto_migrate.py` adds the column on startup. Events created by `plan_trip()` get `is_draft=True`. Frontend shows a Draft badge with Accept/Discard controls per block.

---

## PR Order and Dependencies

| PR | Branch | Depends on | Contents |
|----|--------|-----------|---------|
| **PR-0** | `fix/llm-v1-bugs` | — | Fix retry, Pydantic validate, strict json_schema |
| PR-1 | `feat/llm-singleton-models` | PR-0 | `app_state.py`, per-op model config, lifespan wiring |
| PR-2 | `feat/token-trim` | PR-1 | `token_utils.py`, tiktoken, update `roammate_v1.chat()` |
| PR-3 | `feat/parallel-enrichment` | PR-0 | Rewrite `place_enricher.py` with asyncio.gather + Places API v1 |
| PR-4 | `feat/rate-limiting` | PR-0 | slowapi setup, rate limit config keys, endpoint decorators |
| PR-5 | `feat/token-persistence` | PR-1 | `LLMUsage` DB model, `track_and_persist()` |
| PR-6 | `feat/concierge-endpoint` | PR-1, PR-4, PR-5 | Concierge schema, dispatcher, endpoint, prompt, `is_draft` on Event |

**PR-0 is a hotfix — merge first.** PRs 1–5 can be developed in parallel but should merge in this order to avoid conflicts on `main.py` and `router.py`.

---

## V2 Service Strategy

After Phase 6 ships, `RoammateServiceV2` upgrades the intelligence layer as a **new strategy alongside V1** — no regressions, toggle via `LLM_SERVICE_VERSION=v2` in `.env`. V1 stays untouched as fallback.

| V1 Limitation | V2 Approach |
|--------------|-------------|
| Count-based history trim | Token-based trim via `tiktoken` |
| Single-pass `plan_trip` | Multi-pass: themes (Pass 1) → items per day (Pass 2, parallel) → 30-min-buffer schedule |
| No anchor-awareness in plan_trip | Pack existing trip events into plan prompt context |
| Pre-processor ~55 cities | Expand to ~5K via CSV + alias map (nyc → new york, etc.) |
| No semantic dedup | `text-embedding-3-small` + cosine similarity (pgvector) |

V2 lives at `services/llm/services/v2/roammate_v2.py`.

---

## Configuration Reference

```bash
# Core toggle
LLM_ENABLED=true

# Provider — swap here, no code changes needed
LLM_PROVIDER=openai          # openai | claude | gemini

# Per-operation models (Phase 1)
LLM_CHAT_MODEL=gpt-4o-mini   # brainstorm chat + extract
LLM_PLAN_MODEL=gpt-4o        # plan_trip
LLM_MODEL=gpt-4o-mini        # fallback when specific keys not set

# Token budgets (Phase 2)
LLM_CHAT_MAX_CONTEXT_TOKENS=6000
LLM_CHAT_RESERVED_OUTPUT=512
LLM_MAX_TOKENS_EXTRACT=3000
LLM_MAX_TOKENS_PLAN=4000

# Rate limits (Phase 4)
RATE_LIMIT_BRAINSTORM_CHAT=30/minute
RATE_LIMIT_BRAINSTORM_EXTRACT=10/minute
RATE_LIMIT_PLAN_TRIP=5/minute
RATE_LIMIT_CONCIERGE=30/minute

# API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
GOOGLE_MAPS_API_KEY=...
```

---

## Verification Checklist

```bash
# After PR-0 — all existing tests must stay green
pytest backend/tests/ -v

# After PR-2 — token trim
LLM_ENABLED=false pytest backend/tests/services/test_llm_client.py -v

# After PR-3 — parallel enrichment (no API key = skips enrichment, must not error)
pytest backend/tests/ -k "brainstorm" -v

# After PR-4 — rate limiting enforced
# Send 31 requests to /brainstorm/chat within 1 minute → 31st must return HTTP 429

# After PR-6 — concierge smoke test (requires LLM_ENABLED=true + API key)
curl -X POST http://localhost:8000/api/concierge/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"trip_id": 1, "message": "Push everything back 30 minutes", "day_index": 0}'
# Expected: {"reply": "...", "intent_type": "shift_timeline", "mutations_applied": ["Shifted Day 0 by 30 minutes"]}

# Anti-hallucination check — bogus event ID must return 404
curl -X POST http://localhost:8000/api/concierge/chat \
  -d '{"trip_id": 1, "message": "Remove event 99999"}'
# Expected: HTTP 404

# Token persistence check
psql -c "SELECT operation, model, SUM(input_tokens), SUM(output_tokens) FROM llm_usage GROUP BY 1, 2 ORDER BY 1;"
```
