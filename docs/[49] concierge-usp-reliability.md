# Concierge Service — Reliability, Robustness & USP Plan

## Context

The Concierge is Roammate's on-the-trip AI assistant: a chat that lets trip members make
real-time itinerary changes ("running late", "skip lunch", "find a cafe", "move dinner to
8") and ask questions ("what's next?", "my day"). The goal is to make it the product's
**USP** — extremely reliable, genuinely value-adding, and robust — by fixing correctness
gaps, giving the LLM real trip context to reason over, layering in high-value concierge
capabilities, and turning the chat into a **shared, trip-wide** experience for the group.

It is tightly coupled to the **Smart Ripple Engine** (timeline re-scheduler); most write
actions shift the timeline. Smart Ripple is being hardened separately in
`docs/[42] smart-ripple-robustness.md`. **This plan depends on [42] landing first** (it
relies on [42]'s ripple-on-write for move/add (A7/A8), the `find_nearby` anchor fix (A1),
the clean no-internal-commit error handling (A3), and `require_trip_editor` (A2)). It then
adds the NEW ripple capabilities the enhancements below require.

---

## 1. What the Concierge does today

- **Backend**: `api/endpoints/concierge.py` (6 endpoints), `services/concierge_executor.py`
  (intent→DB mutations), `schemas/concierge.py` (7 intents), LLM dispatch via
  `services/llm/clients/concierge_client.py` → `roammate_v1.concierge_dispatch()` returning
  structured `ConciergeResponse` (intent + user_message + params_json + requires_confirmation).
- **Web**: `ConciergeChatDrawer.tsx` + `ConciergeActionBar.tsx`; Zustand `useTripStore`;
  refetches `/api/events` after a confirmed action.
- **iOS**: `ConciergeStore.swift` + `TripConciergeView.swift` + `ConciergeCards.swift`;
  `@Published` state; `onEventsChanged()` reloads the trip after a mutation.
- **Flow**: free-text → `POST /chat` (LLM → 1 intent + draft params → action_card) →
  confirm → `POST /execute` → executor mutates DB (maybe Smart Ripple) → frontend refetches.
- **Persistence today**: `ConciergeMessage` is **per (trip_id, user_id)** — each member has a
  private thread.

### Capabilities (7 intents)
| Intent | Mutates | Ripple |
|--------|---------|--------|
| `shift_timeline` | start/end | yes |
| `find_nearby` | inserts event | yes |
| `move_event` | start/end/day | no (→ [42] A7) |
| `add_event` | inserts event | no (→ [42] A8) |
| `skip_event` | `is_skipped` | no |
| `explain_plan` / `chat_only` | none | no |
| query endpoints | none | no |

---

## 2. Quick bug fixes (concierge-specific; ripple write-path bugs are owned by [42])

- **B-1 — Fake travel times in the prompt.** `_build_travel_times()` (`concierge.py:120-127`)
  emits `"(will be computed on demand)"`; the LLM reasons with **no real travel data**. Fix:
  feed real leg durations (reuse `DayRoute.legs` when the day's `waypoint_fingerprint`
  matches, per [42] B2; else compute) into the prompt context. (Foundational.)
- **B-2 — Today-only context.** `_load_today_events()` loads only the current trip-local
  day. Fix: load **whole-trip** context (see §3 Multi-day).
- **B-3 — Stale executor docstring** ("UTC-aware TIMESTAMPTZ", false since the DATE/TIME
  split; also [42] A6). Update.
- **B-4 — `enforce_concierge` parity.** `/execute` calls `enforce_concierge(db, user)` without
  `trip=` (`concierge.py:256`) while `/chat` passes `trip=trip`. Align both paths.
- **B-5 — `_move` silently drops a time change** when `event.start_time` is null
  (`concierge_executor.py:209`). Either apply the new time or return a clear message.

---

## 3. Enhancements (selected scope)

### 3.1 Shared, trip-wide concierge chat  *(replaces per-user thread)*
One conversation per trip, visible to the whole group.
- **Data**: keep `ConciergeMessage.user_id` as the **author** (attribution), but load/scope
  history by `trip_id` only. `_load_history()` drops the `user_id` filter; messages carry
  author name/id so the UI can label "Aman:". Interleave author labels into the LLM history
  so the model knows who said what.
- **Write access**: a member may post / propose / confirm actions only if they are **Plus
  AND a trip editor** (`require_trip_editor` from [42] A2 + `enforce_concierge`). A single
  pending action_card is confirmed once by any eligible editor.
- **Read access**: **all trip members read** the thread (including non-Plus) — read-only for
  non-Plus / view-only members (an upsell surface). Gate posting, not reading.
- **Realtime**: out of scope — refetch the thread on open / after a send (matches today's
  no-socket model). Live sync via websockets is a documented follow-up.
- **Files**: `concierge.py` (history scoping, write gate, read endpoint), `schemas/concierge.py`
  (author fields), web `ConciergeChatDrawer.tsx` + iOS `ConciergeStore`/cards (author labels,
  read-only state).

### 3.2 Real travel-time context  *(fixes B-1; foundational)*
Populate the prompt with actual leg minutes from stored `DayRoute.legs` (fresh-fingerprint
reuse) or on-demand `directions()`. Enables the LLM and the validators below to reason about
feasibility.

### 3.3 Whole-trip multi-day awareness  *(fixes B-2)*
Load all trip days grouped with day headers (`Day 3 — 2026-06-13`), each event tagged
`[id=…]`. Cap the context to a token budget; for very long trips, render near days in full
and summarize distant days. `move_event`/`add_event` already accept `new_day_date`/`day_date`.

### 3.4 Persona-tailored recommendations
Load trip members' `User.personas`, summarize into a compact "group vibe" line in the prompt
(aggregate of all members, since the thread is shared). Influences `find_nearby` / suggestions.

### 3.5 Dry-run ripple previews  *(needs Ripple R1)*
The confirm card shows the **real** projected impact, computed **inline during `/chat`
dispatch**, not the LLM's guess.
- For `shift_timeline` / `move_event` / `add_event` / `find_nearby`, dispatch opens a
  **SAVEPOINT** (`db.begin_nested()`), applies the would-be mutation, calls
  `shift_itinerary(..., dry_run=True)`, captures the projected `[(event_id, new_start,
  new_end)]` + warnings, then **rolls back the savepoint** (nothing persists at dispatch).
- The projected impact + warnings ride back in `ConciergeChatResponse` (new `preview` field)
  and render in the action card ("Shifts 3 events; dinner now 8:40pm" + any warnings).
- `/execute` re-runs the same mutation for real (committed).

### 3.6 Conflict / feasibility validation  *(warn-and-allow, not block)*
During the dispatch preview, surface **warnings** (never hard-block): time overlaps,
travel-infeasible gaps (gap < real travel time), cross-midnight (from ripple), and
opening-hours violations (§3.7). Warnings render in the action card; the user can still
confirm.

### 3.7 Opening-hours awareness  *(needs Ripple R4)*
- **Store hours**: add an `opening_hours` (JSON) column to `TimelineItem`, populated from
  `place_details` during `find_nearby` / enriched adds (the Maps layer already returns
  `regularOpeningHours`).
- **Validate**: the dry-run ripple (R4) flags any event whose projected window falls outside
  its venue's opening hours; the warning surfaces in the preview card. Detection/warning only
  in v1 (consistent with warn-and-allow) — ripple does not refuse the shift.

### 3.8 Undo last action  *(last action only, anytime during the trip)*
- New table **`ConciergeAction`** (`trip_id`, `user_id`, `intent`, `inverse_patch` JSON,
  `created_at`, `undone_at`). On every successful `/execute`, the executor records an
  `inverse_patch` capturing prior state of **every** event the action touched (anchor + all
  ripple-shifted events): prior `(day_date, start_time, end_time, is_skipped)`; for adds, the
  inserted event id (inverse = delete); for skips, the prior flag.
- New `POST /{trip_id}/undo` reverts the most recent not-yet-undone action for the trip
  (any eligible editor), applies the inverse patch, marks `undone_at`, emits a system message
  + notification. UI shows an "Undo" affordance on the last action card.

---

## 4. Smart Ripple Engine — NEW functionality required (additive to [42])

- **R1 — Dry-run mode.** `shift_itinerary(..., dry_run: bool = False)`: when true, compute the
  full cascade in-memory and **return projected shifts without committing** (no DB write;
  works inside the caller's SAVEPOINT). Return a structured result: projected
  `[(event_id, new_start, new_end)]` plus `warnings` (overlap, cross-midnight,
  opening-hours). Builds cleanly on [42] A3's "no internal commit/rollback; re-raise with
  `shifted_so_far`" refactor.
- **R4 — Opening-hours-aware warnings.** During the cascade, if a (possibly shifted) event's
  window falls outside its `opening_hours`, append an opening-hours warning to the result.
  Detection only — does not block or re-order (warn-and-allow). Requires the new
  `TimelineItem.opening_hours` column.

*Not needed (deselected):* R2 cross-day cascade, R3 backward compaction.

---

## 5. Files to modify

| File | Changes |
|------|---------|
| `backend/app/services/smart_ripple.py` | R1 `dry_run` mode (no commit, return projected + warnings), R4 opening-hours warnings |
| `backend/app/services/concierge_executor.py` | dry-run/preview path (SAVEPOINT simulate→rollback), record `inverse_patch` on execute, undo executor, populate `opening_hours` on add/find_nearby, B-5 move fix, B-3 docstring |
| `backend/app/api/endpoints/concierge.py` | trip-wide `_load_history`, author attribution, write gate (`require_trip_editor`+Plus), read access for non-Plus, inline preview in dispatch, multi-day + real-travel-time + persona context builders, conflict/hours warnings in response, `POST /undo`, B-4 parity fix |
| `backend/app/schemas/concierge.py` | `preview`/impact + `warnings` fields, author fields, undo request/response |
| `backend/app/models/all_models.py` | new `ConciergeAction` table; `TimelineItem.opening_hours` JSON column |
| Alembic migration | `ConciergeAction` + `opening_hours` column |
| `backend/.../prompts/concierge_dispatch_v1.txt` (or v2) | multi-day context, persona/group-vibe line, real travel times, opening-hours guidance |
| `backend/app/services/roles.py` | `require_trip_editor` (shared with [42] A2) |
| Web `ConciergeChatDrawer.tsx`, `ConciergeActionBar.tsx` | author labels, read-only state for non-Plus, real-impact preview + warnings in action cards, Undo affordance, multi-day summary |
| iOS `ConciergeStore.swift`, `TripConciergeView.swift`, `ConciergeCards.swift`, `Models/Concierge.swift` | same as web, SwiftUI-native |
| `backend/tests/` | preview/undo/opening-hours executor + ripple dry-run + shared-history access + auth-parity tests |

---

## 6. Verification

1. **Targeted backend tests**
   ```
   cd backend && pytest tests/ -k "concierge or ripple or preview or undo or opening" -q
   ```
   New + existing concierge/ripple tests green.
2. **Full suite**: `cd backend && pytest -q` — no regressions across ~480 tests.
3. **Manual — shared thread (3.1)**: as member B (Plus editor), confirm member A's messages
   and actions appear in one thread with author labels; as a non-Plus member, confirm
   read-only (no compose / no confirm). Use `debug-db` to inspect `concierge_message` rows.
4. **Manual — real preview (3.5)**: ask "push everything 45 min"; confirm the card shows the
   true projected times before confirming, and that re-fetching the trip pre-confirm shows
   **nothing persisted** (savepoint rollback). Confirm → `debug-db` shows the committed shift.
5. **Manual — opening hours (3.7)**: add/move an event past its venue's closing time; confirm
   the card shows an opening-hours warning but still allows confirm.
6. **Manual — undo (3.8)**: run a shift that cascades several events, tap Undo, confirm every
   touched event returns to its prior time via `debug-db`; a second Undo is a no-op.
7. **Manual — travel context (3.2)**: with two far-apart events, confirm the concierge's
   feasibility warnings reflect real driving time (not placeholders).

---

## 7. Sequencing notes
- **Land plan [42] first** (ripple-on-write, A3 error handling, `require_trip_editor`).
- Suggested order here: B-fixes + real travel-time context (3.2) → multi-day (3.3) →
  shared chat (3.1) → dry-run preview + validation (3.5/3.6) → opening hours (3.7) →
  undo (3.8) → persona polish (3.4).
- Each surface change must ship to **both** web and iOS (per project convention).
