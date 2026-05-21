# Chat Flows: Plan Trip vs Brainstorm

How the two AI-driven item-generation surfaces actually work end-to-end —
from user prompt → LLM response → Google Maps enrichment → persisted
`BrainstormBinItem` rows.

---

## 1. Plan Trip Chat (Dashboard)

One-shot flow from `DashboardTripPlanner.tsx`. The user types a single
prompt ("5-day Thailand…") and gets back a full preview of a trip.

### Frontend — `frontend/components/dashboard/DashboardTripPlanner.tsx:79`

- `POST /llm/plan-trip` with `{ prompt, timezone }`.
- On success, buffers `{role, content}` pairs for later seeding.
- On **Create Trip and Take Me There**:
  1. `POST /trips/` — create the trip.
  2. `POST /trips/{id}/brainstorm/bulk` — write the previewed items into
     the caller's bin.
  3. `POST /trips/{id}/brainstorm/messages/seed` — backfill the planning
     conversation as the first Brainstorm chat history.

### Backend endpoint — `backend/app/api/endpoints/llm.py:33`

1. `entitlements.enforce_brainstorm()` — gates free-tier usage.
2. `DashboardClient.plan_trip()` →
   `RoammateServiceV1.plan_trip()` (`backend/app/services/llm/services/v1/roammate_v1.py:228`).
3. `entitlements.bump_brainstorm_counter()` — counts against monthly quota.
4. `maps_svc.enrich_items_with_summary(items)` — enriches in parallel.
5. If no `start_date` came from the LLM/pre-extractor → defaults to
   "today in caller tz" so create-trip can auto-create Day 1.
6. `tz_svc.timezone_for(lat, lng)` on the first enriched item → returns
   the IANA tz for the destination (Apple Maps has no tz adapter, so
   this always uses Google).

### How LLM items are produced — `roammate_v1.py:228`

- `pre_extract(prompt)` deterministically pulls **city / country /
  num_days / budget_tier / start_date** out of the raw prompt
  (regex + heuristics) — cheap, runs before any LLM call.
- Loads `plan_trip_v1.txt` and substitutes `{city}`, `{country}`,
  `{num_items}` (≥ `num_days*3`, min 8), `{budget_tier}`, `{today}`,
  `{context_block}`.
- Calls `model.complete(..., response_schema=LLMPlanResponse, temperature=0.7)`
  — **structured output** enforced by the schema in
  `backend/app/schemas/llm.py:52`.
- Parses to `LLMPlanResponse` →
  `{user_output, trip_name, duration_days, start_date, map_output: [LLMItem]}`.
- Each `LLMItem` uses **abbreviated keys** (`t, d, cat, tc, dur, price,
  tags`) — cuts ~40% output tokens across a typical 10-item response.
- `llm_item_to_brainstorm()` (`roammate_v1.py:52`) maps each LLMItem to
  a BrainstormBinItem-shaped dict, **leaving `place_id`, `lat`, `lng`,
  `address`, `photo_url`, `rating` as `None`** — those get filled by
  enrichment next.

### How items are enriched with Google Maps — `backend/app/services/google_maps/base.py:307`

- `enrich_items_with_summary` checks API key + circuit breaker, then
  `enrich_items` runs with `asyncio.Semaphore(5)`.
- Per item, `enrich_item`:
  1. `find_place(title)` — text → place candidate.
  2. `_extract_place_id(candidate)`.
  3. `place_details(pid)` — full record → `_apply_details()` merges
     canonical fields (`place_id`, `lat`, `lng`, `address`, `rating`,
     `price_level`, `photo_url`, `types`).
  4. Falls back to the lighter `find_place` result if details fail.
- Failures set `_last_failure_reason`
  (`quota_exceeded` / `network_error` / `upstream_error` / `missing_api_key` / `breaker_open`);
  the breaker tracks success/failure.
- Returns an `EnrichmentSummary` (`full | partial | none`) which the
  frontend shows as the "X of Y couldn't be loaded" warning.

### How brainstorm items are created

- `/llm/plan-trip` does **not** write to the DB — it returns a preview.
- After the user clicks **Create Trip**, `POST /trips/{id}/brainstorm/bulk`
  (`brainstorm.py:335`) inserts the already-enriched items as
  `BrainstormBinItem` rows with `added_by="AI"`. No re-enrichment, no
  dedup at this stage.

---

## 2. Brainstorm Chat (inside a trip)

Multi-turn flow. **Chat** and **extraction** are split into two
endpoints — the chat turn never touches Maps or creates items.

### 2a. Chat turn — `POST /trips/{trip_id}/brainstorm/chat`

`backend/app/api/endpoints/brainstorm.py:177`

1. `require_trip_member` + `enforce_brainstorm`.
2. Loads the caller's history — `BrainstormMessage` rows scoped to
   `(trip_id, user_id)`.
