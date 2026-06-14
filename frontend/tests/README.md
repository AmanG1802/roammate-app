# Frontend Test Suite

**Framework:** Vitest 4 + React Testing Library · **Environment:** jsdom  
**Run:** `cd frontend && npx vitest run`  
**Coverage:** `cd frontend && npx vitest run --coverage`

---

## Current Coverage (as of June 2026)

| Metric     | Coverage |
|------------|----------|
| Statements | 27.5 %   |
| Branches   | 26.9 %   |
| Functions  | 26.1 %   |
| Lines      | 28.3 %   |

**16 test files · 244 tests · all passing.**

The low overall number is dragged down by large, 0%-covered files (GoogleMap, ConciergeChatDrawer, auth pages). The areas that _are_ tested are reasonably thorough.

---

## Test Files

### `lib/` utilities — 88.9 % statement coverage

| File | Coverage | Test file | What's covered |
|------|----------|-----------|----------------|
| `lib/api.ts` | 70.8 % | `lib/api.test.ts` | Fetch wrapper, error handling, 401 token-refresh flow |
| `lib/auth.ts` | 100 % | `lib/auth.test.ts` | `clearSession` wipes localStorage |
| `lib/categoryColors.ts` | 85 % | `lib/categoryColors.test.ts` | `categoryAccent`, `categoryPinColor` for all tag slugs |
| `lib/plusOnboarding.ts` | 80 % | `lib/plusOnboarding.test.ts` | "seen" flag, `currentUserIdFromCache` |
| `lib/store.ts` | 92.9 % | `lib/store.test.ts` | All Zustand mutations: events, ideas, votes, trip days, route legs, UI state, ripple side-effects |
| `lib/time.ts` | 98.1 % | `lib/time.test.ts` | `parseTimeOfDay`, `formatTimeOfDay`, `compareTimeOfDay`, `combineInTz`, `timeOfDayFromDate` |
| `lib/toast-bus.ts` | — | `lib/toast-bus.test.ts` | Pub/sub emit and subscribe |
| `lib/motion.ts` | excluded | — | Framer Motion re-exports; excluded from coverage |

### `components/trip/` — 48.2 % statement coverage

| File | Coverage | Test file | What's covered |
|------|----------|-----------|----------------|
| `BrainstormBin.tsx` | 83.8 % | `BrainstormBin.test.tsx` | Loading, list render, delete, clear-all, promote-all, selection mode, enrichment retry |
| `BrainstormChat.tsx` | 80.2 % | `BrainstormChat.test.tsx` | Load messages, send, failed message, extract button, quota exhausted state |
| `IdeaBin.tsx` | 63.6 % | `IdeaBin.test.tsx` | Loading, ingest, delete, edit time, read-only mode |
| `Timeline.tsx` | 68.6 % | `Timeline.test.tsx` | Empty states, render, time editing, move-to-bin/restore, drag reorder, filterDay, read-only |
| `VoteControl.tsx` | 89.6 % | `VoteControl.test.tsx` | Initial prop, API fetch, `canVote=false`, casting votes, voter popup |
| `ConciergeChatDrawer.tsx` | **0 %** | none | 1 106-line file — fully untested |
| `ConciergeActionBar.tsx` | **0 %** | none | Action history, undo — fully untested |
| `BrainstormSection.tsx` | **0 %** | none | Thin wrapper — fully untested |
| `VibeCheck.tsx` | **0 %** | none | Group vibe poll — fully untested |

### `components/layout/` — 47.1 % statement coverage

| File | Coverage | Test file | What's covered |
|------|----------|-----------|----------------|
| `NotificationBell.tsx` | 66.5 % | `NotificationBell.test.tsx` | Unread badge, open/close, empty state, notification list, mark-read, refresh |
| `Navbar.tsx` | **0 %** | none | 254-line nav — fully untested |
| `Collaborators.tsx` | **0 %** | none | Tiny avatar list — fully untested |

### `components/billing/` — 35.7 % statement coverage

| File | Coverage | Test file | What's covered |
|------|----------|-----------|----------------|
| `CouponInput.tsx` | 92.7 % | `billing.test.tsx` | Coupon apply/reject happy + error paths |
| `PlusBanner.tsx` | 86.5 % | `billing.test.tsx` | Past-due, free-usage, one-time expiry, re-engagement variants |
| `QuotaPill.tsx` | 100 % | `billing.test.tsx` | Quota counts and exhausted state |
| `OnboardingPlusModal.tsx` | **0 %** | none | Post-purchase onboarding — fully untested |
| `PaywallModal.tsx` | **0 %** | none | 449-line paywall — fully untested |
| `PlanToggle.tsx` | **0 %** | none | Monthly/annual toggle — fully untested |
| `PlusCrest.tsx` | **0 %** | none | Badge icon — fully untested |
| `TierComparison.tsx` | **0 %** | none | Feature comparison grid — fully untested |

### `app/` pages — mixed coverage

