# Roammate Frontend — Bug Fix & UX Enhancement Plan

> **Deliverable target:** Upon approval, this file will be saved to
> `docs/[21] frontend-ux-enhancement-and-bugfix.md` (per user request).
> **Scope:** `frontend/` only. No backend changes.
> **Date:** 2026-05-14

---

## Context

The frontend has reached a feature-complete milestone (login → dashboard →
trip hub → brainstorm/plan/concierge/people). Recent commits have layered in
streaming chat, idea-bin intelligence, timeline polish, and the concierge
drawer. Functional coverage is solid, but a focused review uncovered:

1. **Silent failure modes** — multiple `catch {}` blocks swallow errors that
   leave the user staring at stale/optimistic UI with no feedback.
2. **Mobile is structurally broken** — the 3-column trip-planner and fixed
   `w-60` sidebar collapse below ~768px.
3. **Animation coverage is inconsistent** — Timeline/IdeaBin/Drawer have rich
   framer-motion choreography, but Brainstorm, Dashboard, and route
   transitions feel abrupt by comparison.
4. **Accessibility is sparse** — only a handful of `aria-*` attributes
   across the entire app; drag-drop is mouse-only; modals lack focus traps.
5. **A few real bugs** — dead buttons, leaked event listeners, stale refs,
   race conditions in rapid vote/concierge clicks.

This plan groups the work by **risk × impact** so the team can ship in
focused waves rather than a single mega-PR. Each item cites the offending
file:line so it can be picked up directly.

---

## Wave 1 — Critical bugs & silent failures (ship first)

Goal: stop losing user actions to swallowed errors and dead UI.

### 1.1 Replace empty `catch {}` blocks with user-visible feedback

A shared toast utility already exists for the trip page; reuse it.

| File | Line | Current | Fix |
|------|------|---------|-----|
| `app/dashboard/page.tsx` | 78 | persona save silently fails | Toast "Couldn't save preferences — retry?" |
| `app/dashboard/page.tsx` | 96, 179, 192 | invitation accept/decline swallows | Toast + revert optimistic state |
| `app/dashboard/page.tsx` | 143–147 | trips fetch error logged only | Inline error card with retry button |
| `app/trips/page.tsx` | 80 | members fetch silent | Inline "Couldn't load members" row |
| `app/trips/page.tsx` | 141 | role update silent | Toast + revert dropdown |
| `app/trips/page.tsx` | 335–358 | `moveEventToIdea` silent | Toast + revert optimistic move |
| `lib/store.ts` | 239–305 | `moveIdeaToTimeline` 3× swallows | Throw → caller toasts → revert |
| `components/trip/BrainstormChat.tsx` | 36–38 | chat load fails silently | Inline retry banner |
| `hooks/useAuth.tsx` | 49–56 | stale localStorage fallback silent | Banner: "Showing cached profile — offline" |

**Pattern to adopt:** mutation functions in `lib/store.ts` should always
`throw` on failure; UI callers wrap in try/catch and revert + toast.

### 1.2 Fix dropped abort / loading state

- `app/dashboard/page.tsx:147` — `setIsLoading(false)` is gated on
  `!aborted`, but `isLoading` starts `true` and never clears on abort. Move
  `setIsLoading(false)` into a `finally` outside the abort guard.

### 1.3 Concrete bugs

- **Dead button** — `components/trip/Timeline.tsx:399` `MoreVertical` icon
  has no handler. Either wire it to the existing event-detail panel or remove.
- **Event-listener leak** — `app/trips/page.tsx:89–98` dropdown click-outside
  handler is registered but the cleanup `return` is missing.
- **Stale `pendingRole`** — `app/trips/page.tsx:756` cancel doesn't reset
  `pendingRole`; reopening dropdown shows old selection.
- **Voters ref reuse** — `components/trip/VoteControl.tsx:101–103`
  `votersFetched` ref never resets when `id`/`kind` change; reset in an
  effect keyed on `${kind}:${id}`.
- **Geolocation callback after unmount** —
  `components/trip/ConciergeChatDrawer.tsx:363–375` calls `updateMessage`
  from a geolocation callback with no `isMounted` guard.
