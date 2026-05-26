# iOS Concierge Page — Implementation Plan

## Context

The web app ships a full **Concierge** surface (a 2‑pane Timeline + Map with a floating
`ConciergeActionBar` that opens a rich chat drawer and triggers the Smart Ripple Engine),
but the iOS app only has a throwaway MVP: `TripConciergeView` is a plain text chat with no
rich cards, no quick actions, no map/timeline, and no Smart Ripple. Our cross‑platform rule
says every feature must ship on **both** platforms natively, so we need to bring iOS to
parity — but recomposed for a phone instead of porting the side‑by‑side panes.

**Design chosen (with the user):** a **chat‑first** Concierge SubPage with rich inline cards.
Map and Timeline are kept one tap away as **full‑screen destinations** opened from two new
top‑bar icons (a location‑pin and a timeline glyph). Once inside Map/Timeline, the top bar
shows a **Back** button (returns to chat) plus a **2‑pill toggle** to switch Map ⇄ Timeline.
The entry icon pre‑selects which destination you land on. Chat is always home base.

**Decisions locked:**
- **Availability:** day‑of only (match web) — full actions live during the trip's current day; otherwise an "activates on …" state.
- **Access:** admins + Plus (match web). Backend already gates Plus via `enforce_concierge`; admin‑only is a client choice we mirror.
- **Entry point:** replace the current Concierge SubPage (keep it in the trip dropdown alongside Plan/Brainstorm/People).
- **Map/Timeline:** build **dedicated lean read‑only** Concierge views (day‑of "now" feel), not the editing Plan views.
- **Find Nearby:** inline place‑card carousel **+ "View on map"** handoff that opens the full‑screen Map with result pins.
- **v1 scope:** full web parity — chat + My Day, What's Next, Running Late (Smart Ripple 15/30/60), Skip Next, Find Nearby, action‑confirmation cards.

**Backend:** no changes needed. All endpoints exist:
`POST /concierge/{id}/chat | /execute | /find-nearby | /skip-event`, `GET …/whats-next | …/today-summary`
(`backend/app/api/endpoints/concierge.py`) and `POST /events/ripple/{id}`
(`backend/app/services/smart_ripple.py`). Tests already cover them
(`backend/tests/api/test_api_concierge.py`, `tests/integration/test_intg_concierge_executor.py`).

---

## Navigation model

```
Concierge SubPage (home = CHAT)
  topBar:  ‹Back(trip)   "trip name"   [pin] [timeline] [hamburger]
                                          │      │
              store.detail = .map ───────┘      └─── store.detail = .timeline
                              │
                              ▼
  fullScreenCover  ConciergeDetailView
     topBar:  ‹Back(→chat)        ( Map | Timeline )  ← 2‑pill toggle
     body:    ConciergeMapView  ⇄  ConciergeTimelineView   (read‑only, today only)
```

- The pin/timeline buttons live in the **host** top bar, shown only when `currentPage == .concierge` (mirrors the existing `if currentPage == .brainstorm { BrainstormQuotaPill() }` injection in `TripSubPagesHost.topBar`).
- The detail zone is a `.fullScreenCover(item:)` driven by `ConciergeStore.detail`, so it cleanly replaces the chat's chrome with its own Back + toggle, and the hamburger correctly disappears while "inside" Concierge.
- "View on map" from a place card sets `store.nearbyPins` + `store.detail = .map`.

---

## File‑by‑file work (all under `ios/Roammate/`)

### 1. Models — `Models/Concierge.swift` (extend)
The transport structs (`ConciergeChatResponse`, `PlaceCard`, `FindNearbyResponse`,
`WhatsNextResponse`, `TodaySummaryResponse`, `ExecuteResponse`) already exist and match the
backend 1:1. Enrich the **UI** message model so the chat can render rich cards:
- Add a `ConciergeCard` enum carried on `ChatMessage`: `.text`, `.actionCard`, `.placeCards([PlaceCard])`, `.summary(TodaySummaryResponse)`, `.whatsNext(WhatsNextResponse)`, `.rippleResult(shifted: Int, minutes: Int)`, `.error(retryLabel:)`.
- Add `status: ActionStatus?` (`pending | confirmed | cancelled`) for action cards.
- Decode `WhatsNext`/`TodaySummary` event payloads (`JSONValue`) into the existing `Event` model — backend `_event_dict_for_response` matches `Event`'s `CodingKeys` exactly (snake_case, `start_time` as `"HH:mm:ss"`), so a small `Event(from jsonValue:)` decoder via re‑encoding `JSONValue` → `Event` works. Add this helper.
- `RippleRequest` already exists (used by `EventService.ripple`); reuse it (`delta_minutes`, `start_from_time`).

