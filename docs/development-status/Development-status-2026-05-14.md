# Roammate — Development Status as of 2026-05-14

> Previous status: [Development-status-2026-05-03.md](./Development-status-2026-05-03.md).
> Owner: Aman Gupta · Branch: `aman/UI-enhancements`.

---

## TL;DR

Since 2026-05-03 the project has moved from **"Phase 1 ~80% shipped
with three critical gaps"** to **"Phase 1 functionally complete +
Phase 2 frontend polish landed."** The three critical gaps flagged
on May 3 (enrichment UX, persistent enriched fields on `Event`,
concierge intent dispatcher) are all closed. On top of that, today
we executed a six-wave frontend UX overhaul that was **not in any
prior plan** but was triggered by a fresh code review.

Today's net change: **6 commits, ~1,400 LOC across 21 files**, plus
three new docs. The frontend type-checks with zero errors and the
docker rebuild produced no compile warnings.

---

## 1. What we implemented today (2026-05-14)

All six commits on `aman/UI-enhancements`:

| Commit | Wave | Scope |
|---|---|---|
| `ac0405e` | (prior session) | "Implement Plan 18 and 19" — `[18] idea-bin-state-enhancement.md` + `[19] frontend-async-evaluation.md` |
| `adb092a` | Wave 1 | Silent-failure cleanup, concrete bug fixes, login polish |
| `f36f25a` | Wave 2 | Mobile responsiveness + `MapOverlayLayer` |
| `97bd256` | Wave 3 | Animation polish + a11y hooks |
| `6aa3eb1` | Wave 4+5 | Dialog roles + lazy-loaded heavy components |
| `4e859c0` | — | Test fixture fix (`day_date: null`) |

### 1.1 The six-wave plan (`docs/[21] frontend-ux-enhancement-and-bugfix.md`)

This plan was authored today after a code review surfaced a number of
silent-failure modes, mobile responsiveness gaps, and accessibility
holes. The waves shipped in order, each as its own commit.

**Wave 1 — silent-failure cleanup + bug fixes**

- New shared `Toast` provider (`frontend/components/ui/Toast.tsx`)
  with a framer-motion stack rendered via a Provider at the root
  layout.
- New `toast-bus.ts` so non-React callers (the Zustand store) can
  emit toasts without prop-drilling a hook.
- `lib/store.ts` mutations now report failures: `updateEventTime`,
  `reorderEvent`, `toggleEventSkip` revert their optimistic updates
  on failure; `moveIdeaToTimeline`, `moveEventToIdea`, `deleteTripDay`
  surface user-visible toasts.
- Dashboard: replaced 4 empty `catch {}` blocks with toast feedback;
  added inline error + retry UI for the trips fetch; skeleton cards
  replace the centered spinner; fixed `isLoading` getting stuck after
  `AbortController.abort()`.
- Trip page: error toasts for member fetch, role change, member
  remove.
- BrainstormChat: inline retry banner when chat history fails to
  load.
- `useAuth.tsx`: info toast when serving cached profile after a
  network error (no longer silent).
- Login: replaced fragile `error.startsWith('Account created')`
  string sniffing with explicit `{type, message}` state; added a
  Suspense fallback skeleton.
- Concierge drawer: stable `preAction` key (no more re-firing on
  every render), `mountedRef` guard around geolocation callbacks
  (no `setState` after unmount), `AbortController` per nearby
  search (rapid clicks no longer race).
- Concierge action bar: ripple-toast timer now cleans up on unmount;
  removed the silent local fallback that desynced from the server.
- Removed the dead `MoreVertical` button + unused import from
  Timeline header.
- VoteControl: reset `votersFetched` ref + voters list when path
  changes (prevents stale popovers when a card is re-keyed).

**Wave 2 — mobile responsiveness + `MapOverlayLayer`**

- New `MapOverlayLayer.tsx` with six named slots (`TopLeft`,
  `TopCenter`, `TopRight`, `BottomLeft`, `BottomCenter`,
  `TopBanner`) plus a container-width derived `useMapBreakpoint()`
  hook. Replaces five independent absolute-positioned overlays in
  `GoogleMap.tsx` that previously collided on narrow viewports.