| File | Coverage | Test file | What's covered |
|------|----------|-----------|----------------|
| `(authenticated)/trips/[id]/page.tsx` | 86.7 % | `TripHub.test.tsx` | Load states, nav tabs, invite flow, inline edits, non-admin view |
| `(authenticated)/dashboard/page.tsx` | **0 %** | `app/dashboard.test.tsx` | Dashboard search, section nav, invitations, create-trip modal, delete — tested via component mock, page.tsx not directly exercised |
| All `(auth)/` pages | **0 %** | none | Login, signup, forgot-password, reset, verify — fully untested |
| `admin/` pages | **0 %** | none | Admin dashboard — fully untested |
| `pricing/page.tsx` | **0 %** | none | Fully untested |
| `(authenticated)/trips/page.tsx` | **0 %** | none | Trips list — fully untested |
| `(authenticated)/profile/` | **0 %** | none | Profile, persona, subscription pages — fully untested |

### Completely untested areas

| Area | Files | Notes |
|------|-------|-------|
| **Maps** | `GoogleMap.tsx` (1 268 lines), `MapOverlayLayer.tsx` | Heavy Google Maps SDK dependency — requires map mock strategy |
| **Groups** | `GroupsPanel.tsx` (668 lines) | Friend circles feature — no tests |
| **Auth UI** | `AuthCard`, `Fields`, `OAuthButtons`, `PrimaryButton` | Auth flow components — no tests |
| **Profile/Persona** | `EditProfile.tsx` (745 lines), `OnboardingPersonaModal.tsx`, `PersonaPicker.tsx`, `PersonaSoftPrompt.tsx`, `UserMenu.tsx` | User settings surface — no tests |
| **Tutorial/Onboarding** | `SpotlightOverlay.tsx`, `TutorialProvider.tsx`, `WelcomeModal.tsx` | Tutorial step system — no tests |
| **Dashboard widgets** | `DashboardTripPlanner.tsx`, `TodayWidget.tsx` | Dashboard sub-components — no tests |
| **UI primitives** | `Toast.tsx`, `EnrichmentBadge.tsx`, `PageTransition.tsx`, `VoiceInputButton.tsx` | Small UI atoms — no tests |

---

## Test Infrastructure

### `setup.ts`
Global before/after hooks applied to every test:
- `@testing-library/jest-dom` matchers (`toBeInTheDocument`, `toHaveTextContent`, etc.)
- `cleanup()` after each test — unmounts React trees
- Browser API stubs: `matchMedia`, `ResizeObserver`, `IntersectionObserver`, `scrollIntoView`, `scrollTo`
- `localStorage` mock (in-memory, isolated — cleared before each test)
- `clearMocks: true` + `restoreMocks: true` in vitest config — spy state can't bleed between tests

### `helpers/framerMock.tsx`
Stubs Framer Motion components (`motion.div`, `AnimatePresence`) as plain `<div>` elements so animation-heavy components render synchronously in jsdom.

### Vitest config (`vitest.config.ts`)
- Coverage provider: V8 (`@vitest/coverage-v8`)
- Coverage scope: `lib/**/*.ts`, `components/**/*.tsx`, `app/**/*.tsx`
- Excluded: `**/*.d.ts`, `lib/motion.ts`
- Reports: text (terminal) + html (`coverage/index.html`)

---

## What's Missing / Priority Gaps

### High priority

1. **Auth pages** — Login/signup/reset are critical user paths with zero test coverage. Add smoke tests for form validation and error states.

2. **ConciergeChatDrawer** (`components/trip/ConciergeChatDrawer.tsx`) — The AI concierge is a flagship feature at 1 106 lines with no tests. Minimum: message send/receive, action execution, error recovery.

3. **ConciergeActionBar** — Undo/redo for concierge actions has zero coverage; this is a risky mutation surface.

4. **PaywallModal / OnboardingPlusModal** — Revenue-critical flows. At minimum: plan display, CTA click, and error state.

5. **`app/(authenticated)/trips/page.tsx`** — The trips list page (trip creation entry point) has zero coverage.

### Medium priority

6. **IdeaBin.tsx gaps** — 63.6% coverage; missing: tag filtering, multi-select promote, empty-with-tags state.

7. **Timeline.tsx gaps** — 68.6% coverage; missing: Smart Ripple downstream shift assertions, locked-event enforcement, multi-day event overflow.

8. **NotificationBell.tsx gaps** — 66.5% coverage; missing: trip-context links, notification type variants.

9. **Navbar** — Navigation and mobile hamburger menu have no tests.

10. **`lib/api.ts` gaps** — 70.8% coverage; missing: retry logic, multipart upload paths.

### Lower priority

11. **Dashboard widgets** (`DashboardTripPlanner`, `TodayWidget`) — Isolated from the page test; worth standalone tests.

12. **GoogleMap / MapOverlayLayer** — Requires a Google Maps JS API mock. Consider a lightweight stub factory.

13. **Tutorial system** (`TutorialProvider`, `SpotlightOverlay`) — Step sequencing has complex state; worth a dedicated test suite.

14. **UI atoms** (`Toast`, `EnrichmentBadge`, `VoiceInputButton`) — Simple components that are quick wins for coverage.

---

## Running Tests

```bash
# All tests
cd frontend && npx vitest run

# Watch mode (development)
cd frontend && npx vitest

# Coverage report (outputs to frontend/coverage/index.html)
cd frontend && npx vitest run --coverage

# Single file
cd frontend && npx vitest run tests/lib/store.test.ts

# Single describe block
cd frontend && npx vitest run -t "store — moveIdeaToTimeline"
```