### 2. Store — `Store/ConciergeStore.swift` (rewrite/expand)
Make it the full state machine (mirror `BrainstormStore`'s `@MainActor` + callback pattern):
- Published: `messages`, `isThinking`, `error`, `detail: ConciergeDetail?` (`.map`/`.timeline`, `Identifiable`), `nearbyPins: [PlaceCard]`, `pendingSelectedPlace`.
- Callback `onEventsChanged: (() async -> Void)?` — set by host to reload `TripDetailStore` after any mutation (parallels `brainstormStore.onIdeasPromoted`).
- Methods:
  - `send(_:)` — call `ConciergeService.chat`; route by `intent`: `find_nearby` → `findNearby(...)`; `requires_confirmation` → append `.actionCard` (status `.pending`); else `.text`. Preserves tutorial (backend returns canned replies / 423 — handle 423 `tutorial_locked` silently).
  - `confirm(messageId:)` / `cancel(messageId:)` — `ConciergeService.execute`; flip card status; on success append result text and `await onEventsChanged?()`.
  - `findNearby(query:category:)` — resolve device coordinate via new `ConciergeLocationProvider`; `ConciergeService.findNearby`; append `.placeCards`. On permission denial append `.error`.
  - `selectPlace(_:)` — append `.actionCard` add_event (computes arrival time from `travelTimeS`, like web `handlePlaceSelect`).
  - `runningLate(minutes:)` — `EventService.ripple(tripId:, RippleRequest(deltaMinutes:, startFromTime: now))`; append `.rippleResult`; `await onEventsChanged?()`.
  - `skipNext()` — find next upcoming event from today's set → `ConciergeService.skipEvent`; append result; reload.
  - `whatsNext()` / `todaySummary()` — append `.whatsNext` / `.summary` cards.
  - seed greeting message on init.

### 3. Location — `Services/ConciergeLocationProvider.swift` (new) + Info.plist
- Lightweight `CLLocationManager` wrapper: one‑shot `currentCoordinate() async -> CLLocationCoordinate2D?` with When‑In‑Use auth; fallback to current/next event coordinate, then trip center.
- Add `NSLocationWhenInUseUsageDescription` to the app's `Info.plist` (none exists yet — confirmed no `NSLocation*` keys). `MapService` already imports `CoreLocation`.

### 4. Chat view — `Views/Trips/SubPages/TripConciergeView.swift` (rewrite, store‑backed)
Keep the file/type name (`TripConciergeView(trip:)`) since `TripSubPagesHost` constructs it.
- Back it by the shared `ConciergeStore` via `@EnvironmentObject` (injected by host).
- Message list (`ScrollViewReader` + `LazyVStack`, scroll‑to‑bottom on new message) rendering typed bubbles/cards (subviews below).
- **Quick‑action chip row** above the input (web parity): `My day`, `What's next?`, `Running late` (menu → 15/30/60), `Skip next`, `Find nearby`. Use `FlowLayout` (exists) or horizontal `ScrollView`. Disable when not the live day; show an "activates on <date>" banner when the trip hasn't started / no events today.
- Input bar reusing the existing styling + `SpeechRecognizer` voice button (pattern from `BrainstormChatView`).
- **Preserve tutorial hooks:** keep `.tutorialAnchor("concierge-input")` on the input and `.onReceive(NotificationCenter…publisher(for: .tutorialConciergeSend))` → `store.send(preset)`.
- **Gating:** `isAdmin = detailStore.members.first{ $0.userId == authManager.currentUserId }?.role == "admin"` (pattern from `PeoplePaneView`/`TripLandingView`). Non‑admins see an explainer state. Plus is enforced by backend 402 → existing `.needsPlus` → `PaywallObserver`/`PaywallSheet(feature: .concierge)`; also pre‑check `subscriptionStore.entitlement.canUseConcierge` to show a Plus CTA up front.
- `.fullScreenCover(item: $store.detail)` → `ConciergeDetailView`.

### 5. Rich card subviews — `Views/Trips/SubPages/Concierge/` (new folder)
- `ConciergeBubble.swift` — text bubble (carry over current styling; markdown bold/italic like `BrainstormMessageBubble`).
- `ConciergeActionCard.swift` — intent icon + title + Confirm/Cancel; `pending`/`confirmed`(green check)/`cancelled` states.
- `ConciergePlaceCarousel.swift` — horizontal `PlaceCard` cells (photo, rating, price, travel‑time badge), tap → `store.selectPlace`, footer **"View on map"** → `store.nearbyPins = …; store.detail = .map`.
- `ConciergeSummaryCard.swift` — today summary with status dots (completed/ongoing/upcoming/skipped).
- `ConciergeWhatsNextCard.swift` — current + next event, countdown, travel‑time badges.
- `ConciergeRippleResultCard.swift` — "Shifted N events by +M min" confirmation.
- `ConciergeErrorCard.swift` — message + Retry.
All use theme tokens (`.roammateIndigo`, `Color.categoryColor`, `RoammateSpacing/Radius/Shadow`).

### 6. Detail zone — `Views/Trips/SubPages/Concierge/ConciergeDetailView.swift` (new)
- Own top bar: Back (`store.detail = nil`) + segmented Map/Timeline pill (binds to `detail`).
- Switches between the two dedicated views; honors which icon opened it.

### 7. Dedicated read‑only views (new, day‑of tuned)
- `ConciergeMapView.swift` — SwiftUI `Map` (MapKit). Renders **today's** events as markers (`MapService.buildMarkers`), today's route overlays (`RouteService.fetchStoredRoute(tripId, todayStr)` → `decodeStoredRoute`, `RouteLegColors`), a distinct "NOW" marker for the current event, and `store.nearbyPins` (distinct pin style) with an add‑as‑event callout. Read‑only — no drag/add. Reuse `MapPinView`/`MapCalloutSheet` styling from `Views/Trips/Plan/` where helpful.
- `ConciergeTimelineView.swift` — vertical list of **today's** events (`detailStore.eventsByDay[todayStr]`) sorted by `startTime`, with a "now" line, completed/ongoing/upcoming/skipped styling, and travel‑leg labels. Lean read‑only variant of `TimelineDrawerContent`/`TimelineRow` (no editing, no drag, no day tabs).
- Both compute `todayStr` from `trip.timezone`; read events/routes from the shared `TripDetailStore` (no new fetches except today's stored route).

### 8. Host wiring — `Views/Trips/TripSubPagesHost.swift` (edit)
- Add `@StateObject private var conciergeStore` (init with `trip.id`, parallel to `brainstormStore`).
- In `topBar`, when `currentPage == .concierge`, inject two 44pt icon buttons before the hamburger: pin (`map` / `mappin.and.ellipse`) → `conciergeStore.detail = .map`; timeline (`calendar.day.timeline.left` or `list.bullet.rectangle`) → `.timeline`. Gate to `isAdmin && live day`.
- Inject `conciergeStore` into `pageContent` for `.concierge` (`.environmentObject`), and set `conciergeStore.onEventsChanged = { await detailStore.loadDay(today) }` in `.task`.

---

## Contract / data notes
- Backend `start_time`/`end_time` are trip‑local wall‑clock `"HH:mm:ss"` → maps to `TimeOfDay`; absolute instants need `dayDate` + `trip.timezone`.
- `find-nearby`/`execute`/`skip-event`/`chat` enforce Plus (`enforce_concierge`, 402 on miss); `whats-next`/`today-summary` are member‑only (no Plus) — safe to call for the live cards.
- Ripple rejects shifts past local midnight (v1 constraint) and returns the shifted `[Event]`.
- Admin is **not** enforced server‑side; it's a client gate to mirror web.

---

## Verification
1. **Build:** open `ios/Roammate.xcodeproj`, build the `Roammate` scheme for an iOS Simulator; resolve any compile errors.
2. **Seed state:** use `/debug-db` (or the backend) to ensure a test trip where **today** is a trip day with several events (some past, one ongoing, some upcoming) and the user is **admin + Plus**. Local backend via Docker Compose; point the app at it.
3. **Manual run (simulator):**
   - Open the trip → Concierge SubPage: greeting + chips show; map/timeline icons visible in top bar.
   - Tap **pin** → full‑screen Map with today's markers + route + NOW marker; **toggle** to Timeline; **Back** returns to chat (scroll preserved).
   - **What's next?** / **My day** → live cards render with correct counts/countdown.
   - **Running late → +30** → ripple result card; reopen Map/Timeline and confirm event times shifted.
   - **Find nearby → "coffee"** → grant location → place carousel; **View on map** drops result pins; select a place → add‑event confirm → Confirm → appears on timeline.
   - **Skip next** → next event marked skipped.
   - Free‑text chat that triggers a confirmation (e.g. "move dinner to 8pm") → action card → Confirm executes.
4. **Gating:** as a **non‑admin** member, confirm the explainer/locked state. As **free** tier, confirm the action triggers the Plus paywall (`PaywallSheet(feature: .concierge)`).
5. **Availability:** on a trip whose dates are in the future, confirm the "activates on <date>" state and disabled chips.
6. **Tutorial:** run the onboarding tutorial trip; confirm canned Concierge replies still flow and `.tutorialConciergeSend` drives the input (the `concierge-input` anchor still resolves).
7. **A11y/polish:** VoiceOver labels on the pin/timeline/chip/card buttons; ≥44pt targets; reduced‑motion respected; safe‑area insets for the input bar and detail top bar.
8. **(If an iOS test target exists)** add `ConciergeStore` unit tests for intent routing (find_nearby → placeCards, requires_confirmation → pending card, ripple → rippleResult). Otherwise rely on the existing backend test suite (`pytest backend/tests/... -k concierge`) which already passes.

---

## Out of scope (v1)
- Streaming/SSE chat (backend returns whole responses; keep request/response).
- Editing on the Concierge Map/Timeline (read‑only by design).
- Persisting Concierge chat history fetch on open (backend stores it; loading prior history can be a fast‑follow — v1 seeds a fresh greeting).
- Web changes (already at parity).
