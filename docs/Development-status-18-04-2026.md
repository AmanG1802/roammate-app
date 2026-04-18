# Roammate — Development Status (2026-04-18)

A snapshot of what's built, what's half-built, what's left in Phase 1, and how the remaining Phase 1 work splits into **Phase 1A (Intelligence)** and **Phase 1B (Spatial & Timeboxing)**.

---

## 1. Delivered (Phase 1)


| Item                                                                                                | Value it adds                                                                                                                                                   |
| --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Idea Bin ingestion** (paste text, comma/newline split, URL persistence)                           | Lets users dump places they're considering from any source into a single staging area before committing to a schedule — the lowest-friction on-ramp to the app. |
| **Manual Event CRUD** (create, update, delete, move-to-bin)                                         | The baseline "I want to put this on my timeline" primitive. Everything else (drag, ripple, vote) ultimately mutates this.                                       |
| **Drag-from-Bin → Timeline**                                                                        | Converts loose ideas into scheduled events with one gesture, making the Planning phase feel fluid rather than form-heavy.                                       |
| **Trip Roles & Multiplayer Planning** (admin / view_with_vote / view_only; invites; accept/decline) | Turns Roammate from a solo planner into a group-travel tool. Admin gating prevents chaos; view_with_vote lets non-admins weigh in without breaking things.      |
| **Voting on Ideas AND Events** (with tally + role gating)                                           | Group decisions become data, not DMs. Admins can see what the group actually wants before committing.                                                           |
| **Vote Transfer** (idea → event on scheduling; event → idea on move-to-bin)                         | Preserves group consensus across state changes — a vote isn't "lost" just because the admin moved an item between the bin and the timeline.                     |
| **Ripple Engine** (shift future events on delta, tz-aware, trip-isolated, admin-only)               | The core Concierge primitive — "running late by 30 min" becomes a single action instead of editing every subsequent event.                                      |
| **JWT Auth + Protected Routes**                                                                     | Baseline security and per-user data isolation for every other feature.                                                                                          |
| **Today Widget / Dashboard** (past / active / upcoming bucketing, smart default page selection)     | The "open the app and know what to do next" surface — converts Roammate from a planner into a daily travel companion.                                           |
| **Natural-language Quick Add** *(deprecated — to be replaced in Phase 1A)*                          | Currently works but too rigid; slated for removal in favor of the richer LLM pipeline.                                                                          |


---

## 2. Built but not in the original plan


| Item                                                                                                                       | Value it adds                                                                                                                                                       |
| -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Groups layer** (create group, invite members, attach trips to group, group-level roles)                                  | Supports recurring travel crews (family, friend group, club). A group is a persistent identity across many trips instead of re-inviting the same people every trip. |
| **Cross-trip Idea Library with Tags** (group-scoped library, tag search, provenance via `origin_idea_id`, cross-trip copy) | Travelers reuse ideas ("that restaurant Mom loved in Rome"). The library makes those ideas discoverable across every future trip the group plans.                   |
| **Notification System** (typed events, fan-out to impacted users, unread counts, mark-read)                                | Multiplayer planning is useless if collaborators don't know something changed. Notifications make the app feel live without requiring WebSockets yet.               |
| **Automatic Postgres Schema Sync** (diff SQLAlchemy metadata → live DB catalog)                                            | Developer-velocity multiplier — schema changes ship without writing migrations for every column tweak.                                                              |
| **Extensive Test Suite** (~439 tests across api / services / cross / schemas)                                              | Acts as living contract documentation and lets Phase 1A/1B ship aggressively without regressing Phase 1 fundamentals.                                               |


---

## 3. Partially Delivered

These items exist in the UI or as scaffolding but are **not wired to meaningful logic**. They look right in screenshots; they don't do real work yet.

- **Google Places / Google Maps integration** — Service wrapper exists and `find_place` is called during ingestion, but the app does not actually depend on live map data: no route rendering, no transit times, no coordinates-driven clustering. It's a placeholder call, not an integration.
- **"Timeline Map" Split View** — `GoogleMap` component exists in isolation; no scroll-to-pan sync between timeline and map, no route polyline between events.
- **One-Tap Concierge Action Bar** — UI shell rendered; only "Running Late" (Ripple) is functional. "Skip Next", "Find Coffee", "Chat Now" are not wired.
- **Vibe Check morning prompt** — Component rendered; the "Low Energy → swap hike for cafe" logic is not implemented (requires LLM + swap primitives).
- **Smart Timeboxing & Buffer Zones** — No transit-time calculation, no impossible-day warnings.
- **Drag-overlap Visual Warning** — Drag handlers work, but there's no "red block" feedback when an event is dragged into an overlapping slot.