- **Rapid-click race** — `ConciergeChatDrawer.tsx:411` `doNearbySearch`
  needs an `AbortController` per call so a slow first request doesn't
  overwrite a fast second one.
- **Vote race** — `VoteControl.tsx:137–167` `cast()` uses stale `tally`
  if double-clicked. Move tally into a ref or queue via a small reducer.
- **Cache key** — `ConciergeChatDrawer.tsx:231` `JSON.stringify(preAction)`
  is unstable across renders; memoize with a stable id.

### 1.4 Auth/login polish

- `app/(auth)/login/page.tsx:84–87` — replace
  `error.startsWith('Account created')` with an explicit
  `{ type: 'success' | 'error', message: string }` state.
- `app/(auth)/login/page.tsx:192` — `<Suspense>` has no fallback; add a
  skeleton matching the form so slow networks don't show a blank page.

---

## Wave 2 — Mobile responsiveness pass

Goal: make the app usable below 768px. Currently the plan-mode 3-column
layout, dashboard sidebar, and trip hero are all desktop-only.

### 2.1 Dashboard

- `app/dashboard/page.tsx:284–318` — sidebar is fixed `w-60`. Convert to a
  drawer on `< md:` (slide from left with a hamburger trigger). Reuse the
  existing `ConciergeChatDrawer` motion pattern.
- Header `p-8` → `p-4 md:p-8`.
- "Create Trip" modal `max-w-lg` → `max-w-[calc(100vw-2rem)] sm:max-w-lg`.
- Add skeleton cards (3× placeholder) to `TripGrid` (line 695) instead of
  a centered spinner.