- At `sm`: control column flips to a horizontal row, Layers/Legend
  collapse into a kebab menu, `Refresh Route` drops its label,
  `DayBadge` truncates, toasts render as a full-width banner.
- Dashboard: sidebar becomes a slide-in drawer below `md` with a
  hamburger trigger + backdrop; header padding scales; `New Trip`
  button hides its label on phones; create-trip modal width clamps
  to `(100vw - 2rem)`.
- Trip planner: plan + concierge modes use a tabbed view below `lg`
  (Timeline / Map / Ideas for plan, Timeline / Map for concierge)
  so the 3-column layout no longer breaks on narrow screens.
- Trip hub: hero `font-size: clamp()` bottoms out at `2.25rem` so
  it doesn't overflow phones; invite form stacks vertically on `sm`.

**Wave 3 — animation polish + a11y hooks**

- New `PageTransition.tsx` utility (framer-motion, respects
  `prefers-reduced-motion`).
- BrainstormChat: extract button fades+slides in via
  `AnimatePresence`; send button gains `active:scale` + aria-label;
  typing indicator gets `aria-live="polite"`.
- Timeline: replaced conflict border (2px width shift) with
  `ring-2` (no layout shift); grip handle hovers indigo + scales.
- VoteControl: voter popup gets `role="tooltip"` + `aria-hidden`.
- ConciergeChatDrawer: `role="dialog"` + `aria-modal` + Esc-to-close.
- NotificationBell: bell shakes when unread count increases (skipping
  first paint), unread badge scale-in via spring; aria-label includes
  unread count.

**Wave 4 — accessibility hardening**

- Confirmation modals (create trip, delete trip, delete day, remove
  member) get `role="alertdialog"` / `role="dialog"`, `aria-modal`,
  `aria-labelledby`; all wrap in `p-4` + `max-w-*` so they don't
  overflow phones.

**Wave 5 — performance**

- `GoogleMap` and `ConciergeChatDrawer` lazy-loaded via `next/dynamic`
  with `ssr: false`. The heavy `@googlemaps/*` and concierge bundles
  no longer ship in the initial chunks for `/trips`.

### 1.2 Net-new modules

- `frontend/components/ui/Toast.tsx` — global Provider + `useToast` hook
- `frontend/components/ui/PageTransition.tsx` — framer wrapper
- `frontend/components/map/MapOverlayLayer.tsx` — overlay coordinator
- `frontend/lib/toast-bus.ts` — module-level toast emitter for non-React callers

### 1.3 Net-new documentation

- `docs/[21] frontend-ux-enhancement-and-bugfix.md` — the wave plan
- `docs/[22] nextjs-upgrade.md` — Next 14 → 16 + React 19 upgrade plan
- `docs/roammate-sales-pitch.md` — sales/marketing knowledge base

---

## 2. Items from the original plan — status changes since 2026-05-03

The May 3 status doc flagged three **critical** items and several
**high/medium** items. Reconciling against the codebase:

### 2.1 Critical items — all three closed ✓

| ID | Item | Status | Evidence |
|---|---|---|---|
| 1a | Enrichment failure UX | **Done** | `76ef736` "enrichment failure surfacing with retry, route gate, and Pydantic compat fixes" |
| 1b | Persist enriched fields on `Event` | **Done** | `862d250` "unify place-field models (1b) and surface enrichment failures (1a)" + `ddd2d54` "persist route data to DB with staleness detection" |
| 1c | Concierge intent dispatcher | **Done** | `d67d9d6` "add concierge intent dispatcher with chat drawer and fix timezone handling" |

The concierge dispatcher is the most strategically important close —
Phase 2's signature feature now works end-to-end (running-late,
skip-next, find-nearby, free-form chat).

### 2.2 High / medium items — partial progress

