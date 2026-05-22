# Roammate — Development Status as of 2026-05-03

## Summary
Audit across all docs in `/docs` vs. backend (`/backend`), frontend (`/frontend`), and tests.

**Phase 1 is ~80–90% shipped.** The LLM pipeline, brainstorm flow, personas, groups + notifications, admin dashboard, and the maps service abstraction (v1/v2/mock + cache + breaker + tracker) are complete and tested. The biggest remaining gaps are:

1. **Enrichment failure UX** — silent failures, no user feedback.
2. **Persistence of enriched map data on `Event`** — blocks split-view sync and offline route rendering.
3. **Concierge intent dispatcher** wiring.
4. **Idea Bin LLM upgrade** — still uses comma-split.
5. **Frontend e2e test coverage** for admin / persona / profile components.

---

## 1. CRITICAL — Address before Phase 1 ships

### 1a. Enrichment degradation has zero user feedback
- **Doc:** `enrichment-degradation-ux.md` — 0% implemented.
- **Issue:** When Google Maps quota runs out, the API key is missing, or the breaker opens, items return without photo/address/lat-lng and the UI says nothing. Already tracked server-side (`GoogleMapsApiUsage.enriched_count` / `skipped_count`, `status`) but never surfaced.
- **Fix sketch:** Add `enrichment_status` to `BrainstormExtractResponse` and `PlanTripResponse` in `backend/app/schemas/brainstorm.py`; surface a banner in `frontend/components/trip/BrainstormBin.tsx` and `DashboardTripPlanner.tsx`.

### 1b. Enriched map data not persisted to `Event` / `IdeaBinItem`
- **Docs:** `architecture.md`, `Development-status-18-04-2026.md`.
- **Issue:** `BrainstormBinItem` and `IdeaBinItem` carry rich Maps fields, but `Event` does not persist lat/lng/photo/rating durably. Consequence: route polylines and split-view markers must re-fetch on every render; offline rendering impossible; split-view scroll-sync blocked.
- **Fix sketch:** Extend `Event` model with the same Maps field set; copy fields on promotion from bin → timeline.

### 1c. Concierge intent dispatcher missing
- **Docs:** `roammate-brainstorm.md`, `architecture.md`.
- **Issue:** `ConciergeChatClient` and prompt template exist, but no `/api/concierge/chat` endpoint or intent parser → mutation mapping (ShiftTimeline, MoveEvent, SwapEvent, FindNearby, SkipNext, etc.). The One-Tap Action Bar has only "Running Late" wired (Ripple).
- **Fix sketch:** Add concierge endpoint + intent dispatcher; wire remaining action-bar buttons.

---

## 2. HIGH — Mentioned but not yet built

### 2a. Idea Bin LLM upgrade
- **Doc:** `idea-bin-intelligence-plan.md` — explicitly deferred.
- **State:** `services/idea_bin.py` still does comma-split + Google Places. The upgraded LLM pipeline path is wired only inside Brainstorm. Plan calls for `ingest_from_text()` to use pre-extract → extract_items → enrich → dedup when `LLM_ENABLED`.

### 2c. Smart Timeboxing & buffer zones
- **Docs:** `architecture.md`, `roammate-brainstorm.md`, `Development-status-18-04-2026.md`.
- **State:** Travel-time chips render between adjacent events ✓, but no transit-aware scheduling, no impossible-day warnings, no drag-overlap red-block visual feedback. Conflict *detection* is in (max-prior-end), but conflict *repair suggestions* are not.

### 2d. Vibe Check morning prompt
- **Doc:** `roammate-brainstorm.md`.
- **State:** Component shell exists; "Low Energy → swap" mutation logic missing.

### 2e. Avatar upload endpoint
- **Doc:** `user-persona-implementation-plan.md`.
- **State:** `User.avatar_url` field + frontend crop modal ✓; `POST /users/me/avatar` (multipart) not found in `users.py`. Likely never wired to S3/static.

### 2f. Email change verification
- **Doc:** `user-persona-implementation-plan.md` (stub).
- **State:** Email can be changed without verification. Acceptable for MVP, but worth documenting the risk.

---

## 3. MEDIUM — Test suite gaps

`comprehensive-test-suite-plan.md` specifies ~270 tests across 9 sections. Current state: ~750 tests collected, ~150 of the *plan's* tests landed (~55% of plan, but coverage of shipped code is healthy).

Specific missing files from the plan:
- `test_roammate_v1.py` — envelope parsing (user_output / map_output wrapping).
- `test_llm_models.py` — provider-model response shape parity.
- Frontend Vitest specs for `PersonaPicker`, `OnboardingPersonaModal`, `EditProfile`, `useAdminAuth`, admin dashboard pages. Only 4 frontend test files exist (Timeline, IdeaBin, TripHub, store).

Infra gaps: no Postgres-variant test config (Numeric precision verified only on SQLite); no snapshot library for prompt diffs.

---

## 4. MEDIUM — Map UI polish (`map_ui_enhancements.md`)

Implemented: info windows, marker clustering, category-colored markers, fit-all/style-toggle/legend controls, leg duration labels, bidirectional click highlight.

Missing:
- Polyline entrance animation (progressive draw).
- Per-leg color-coded route segments (currently single indigo stroke for all legs).
- Map skeleton loader (commented but no visual).
- `<1h gap + leg data` single-dot variant (`add-time-duration-between-timelines.md`) — current code only renders gap dots when count > 0; verify if intentional.

---

## 5. PHASE 2 / 3 — Out of current scope but mentioned

From `roammate-brainstorm.md`, `dashboard-groups-brainstorm.md`, `llm-integration-plan.md` §9:

- LLM streaming (SSE) for chat/extract.
- Rate limiting on LLM endpoints (Redis quotas: 20 chats/hr, 5 extracts/hr, 3 plan-trips/hr).
- Dashboard "Today Widget" state machine (pre/in/post-trip variants).
- NLP Quick-Add with multi-trip routing.
- Voting consolidation (ideas + events) and Ripple decision consensus.
- Group-level library deep search + tagging UX.
- Weather-based proactive alerts → Ripple suggestion flow.
- Phase 3: affiliate links, email forwarding ingestion, push notifications, offline-first sync layer (Dexie/IndexedDB).
- Async retry queue for failed enrichments (heavy variant of §1a).

---

## 6. Architectural notes worth tracking

- `place_enricher.py` (proposed in `llm-integration-plan.md`) does not exist; the equivalent lives in `google_maps/base.py` (`enrich_items`). Functionally equivalent — leave as-is unless reorganizing.
- `Trip.group_id` and `IdeaBinItem.group_id` are in place — Phase 1 groups foundation is done.
- Notifications service (`notification_service.py`) supports the full event vocabulary from the plan; bell UI polls every 30s.

---

## Recommended order of attack

1. **Persist enriched fields on `Event`** (1b) — unblocks split-view sync and route rendering improvements.
2. **Surface enrichment status** (1a) — small, high-leverage UX fix.
3. **Concierge intent dispatcher** (1c) — completes the Phase 2 Concierge promise; high product value.
4. **Idea Bin LLM upgrade** (2a) — once #1 lands, this is mostly wiring.
5. **Avatar upload + email verify** (2e/2f) — small loose ends before any external launch.
6. **Frontend test coverage backfill** (§3) — prevents regressions as the above lands.
7. Then Phase 2 polish (split-view sync, map UI animations, smart timeboxing, vibe-check logic).