- Add empty-state for *filtered* trips (currently only empty for "no trips
  at all").

### 2.2 Trip planner (`app/trips/page.tsx:436–443`)

- **Plan mode** (`w-[420px] / flex-1 / w-80`): on mobile, switch to a
  **tabbed view** — Timeline / Map / Ideas — with the existing mode tab
  bar gaining a sub-row. Persist last sub-tab in `sessionStorage`.
- **Concierge mode** (`w-[380px]` sidebar): on mobile, stack day selector
  above map; collapse to chips.
- **People tab**: cap scroll container with `max-h-[calc(100dvh-...)]`.

### 2.3 Map pane floating controls — collision & overflow fix

**The problem.** The map currently has **five independent
absolute-positioned overlays** stacked over `GoogleMap`, none of which are
aware of each other. As the browser width shrinks, they overlap,
truncate, and become unclickable.

Current overlays (all in `frontend/components/map/GoogleMap.tsx`):

| # | Element | Position | File:line |
|---|---------|----------|-----------|
| A | Control column (Fit / Layers / Fullscreen / Legend) | `top-4 right-4` | 897 |
| B | RefreshRoute pill + context message | `top-4 left-1/2 -translate-x-1/2` | 1051 |
| C | DayBadge ("Day · Tue, May 12" / "Live Route View") | `top-4 left-4` | 1093 |
| D | Toast (errors / info / success) | `top-20 left-1/2 -translate-x-1/2` | 1122 |
| E | Legend popover | `bottom-6 left-4` | 929 |

And in `app/trips/page.tsx:576` there is a **sixth** overlay (the live-day
selector pill) at `bottom-6 left-1/2 -translate-x-1/2` that collides with
**E** on narrow widths.

At ≤ ~900px:
- **C** (DayBadge, left) + **B** (Refresh, centered) + **A** (4-button
  column, right) all sit on the same `top-4` row and overlap.
- **B**'s `Refresh Route` label is full uppercase tracking-widest text —
  ~140px wide before the icon — and bleeds under **A**.
- **D** (toast) reuses `left-1/2 -translate-x-1/2` at `top-20`, but with
  `max-w-md` (448px) it overflows the viewport on phones.
- At ≤ ~600px the whole top row becomes a stacked mess; clicks land on
  the wrong button.

**The fix — a single `MapOverlayLayer` with responsive zones.**

Introduce one wrapper component that owns the four corners + a top-center
slot, with breakpoint-aware behavior:

```
┌─────────────────────────────────────────────────────────┐
│  [C DayBadge]                       [A Control column]  │  top-zone
│                                                          │
│                 [B Refresh Route]                        │  centered
│                 [D Toast]                                │
│                                                          │
│  [E Legend]                       [F Live-day pill]     │  bottom-zone
└─────────────────────────────────────────────────────────┘
```

Responsive rules (Tailwind breakpoints):

1. **`≥ lg` (current behavior)** — corners stay as-is.
2. **`md` (640–1024px)** —
   - **A** becomes a **horizontal row** (`flex-row`) at `top-4 right-4`
     instead of a column, so it doesn't intrude into the centered slot.
   - **B** drops its uppercase label and shows icon-only with a tooltip
     (keep label on `lg:` and up).
   - **D** toast width: `max-w-md → max-w-[calc(100vw-2rem)]`.
3. **`sm` (≤ 640px)** —
   - **C** (DayBadge) moves to the **bottom-left** (so it can't collide
     with the top row), or alternatively collapse into a small chip
     showing only the date number.
   - **A** condenses to **2 buttons visible + an overflow `…` menu**
     (kebab popover) that reveals Layers + Legend; Fit + Fullscreen
     remain primary.
   - **B** RefreshRoute moves to the **bottom-center** as a FAB so it
     never overlaps the top controls. The context message renders
     **above** the FAB (`bottom: calc(100% + 8px)`).
   - **D** toasts also reposition to `top-4 left-4 right-4` (full-width
     bar) instead of fixed-width centered pill.
   - **E** (Legend) and **F** (Live-day pill) stack: legend collapses
     into a button that opens a bottom-sheet on tap, live-day pill
     becomes the only bottom-center element.

**Implementation notes:**

- Create `frontend/components/map/MapOverlayLayer.tsx` exporting named
  slots: `<MapOverlay.TopLeft>`, `<TopCenter>`, `<TopRight>`,
  `<BottomLeft>`, `<BottomCenter>`, `<BottomRight>`. Slot styles use
  `pointer-events-none` on the wrapper + `pointer-events-auto` on
  children so the rest of the map remains pannable.
- Add a `useMapBreakpoint()` hook (or just Tailwind `md:`/`sm:` classes
  on each child) so layout shifts happen with no JS.
- The Live-day pill in `app/trips/page.tsx:576` should be moved into the
  new layer too — currently the trip page reaches into the map's
  visual space without coordination.
- Add `prefers-reduced-motion` respect when moving B between top-center
  and bottom-center on resize (skip the layout transition).

**Files changed in this section:**
- `frontend/components/map/GoogleMap.tsx` — replace the five inline
  absolute divs with `<MapOverlayLayer>` slots.
- `frontend/components/map/MapOverlayLayer.tsx` — **new**.
- `frontend/app/trips/page.tsx` — move the live-day pill (line 576)
  into the overlay layer slot.

**Verification:**
- Resize Chrome from 1440 → 320px in 100px steps; confirm no overlap at
  any width, all buttons remain clickable, no horizontal scroll.
- Force a long DayBadge label (e.g. German locale "Donnerstag, 22.
  Januar") and confirm it truncates with `truncate max-w-[...]` instead
  of wrapping under the centered button.
- Trigger a toast while RefreshRoute is loading at 375px width —
  confirm the toast does not visually merge with the FAB.

### 2.4 Trip hub (`app/trips/[id]/page.tsx`)

- Hero title `clamp(3rem, 7vw, 7.5rem)` is too large on phones. Use
  `clamp(2rem, 8vw, 7.5rem)` and reduce line-height on small screens.
- Invite form (line 505–554) — stack vertically below `sm:`, drop
  `min-w-[100px]` on the button.

---

## Wave 3 — Animation & micro-interaction polish

Goal: bring Brainstorm, Dashboard, and route transitions up to the
choreography level of Timeline/Drawer.

**Library policy:**
- **Framer Motion** — use for *in-app* motion: drawers, modals, list
  enter/exit, layout transitions, micro-interactions. Already installed
  and used in Timeline / IdeaBin / ConciergeChatDrawer.
- **GSAP + ScrollTrigger** — keep, **landing-page only**
  (`frontend/app/page.tsx`). Powers the hero timeline, magnetic buttons,
  ScrollTrigger section reveals, feature-card stagger, showcase
  parallax, and floating icons. Framer can't cleanly replicate
  scroll-tied imperative timelines or `ease: "elastic.out(1, 0.3)"`
  physics. Do **not** import gsap anywhere outside `app/page.tsx`.
- To avoid GSAP shipping in every route bundle, gate it behind a
  dynamic import: `app/page.tsx` already runs on its own route, but
  verify `next build` chunk analysis shows gsap only in the landing
  chunk. If it leaks (e.g. via a barrel re-export), fix the import path.

### 3.1 Route & page transitions

- Wrap each top-level page in a shared `<PageTransition>` using
  `motion.div` with `initial={{ opacity: 0, y: 8 }}` /
  `animate={{ opacity: 1, y: 0 }}` / `exit` — keyed on pathname via
  `AnimatePresence` in the root layout.
- Keep the existing View Transitions API usage for back/forward; the
  framer wrapper is for in-app forward navigation.

### 3.2 BrainstormChat (`components/trip/BrainstormChat.tsx`)

- **Streaming**: server already supports streaming on the concierge path
  — extend to brainstorm. Replace the all-at-once append at line 78–85
  with token streaming. Show a blinking caret on the in-progress bubble.
- **Extract button appearance** (line 221–230): wrap in `AnimatePresence`
  so it fades + slides in when `hasAssistant` flips true.
- **Send button**: add `active:scale-[0.98]` to match concierge buttons.
- **Brainstorm → Idea-Bin promotion** (line 117): when items are
  extracted, dispatch a CSS variable change that triggers a brief
  highlight on newly-added IdeaBin rows (use `layout` + a one-shot
  `animate` keyed on `created_at`).

### 3.3 IdeaBin (`components/trip/IdeaBin.tsx`)

- **Selection-mode toggle** (line 319–357): wrap button group in
  `AnimatePresence mode="wait"` for a fade swap.
- **Details popover** (line 459–524): on mobile, render as a bottom sheet
  instead of an absolutely-positioned popover (the `popoverTop`
  calculation already risks overflow).
- **Focus trap** in popover — use `focus-trap-react` (small dep) or a
  manual loop, plus `Esc` to close.

### 3.4 Timeline (`components/trip/Timeline.tsx`)

- Replace conflict-indicator `border` (line 490) with `box-shadow` to
  avoid layout shift.
- Event-skip toggle (line 551–559): brief green flash on restore.
- Grip icon: add `group-hover:text-indigo-500 group-hover:scale-110`.
- **Keyboard reorder**: add `Tab` + `↑/↓` to move events as a fallback
  for drag-drop (which is mouse-only at line 468).

### 3.5 VoteControl (`components/trip/VoteControl.tsx`)

- Animate tally update: button scale (existing) → number "pop"
  (`scale: [1, 1.3, 1]`) → settle. Use `motion.span key={tally}` so each
  count gets its own enter/exit.
- Voter popup (line 58–79): add `role="tooltip"` + `aria-hidden` toggle.

### 3.6 ConciergeChatDrawer (`components/trip/ConciergeChatDrawer.tsx`)

- Add `role="dialog"` + `aria-modal="true"` and focus trap on open.
- `Esc` to close (backdrop click already works).
- Stagger place-card carousel entry (line 737–747) with framer
  `staggerChildren: 0.05`.

### 3.7 ConciergeActionBar (`components/trip/ConciergeActionBar.tsx`)

- Toast (line 89–94): add a small `useEffect` cleanup for the `setTimeout`
  in line 50.
- On API failure, revert the optimistic ripple (line 54–61).

### 3.8 NotificationBell (`components/layout/NotificationBell.tsx`)

- Bell shake animation on new notification arrival (one-shot
  `rotate: [0, -10, 10, -6, 6, 0]` over 600ms).
- Unread dot: `motion.span` with `initial scale 0`.

---

## Wave 4 — Accessibility hardening

Goal: pass a basic axe scan and support keyboard-only users.

- Add `aria-label` to all icon-only buttons (audit via grep — there are
  ~30 across `components/trip/*`).
- Add `aria-live="polite"` regions around:
  - BrainstormChat typing indicator (line 190)
  - Concierge action confirmations (Drawer line 676)
  - Toast container
- Modals get `role="dialog" aria-modal="true"` + focus trap:
  - Trip planner delete-day modal
  - Trip planner remove-member modal
  - Dashboard create-trip modal
  - Dashboard persona onboarding
- Ensure all interactive elements meet WCAG AA contrast — audit the
  `opacity-60` disabled states (VoteControl line 182, IdeaBin promote
  button line 329) on light backgrounds.
- Add `prefers-reduced-motion` respect to the new PageTransition wrapper
  and to the NotificationBell shake (Trip hub already does this at
  line 143 — follow that pattern).

---

## Wave 5 — Performance & cleanup

- **Keep `gsap`** — required by the landing page (`app/page.tsx`).
  Verify the production bundle isolates it to the landing-page chunk
  (`next build` → inspect `.next/analyze` or `BUNDLE_ANALYZE=true`).
- `lib/store.ts:494–529` `deleteTripDay` re-fetches all days; switch to
  optimistic removal with rollback on failure.
- Memoize trip-list filter results in dashboard (currently recomputes
  every keystroke).
- Lazy-load `GoogleMap` and `ConciergeChatDrawer` via `next/dynamic` with
  `ssr: false` — both are heavy and not needed on first paint of the
  trip hub.

---

## Critical files (single source of truth for the implementation)

```
frontend/
├── app/
│   ├── (auth)/login/page.tsx        # 1.4
│   ├── dashboard/page.tsx           # 1.1, 1.2, 2.1
│   ├── trips/page.tsx               # 1.1, 1.3, 2.2
│   └── trips/[id]/page.tsx          # 2.4
├── components/
│   ├── layout/NotificationBell.tsx  # 3.8
│   ├── map/
│   │   ├── GoogleMap.tsx            # 2.3 (overlays)
│   │   └── MapOverlayLayer.tsx      # 2.3 (NEW)
│   ├── trip/
│   │   ├── BrainstormChat.tsx       # 1.1, 3.2
│   │   ├── IdeaBin.tsx              # 3.3
│   │   ├── Timeline.tsx             # 1.3, 3.4
│   │   ├── VoteControl.tsx          # 1.3, 3.5
│   │   ├── ConciergeChatDrawer.tsx  # 1.3, 3.6
│   │   └── ConciergeActionBar.tsx   # 3.7
├── hooks/useAuth.tsx                # 1.1
├── lib/store.ts                     # 1.1, 5
└── package.json                     # 5 (remove gsap)
```

New shared utilities to add:

- `frontend/components/ui/PageTransition.tsx` — framer wrapper for routes
- `frontend/components/ui/Toast.tsx` — promote the inline toast in
  `app/trips/page.tsx` into a shared component used everywhere
- `frontend/components/ui/Skeleton.tsx` — single source for the cards/rows
  currently re-implemented in TripGrid, Timeline, IdeaBin

---

## Verification

After each wave:

1. **Type-check & lint**: `cd frontend && npm run lint && npx tsc --noEmit`
2. **Unit tests**: `npm run test` (vitest is already configured)
3. **Manual flows** (Chrome + Safari, plus a 375px-wide mobile preview):
   - Sign up → onboarding modal → create trip → open trip → brainstorm a
     few items → extract → drag to timeline → vote → open concierge →
     "Find coffee" → close drawer → back to dashboard.
   - Force-fail each mutation (block the API in DevTools network tab)
     and confirm a toast appears + state reverts.
   - Run with `prefers-reduced-motion: reduce` — animations should
     gracefully degrade.
4. **Axe DevTools** scan on dashboard, trip hub, and each trip-planner
   tab. Target: zero serious or critical violations after Wave 4.
5. **Lighthouse mobile**: confirm performance budget hasn't regressed
   after Wave 3 (animations should be GPU-only — `transform`/`opacity`).

---

## Suggested PR sequence

1. **PR 1 — Wave 1** (bug fixes, silent-failure cleanup, shared Toast)
2. **PR 2 — Wave 2** (mobile responsiveness, sidebar drawer, plan-mode tabs, **map overlay layer**)
3. **PR 3 — Wave 3.1–3.2** (PageTransition + Brainstorm streaming)
4. **PR 4 — Wave 3.3–3.8** (component-level polish)
5. **PR 5 — Wave 4** (accessibility)
6. **PR 6 — Wave 5** (perf cleanup, remove gsap, lazy loads)

Each PR is independently revertable and ships visible value.