| ID | Item | Status |
|---|---|---|
| 2a | Idea Bin LLM upgrade | Still pending. The plan in `[1] idea-bin-intelligence-plan.md` was deferred and remains so. |
| 2c | Smart Timeboxing & buffer zones | Partial. Travel-time chips render between adjacent events (Wave 2 prior). Transit-aware scheduling, impossible-day warnings, and conflict-repair suggestions are still **not** implemented. |
| 2d | Vibe Check morning prompt | Pending. Component shell still missing the "Low Energy → swap" mutation logic. |
| 2e | Avatar upload endpoint | Pending. Frontend crop modal exists, multipart `POST /users/me/avatar` does not. |
| 2f | Email change verification | Pending (acceptable for MVP). |

### 2.3 Frontend test coverage gaps (May 3 §3) — unchanged

The test plan from `[9] comprehensive-test-suite-plan.md` still has the
same gaps:

- Missing backend tests: `test_roammate_v1.py`, `test_llm_models.py`.
- Missing frontend Vitest specs for `PersonaPicker`,
  `OnboardingPersonaModal`, `EditProfile`, `useAdminAuth`, admin
  dashboard pages.
- Only 4 frontend test files exist (Timeline, IdeaBin, TripHub, store).

Today's frontend work added meaningful new surfaces (Toast,
MapOverlayLayer, PageTransition) without adding test coverage for
them. That's a deliberate trade-off for speed but should be revisited
before the next external release.

---

## 3. Items implemented today that were NOT in any prior plan

Listed for transparency, since this is now a meaningful slice of the
codebase:

### 3.1 Frontend UX overhaul (Waves 1–5)

The entire six-wave plan in `docs/[21]` was authored *today* in
response to a fresh review and immediately executed. None of the
following existed in any prior planning doc:

- The shared toast infrastructure.
- The `MapOverlayLayer` abstraction.
- The mobile-tabbed plan/concierge modes.
- The dashboard sidebar drawer pattern.
- The `prefers-reduced-motion` PageTransition utility.
- The lazy-loading of `GoogleMap` and `ConciergeChatDrawer`.
- The accessibility hardening across modals (dialog roles + labels).
- The bell-shake on new notifications.

The motivation was that prior planning had focused almost entirely on
*backend correctness* (LLM pipelines, enrichment, route persistence,
admin metrics) and *feature completeness* (concierge, personas,
groups). Quality-of-life UX — error feedback, mobile, a11y, perf —
had accumulated debt that was no longer ignorable.

### 3.2 Sales pitch doc

`docs/roammate-sales-pitch.md` — written today as a knowledge base
for the sales and marketing teams. Not engineering work strictly, but
captures the current product surface in pitchable form and lists
forward-looking roadmap items.

### 3.3 Next.js upgrade plan

`docs/[22] nextjs-upgrade.md` — scoped today after `docker compose
build` flagged a security advisory on Next 14.1.0. Plan only; not
implemented. The codebase is unusually well-positioned (all-client,
no `unstable_cache`, no `middleware.ts`, no `next.config.js`) so the
upgrade should be largely a version bump.

---

## 4. What's still missing

### 4.1 Carried over from May 3 — still open

- **Idea Bin LLM upgrade** (`[1] idea-bin-intelligence-plan.md`).
- **Smart Timeboxing / conflict repair** suggestions.
- **Vibe Check** mutation logic.
- **Avatar upload** endpoint.
- **Email change verification** flow.
- **Frontend test backfill** for personas, admin, and new UI utils
  (Toast, MapOverlayLayer).
- **Backend tests** for `roammate_v1` envelope parsing and
  `llm_models` parity.

### 4.2 New gaps introduced by today's work

- **Test coverage** for new modules: `Toast`, `toast-bus`,
  `MapOverlayLayer`, `PageTransition`. None of them have specs.
- **`forwardRef` simplification** under React 19 (deferred — will
  pair with the Next 16 upgrade).
- **Brainstorm streaming** — the BrainstormChat improvements stopped
  short of true token streaming because that requires a backend
  endpoint change.

### 4.3 Phase 2 / 3 items mentioned in early docs, still untouched

From `roammate-brainstorm.md` and `[3] llm-integration-plan.md` §9:

- LLM streaming (SSE) for chat/extract — concierge already streams;
  brainstorm does not.