---

## 4. Not Yet Built (Phase 1)

Grouped by the sub-phase that will deliver them:

### Phase 1A — Intelligence (LLM / AI-driven features)

- **Chat Now conversational concierge** (the product's top differentiator)
- **Advanced NLP / LLM Idea Bin ingestion** (replaces the deprecated Quick Add — one LLM pipeline serves both ingestion and concierge)
- **AI full-itinerary generation from anchors + loose preferences**

### Phase 1B — Spatial & Timeboxing

- **Real Google Maps API integration** (Places, Directions, Distance Matrix — with clearly scoped request/response shape)
- **Smart Timeboxing & Buffer Zones** (transit-aware scheduling, impossible-day warnings)
- **Conflict Resolution** (overlap detection, visual drag warnings, swap/repair suggestions)
- **Graph-based Routing / Day Clustering** (re-order a day by geographic clustering)
- **Timeline ↔ Map Split-View sync** (scroll timeline → pan/zoom map, highlight active event)

---

## 5. Phase 2 (Brief)

Deferred to after Phase 1 ships in full. Original Phase 2 plus items de-scoped from Phase 1:

- Proactive **Weather-based adaptation** (moved from Phase 1)
- **Offline-first architecture** (IndexedDB / SQLite on client, sync queue) (moved from Phase 1)
- **Affiliate Handoff & Deep Linking** (Skyscanner, Booking.com, GetYourGuide)
- **Email Forwarding → Itinerary** (TripIt-style confirmation parsing)
- **Unified Booking Wallet** (tickets, QR codes, PDFs per timeline event)
- **Dynamic Pricing Alerts** on unbooked library items
- **AI Booking Concierge** (live flight/hotel options inside chat)
- **Expense Tracking UI** (booked vs estimated)
- **In-trip Booking** via OpenTable / Fork APIs
- **Disruption Management** (flight-delay driven auto-adjustment)
- **End-to-End Document Encryption** for the Wallet

---

# Phase 1A — Intelligence

**Theme:** The concierge and ingestion flows are the product's moat. One well-built LLM pipeline serves all three features below — same intent schema, same place-resolution layer, same mutation surface.

## 1A.1 Advanced NLP / LLM Idea Bin Ingestion *(replaces Quick Add)*

**Value:**

- Users paste messy, heterogeneous input — a travel-blog paragraph, a WhatsApp message, a list, a single place name — and get back a clean, enriched, deduplicated set of Idea Bin items.
- Removes the current "one structured quick-add at a time" friction. Ingestion becomes the *first* AI touchpoint users experience, setting expectations for the concierge.

**Implementation:**

1. **Intent schema** — define a Pydantic `IngestIntent` returning a list of `{title, place_hint, time_hint, duration_hint, tags, source_snippet}` items.
2. **LLM call** — prompt an LLM (Claude or similar) with a structured-output JSON schema. System prompt anchors on Roammate vocabulary (trip, day, idea, event).
3. **Place resolution** — for each item, call Google Places `find_place` (Phase 1B dependency for production quality; placeholder OK until 1B lands) to attach `place_id`, coordinates, photo, hours.
4. **Dedup** — on ingest, soft-match against the trip's existing bin + library by `place_id` first, then normalized title.
5. **Tag inference** — reuse the LLM call to suggest tags; merge with existing `IdeaTag` rows.
6. **Rollback of Quick Add** — remove `QuickAddService`, `/quick-add` endpoint, and the Quick Add UI. Migrate tests accordingly.

## 1A.2 Chat Now Conversational Concierge

**Value:**

- The single highest-leverage feature in the product. Converts the app from "static itinerary editor" to "travel assistant that mutates the plan on demand."
- Example user phrases it must handle: *"Push everything back 2 hours", "Find a vegan place near my next stop", "Move the Colosseum to tomorrow afternoon", "We're too tired for the hike — swap it for something chill nearby."*

**Implementation:**

1. **Intent taxonomy** — define a closed set of `ConciergeIntent` variants:
  - `ShiftTimeline(delta_minutes, from_event_id?)` → calls existing Ripple Engine.
  - `MoveEvent(event_id, new_start)` → calls event update.
  - `SwapEvent(event_id, criteria)` → Phase 1B needed for "nearby"/"indoor"; for 1A, support swap with an existing bin item.
  - `FindNearby(category, anchor_event_id)` → Phase 1B dependency; stub returns bin items tagged accordingly in 1A.
  - `AddEvent(title, when, where?)` → reuses 1A.1 ingest + schedule.
  - `DeleteEvent(event_id)`, `SkipNext`.
  - `ExplainPlan` (read-only) — narrates today/tomorrow.
2. **Pipeline**: user text → LLM (with the user's current trip/day state packed into the prompt as structured context) → `ConciergeIntent` JSON → Python intent-dispatcher → endpoint call → returns updated state + a natural-language confirmation.
3. **Context packing** — bounded snapshot: current day's events, next N events, active trip members, user's role. Trim aggressively to stay under context budget.
4. **Safety rails** — every mutating intent requires admin role (same gating as Ripple). Non-admins see a read-only concierge. Confirmations shown before destructive actions (delete/skip).
5. **Chat transport** — REST `POST /api/concierge/chat` returning `{reply, intent, applied_changes}`. Streaming deferred to Phase 2.
6. **Audit trail** — persist each concierge action as a `Notification` so collaborators see "Alice asked the concierge to push everything back 2h."
7. **Wire "Chat Now" button** on the Concierge Action Bar.

## 1A.3 AI Full-Itinerary Generation

**Value:**

- Onboarding accelerator — a new trip goes from empty to "here's a reasonable first draft" in under a minute.
- Hooks the "meticulous planner" persona (they'll edit the draft) and the "spontaneous traveler" persona (they'll ship the draft as-is).

**Implementation:**

1. **Input form** — destination, date range, fixed anchors (flight arrivals/departures, hotel check-ins), loose prefs ("museums, food, light walking").
2. **Multi-pass LLM flow**:
  - Pass 1: break the trip into day themes (arrival/food day, history day, day-trip, etc.).
  - Pass 2: for each day, emit 3–5 `IdeaBinItem`s respecting anchors.
  - Pass 3: draft a schedule (depends on Phase 1B for realistic transit times; until then, use naive fixed buffers of 30 min).
3. **Output as draftable state** — all items created in the Idea Bin first, then scheduled events flagged `is_draft=True` so the user accepts/rejects per block. Avoids "AI overwrote my plan" complaints.
4. **Reuses 1A.1 place-resolution pipeline** — every generated item goes through Google Places before hitting the DB, so coordinates are real.
5. **Reuses 1A.2 concierge loop** — after generation, user can immediately say "make day 2 more relaxed" and re-run locally on that day.

**Shared infra across 1A.1 / 1A.2 / 1A.3:**

- Single LLM client module (`services/llm_client.py`) — model config, retry, structured-output enforcement.
- Single intent dispatcher — maps any structured intent to the existing endpoints, so LLM changes don't mean endpoint changes.
- Prompt templates stored as versioned files, not inline strings — makes eval and iteration tractable.

---

# Phase 1B — Spatial & Timeboxing

**Theme:** Make the plan *physically real*. Every feature below depends on Google Maps being a first-class dependency, not a placeholder.

## 1B.1 Real Google Maps API Integration

**Value:**

- Unlocks every other Phase 1B feature. Also raises the quality floor of Phase 1A (concierge "find nearby" becomes actually useful).

**Implementation:**

1. **APIs wired:**
  - **Places API** — `findPlaceFromText`, `placeDetails` (name, place_id, lat/lng, opening_hours, photo_reference, rating).
  - **Directions API** — route between two events, for rendering on the split-view map.
  - **Distance Matrix API** — N×M transit times for Smart Timeboxing and routing.
2. **Wrapper layer (`services/google_maps.py` — expanded):** typed request/response models; retry + exponential backoff; quota guarding; mock mode for tests (already in use).
3. **Caching** — Redis cache for `place_id → details` (long TTL) and origin-dest-mode → duration (24h TTL). Cuts cost ~90% in practice.
4. **Persistence** — denormalize `lat`, `lng`, `opening_hours_json`, `photo_url` onto `IdeaBinItem` and `Event` so we don't re-fetch on render.
5. **Key management** — server-side only. Frontend calls a Roammate endpoint, never Google directly, so keys don't leak and we control quota.

## 1B.2 Smart Timeboxing & Buffer Zones

**Value:**

- The core win for the meticulous-planner persona: "this day is impossible" / "you have 20 min to get between these two" shown proactively, not discovered during the trip.

**Implementation:**

1. **Per-day transit model** — for each adjacent event pair on a day, call Distance Matrix (mode defaults to driving, user-configurable per trip). Cache per-pair.
2. **Buffer heuristic** — required buffer = `transit_duration + user_buffer_pref (default 15 min)`.
3. **Day feasibility check** — sum of `event_duration + required_buffer` vs waking hours (default 8am–10pm). Flag overage.
4. **Surfacing:**
  - Inline warning badge next to each event: `⚠ 12 min tight` (transit > gap).
  - Day-level badge: `⚠ Day overbooked by 45 min`.
5. **Trigger points** — recompute on event create/update/delete and on ripple. Batched into a single background task per mutation.
6. **Endpoint** — `GET /api/trips/{id}/days/{day_id}/feasibility` returns structured flags; frontend renders.

## 1B.3 Conflict Resolution (Overlap & Drag Warnings)

**Value:**

- Makes the drag-and-drop UI trustworthy. Right now you can silently create overlapping events; this closes that hole.

**Implementation:**

1. **Overlap detector** — O(n log n) sweep over a day's events; returns a list of overlap pairs.
2. **Drag-time preview** — frontend pre-computes overlap as the user drags; the dragged block turns red on collision, with a tooltip showing the conflicting event.
3. **Commit-time enforcement** — backend `POST /events` and `PATCH /events/{id}` reject with a 409 + structured `{overlaps_with: [event_id]}` unless a `force=true` flag is sent (for intentional overlap, e.g., a walking tour that spans a lunch).
4. **Repair suggestions** — when an overlap exists, offer: (a) ripple from the overlapping event, (b) move earlier event to bin, (c) shorten earlier event. Surfaced as a modal on commit.

## 1B.4 Graph-based Routing / Day Clustering

**Value:**

- "Optimize this day" — reorders a day's events by geographic clustering to minimize total transit. Big quality win for users who throw ideas in and want the app to sort them.

**Implementation:**

1. **Anchors respected** — events with fixed `start_time` (user-marked) don't move.
2. **Clustering** — for non-anchored events, run 2-opt TSP approximation over Distance Matrix durations. With 3–8 events/day (typical), this is sub-second.
3. **Preview before apply** — return the proposed order with per-leg durations; user confirms before mutations commit.
4. **Endpoint** — `POST /api/trips/{id}/days/{day_id}/optimize-route`.
5. **Concierge hook** — `Optimize(day_id)` intent added to 1A.2 so "Make day 3 less exhausting" can call this directly.

## 1B.5 Timeline ↔ Map Split-View Sync

**Value:**

- The visualization promise in the original brainstorm — turns the app from "a list with times" into "a spatial story of your day." Also the natural surface on which route polylines (1B.1) and warnings (1B.3) render.

**Implementation:**

1. **Shared store** — a Zustand slice holds `activeEventId`. Timeline scroll updates it (via IntersectionObserver on event cards); map subscribes and pans/zooms to that event.
2. **Route polyline** — render Directions polylines between sequential events on the active day. Re-fetch on day change, cache by day signature.
3. **Bi-directional** — clicking a map marker scrolls the timeline to that event (symmetric UX).
4. **Performance** — only render the active day's polylines; lazy-load marker clusters for trips with many events.

---

## Dependency Order

Phase 1A and Phase 1B are largely **parallelizable**, with two cross-dependencies:

- 1A.2's `FindNearby` / `Swap nearby` intents become genuinely useful only once 1B.1 lands.
- 1A.3's schedule-draft pass gets real transit times only once 1B.2 lands.

Until 1B is ready, 1A ships with placeholder transit values (fixed 30-min buffer) and returns `"need-map-data"` for any nearby-search intent. That keeps 1A demo-able end-to-end without blocking on the maps work.

---

## Success Criteria for Closing Phase 1

- A new user can: create a trip, paste a blog URL, get a populated bin, generate a draft itinerary with AI, tweak it via Chat Now, see the route on the map, and get warned when they overschedule a day.
- Everything a trip admin does via the UI is also doable via the concierge.
- 100% of mutating concierge actions produce notifications.
- Test suite stays at or above 439 passing.