3. `BrainstormChatClient.chat()` → `RoammateServiceV1.chat()`
   (`roammate_v1.py:154`):
   - `pre_extract` on the new user message for a tiny context block.
   - Loads `brainstorm_chat_v1.txt`, injects `{context_block}` and the
     packed persona descriptors.
   - `_trim_history` keeps the last 6 messages (~3 turns).
   - `model.complete(messages)` — **plain text reply**, no schema, no
     items extracted here.
4. Writes the user message + assistant reply as two `BrainstormMessage`
   rows, bumps the brainstorm counter, commits.

The chat turn alone never creates brainstorm items or calls Maps.

### 2b. Extract — `POST /trips/{trip_id}/brainstorm/extract`

`brainstorm.py:251` — this is what mines chat history into bin items.

1. Selects only `BrainstormMessage` rows where `extracted_at IS NULL`
   — decoupled from bin contents, so once items are promoted (deleted
   from `BrainstormBinItem`) or trashed we don't re-mine the same
   chat turns.
2. If nothing new → return early; no LLM call, no Maps, no counter bump.
3. `BrainstormChatClient.extract_items(history)` →
   `RoammateServiceV1.extract_items` (`roammate_v1.py:194`):
   - Loads `brainstorm_extract_v1.txt`.
   - `model.complete(messages, response_schema=LLMExtractResponse,
     temperature=0.3, max_tokens=LLM_MAX_TOKENS_EXTRACT)`.
   - Parses `LLMExtractResponse` → **discards `user_output`**, maps
     `map_output: [LLMItem]` via `llm_item_to_brainstorm()` (same
     skinny → bin-shaped mapping; place_id/lat/lng/etc. start as `None`).
4. **Maps enrichment** — identical path to plan-trip:
   `maps_svc.enrich_items_with_summary(raw_items, user_id, trip_id)`
   → parallel `enrich_item` with Sem(5), breaker, tracking.
5. **Dedup** — `deduplicate(raw_items, existing_rows)`
   (`backend/app/services/llm/dedup.py`):
   - Normalises titles (lowercase, strip accents, collapse whitespace,
     remove punctuation) for an exact-match pass.
   - Levenshtein distance for near-duplicates against the caller's
     existing `BrainstormBinItem` rows.
6. Inserts the survivors as `BrainstormBinItem` rows with `added_by="AI"`.
7. Stamps `extracted_at = now()` on the consumed `BrainstormMessage`
   rows **in the same transaction** as the bin inserts — that's what
   prevents re-extraction.
8. Returns the new rows + an `EnrichmentSummary` (only non-null when
   status ≠ `full`).

---

## TL;DR — side-by-side

| Step | Plan Trip (dashboard) | Brainstorm Chat (in-trip) |
|---|---|---|
| LLM call | one-shot `plan_trip` with `LLMPlanResponse` | two-phase: `chat` (free text) + `extract` (`LLMExtractResponse`) |
| What LLM emits | `trip_name`, `duration_days`, `start_date`, `map_output` | `map_output` (extract); free text (chat) |
| Item fields from LLM | `t, d, cat, tc, price, tags` — place_id/lat/lng = None | same |
| Maps enrichment | inline in `/llm/plan-trip` | inline in `/brainstorm/extract` only |
| Dedup | none (fresh trip) | yes, against caller's existing bin items |
| DB write of items | not here — happens in `/brainstorm/bulk` after create-trip | directly in `/brainstorm/extract` |
| Counter bump | yes, in `/llm/plan-trip` | yes, in `/chat`; not in `/extract` |
| Timezone inference | yes (Google Time Zone API on first lat/lng) | no |
| iOS-aware enrichment | yes (`X-Client-Platform: ios` → Apple Maps adapter) | yes (same header switch) |

---

## Key files

- `backend/app/api/endpoints/llm.py` — `/llm/plan-trip`
- `backend/app/api/endpoints/brainstorm.py` — `/chat`, `/extract`, `/bulk`, `/messages/seed`, `/promote`
- `backend/app/services/llm/clients/dashboard_client.py`
- `backend/app/services/llm/clients/brainstorm_client.py`
- `backend/app/services/llm/services/v1/roammate_v1.py` — pipeline impl
- `backend/app/services/llm/services/v1/prompts/` — `plan_trip_v1.txt`, `brainstorm_chat_v1.txt`, `brainstorm_extract_v1.txt`
- `backend/app/services/llm/pre_processor.py` — deterministic pre-extract
- `backend/app/services/llm/dedup.py` — normalise + Levenshtein dedup
- `backend/app/schemas/llm.py` — `LLMItem`, `LLMPlanResponse`, `LLMExtractResponse`
- `backend/app/services/google_maps/base.py` — `enrich_items[_with_summary]`, `timezone_for`
- `frontend/components/dashboard/DashboardTripPlanner.tsx`