- Redis-backed rate limiting on LLM endpoints.
- Dashboard "Today Widget" state machine (pre / in / post-trip).
- NLP Quick-Add with multi-trip routing.
- Voting consolidation (ideas + events) and Ripple decision
  consensus.
- Group-level library deep search + tagging UX.
- Weather-based proactive alerts → Ripple suggestion flow.
- Phase 3: affiliate links, email forwarding ingestion, push
  notifications, offline-first sync layer (Dexie/IndexedDB).
- Async retry queue for failed enrichments (heavy variant of §1a).

---

## 5. What we're looking at next — recommended order

Given current state (Phase 1 essentially done, frontend UX
modernized), the next phase has both a technical-debt track and a
feature track. They can run in parallel.

### 5.1 Technical-debt track (low risk, high leverage)

1. **Next.js 14 → 16 + React 19 upgrade** — plan exists at
   `docs/[22]`. Closes the npm security advisory, gets us on a
   supported version. Half-day effort.
2. **Avatar upload endpoint + email verify** (2e + 2f from May 3) —
   small loose ends before any external launch.
3. **Frontend test backfill** — Vitest specs for the four net-new
   modules from Waves 1–3 plus the personas/admin gaps from May 3.
4. **Idea Bin LLM upgrade** (`[1] idea-bin-intelligence-plan.md`) —
   the only originally-planned Phase 1 item still open. Wiring
   work, not new design.

### 5.2 Feature track (Phase 2 polish + Phase 3 prep)

1. **Booking integrations** — surface OpenTable / Resy / Booking.com
   links on Idea Bin and Timeline entries. Highest commercial value.
2. **Brainstorm token streaming** — match the concierge streaming
   UX; requires the backend SSE work.
3. **Mobile PWA → native app shell** — the live concierge benefits
   the most from push notifications and offline support. The Wave 2
   mobile-responsive work was a prerequisite for this.
4. **Itinerary export + public share links** — PDF day-by-day +
   public read-only trip URLs.
5. **Smart conflict resolver** — one-tap reflow suggestions when
   the timeline flags a conflict (2c follow-through).
6. **Calendar sync** (Google / Apple) — two-way bind.

### 5.3 Vision-level items (mentioned but not yet scoped)

- Trip templates & remixing.
- Budget tracking.
- Flight + accommodation email parsing.
- AI image grounding (Instagram URL → Idea Bin entry).
- Marketplace of verified local guides.
- Post-trip memories recap.

---

## 6. Verification snapshot (end of day)

- `npx tsc --noEmit` — **0 errors** (was 1 stale test-fixture error
  on `main`; closed by `4e859c0`).
- `docker compose build frontend` — **clean** (only the standard
  npm deprecation chatter on transitive deps).
- `docker compose up -d frontend` — **ready in 2.2s**.
- Routes probed (`/`, `/login`, `/dashboard`, `/trips`) — **all
  HTTP 200**, all compiled cleanly.
- Type errors, lint warnings, hydration errors — **none** introduced
  today.

---

## 7. Risk & watchlist

- **Test coverage** is the most material technical risk. The Wave
  1–5 changes are broad; if a regression slips in, current automated
  coverage won't catch it. Backfill before merge.
- **Next 14.1.0 security advisory** is open until the upgrade lands.
- **Backend hasn't moved today** — all today's work is frontend-only.
  Backend tasks from May 3 (idea-bin LLM upgrade, brainstorm
  streaming) need someone's attention soon to maintain pipeline
  health.
- The **`aman/UI-enhancements` branch** now contains seven commits
  (one from yesterday + six today) totaling ~1,400 LOC of frontend
  changes. Worth a deliberate review pass before merging to `main`.

---

## 8. Doc index updated today

```
docs/
├── [21] frontend-ux-enhancement-and-bugfix.md      (new — wave plan)
├── [22] nextjs-upgrade.md                          (new — upgrade plan)
├── Development-status-2026-05-14.md                (this doc)
├── roammate-sales-pitch.md                         (new — marketing)
```

Previous status: `Development-status-2026-05-03.md` (still valid as
historical baseline).
