# Roammate iOS — Trip Sub-Pages (Plan / Brainstorm / People)

## Context

The iOS app's foundation is complete: Dashboard, Trips list, Trip Landing, Invitations, Groups, Profile, and a Plan-Trip drawer all work end-to-end against the FastAPI backend. Trip Landing currently has four cards (Plan, Brainstorm, Concierge, People) that push to "Coming soon" stubs. This plan replaces those stubs with real, content-rich sub-pages that mirror the web app's planner workflow but rethink the layout for a phone.

Concierge is intentionally deferred — its menu entry exists and routes to a Coming Soon stub.

---

## Locked decisions (from user)

- **Idea → Timeline**: multi-select + batch add. No drag-and-drop, no long-press magic.
- **Map provider**: Apple MapKit (native SwiftUI `Map`).
- **Routes / polylines**: skip for v1 — pins only.
- **Top-left back button**: pops all the way back to Dashboard (skips Trip Landing on return).
- **Top-right button**: opens a side drawer from the right with 4 sub-page nav items.
- **Plan page layout**: 2 horizontally-paged screens. Left = Map full-bleed + bottom drawer (60% detent default) holding the timeline. Right = Idea Bin.
- **Brainstorm page layout**: 2 horizontally-paged screens. Left = AI chat. Right = Brainstorm Bin (delete, count, send all, select & send).
- **People page**: mirrors web — member list with role badges + invite (admin only).
- **Visual parity**: idea / timeline / brainstorm rows replicate the web's data fields (title, photo, category badge, address, rating, votes, time, added-by).

## Defaults I'm baking in (push back if any feel wrong)

- **Bin row layouts**: 1-column list on iPhone (web uses 2-col grids; cramped on a 393pt screen).
- **Vote controls**: present on Timeline events and Idea Bin items (up/down + my-vote indicator). Brainstorm Bin has no votes (matches web — votes are post-promotion).
- **Brainstorm promotion**: toast on success, user stays on Brainstorm Bin. No auto-jump to Idea Bin.
- **Trip Landing**: kept as-is. It remains the first screen after tapping a trip; users pick a sub-page from there. Sub-page back button skips Trip Landing on return (pops to Dashboard).
- **Concierge in side drawer**: visible entry but routes to a "Coming soon" stub.

---

## Architecture overview

```
DashboardView (NavigationStack root)
  └─ TripLandingView  (push 1)
       └─ TripSubPagesHost  (push 2 — one umbrella view for all 4 sub-pages)
              ├─ custom top bar: ◁ back | trip name | ☰ menu
              ├─ right-side drawer overlay (menu)
              ├─ @State currentPage: SubPage  →  switches in-place
              │     ├─ PlanPane         (paged: MapView + TimelineDrawer | IdeaBinView)
              │     ├─ BrainstormPane   (paged: BrainstormChat | BrainstormBin)
              │     ├─ ConciergeStub    (Coming soon)
              │     └─ PeoplePane
              └─ pop-to-root via NavigationPath binding
```

The "pop to Dashboard" back behavior is implemented by giving Dashboard's NavigationStack a `@State var path = NavigationPath()` and threading a `popToRoot: () -> Void` closure down through TripLandingView → TripSubPagesHost.

Switching between sub-pages via the right drawer is **state**, not navigation — the umbrella `TripSubPagesHost` swaps which child view it renders. This keeps the back button always one tap (no growing nav stack), which is exactly what the user wants.

---

## File structure

### New files (20)

```
ios/Roammate/
├── Models/
│   └── Brainstorm.swift                    # BrainstormItemOut, BrainstormMessage, request shapes
├── Network/
│   └── BrainstormService.swift             # /brainstorm/{items,messages,chat,extract,promote,clear}
├── Store/
│   └── BrainstormStore.swift               # owns chat history + bin items per trip
├── Theme/
│   ├── BottomDrawer.swift                  # 3-detent custom drawer (snap, drag, handle)
│   ├── PaneSlider.swift                    # 2-page horizontal pager wrapper
│   └── SideDrawer.swift                    # right-edge slide-in menu overlay
└── Views/Trips/
    ├── TripSubPagesHost.swift              # umbrella container + top bar + menu state
    ├── SubPageMenu.swift                   # 4 menu rows (icon + label) inside SideDrawer
    ├── Plan/
    │   ├── PlanPaneView.swift              # 2-page slider: MapPage | IdeaBinPage
    │   ├── PlanMapPage.swift               # MapKit `Map` + bottom TimelineDrawer
    │   ├── TimelineDrawerContent.swift     # day tabs + grouped event list
    │   ├── DayTabsBar.swift                # horizontal pill tabs "Overview / Day 1 …"
    │   ├── TimelineRow.swift               # event card (photo, title, time, category, votes)
    │   ├── IdeaBinView.swift               # 1-col list of ideas; "Select" enters multi-select
    │   ├── IdeaRow.swift                   # idea card (photo, title, category, address, votes)
    │   └── AddToTimelineSheet.swift        # day picker + "Add N to Day X" CTA
    ├── Brainstorm/
    │   ├── BrainstormPaneView.swift        # 2-page slider: Chat | Bin
    │   ├── BrainstormChatView.swift        # chat list + input + extract button
    │   ├── BrainstormMessageBubble.swift   # user / assistant bubble + sparkle avatar
    │   └── BrainstormBinView.swift         # 1-col list, multi-select, send all / send selected
    └── People/
        └── PeoplePaneView.swift            # members list + invite admin-only
```

### Files to update

- `Views/Trips/TripLandingView.swift` — replace 4 NavigationLinks. Each card now pushes `TripSubPagesHost(trip:, initialPage:)`. Trip Landing also threads down the `popToRoot` closure it receives from the Dashboard.
- `Views/Dashboard/DashboardView.swift` — convert the NavigationStack to take a `@State var path: NavigationPath`. Provide `popToRoot = { path.removeLast(path.count) }` to children via a `@Environment(\.popToRoot)` custom EnvironmentKey.
- `Theme/RoammateTheme.swift` — add `categoryColor(_ category: String?) -> Color` mapping (food→amber, culture→violet, nature→emerald, …) to match web's `categoryColors.ts`.
- `Views/Trips/SubPages/TripPlanView.swift`, `TripBrainstormView.swift`, `TripPeopleView.swift` — **delete**. Replaced by the new sub-page views.
- `Views/Trips/SubPages/TripConciergeView.swift` — keep, used as the Coming Soon stub.

---

## Per-screen design

### 1. TripSubPagesHost (the umbrella)

```
┌────────────────────────────────────────────┐
│  ◁     Trip to New York            ☰      │  ← custom top bar
├────────────────────────────────────────────┤
│                                            │
│            currentPage view                │
│                                            │
└────────────────────────────────────────────┘
```

- Custom top bar (not the system nav bar — system nav is hidden on this push).
- `◁` back: calls `popToRoot()` → Dashboard. Light haptic.
- Center: trip name in `.title3, weight: .semibold` ink color.
- `☰` menu: opens `SideDrawer(edge: .trailing)` with the 4 sub-page items.
- `@State var currentPage: SubPage` with cross-fade animation (`.easeInOut(0.18)`) between sub-views.
- Picking a menu item updates `currentPage` and closes the drawer.

`SideDrawer`:
- Backdrop: black 30% opacity, tap → close.
- Panel: 320pt wide, slides in from `.trailing` with `.spring(response: 0.35, dampingFraction: 0.85)`.
- Internal: list of 4 rows (icon, label, chevron), one highlighted (`.roammateIndigoTint` background) showing the current page.

### 2. PlanPane (the most important)

**Layout (2 horizontally-paged):**

```
┌─ page 0 (Map + drawer) ─┬─ page 1 (IdeaBin) ─┐
│                          │                     │
│       MapKit Map         │   ┌───────────────┐ │
│                          │   │ Idea card  ⓘ │ │
│                          │   ├───────────────┤ │
│  ┌─ TimelineDrawer ────┐ │   │ Idea card  ⓘ │ │
│  │  ━━ (handle)        │ │   │     …         │ │
│  │  [Overview][Day 1]… │ │   └───────────────┘ │
│  │                     │ │                     │
│  │  Day 1 — 5 stops    │ │   [Select] toolbar  │
│  │   • event row       │ │                     │
│  └─────────────────────┘ │                     │
└──────────────────────────┴─────────────────────┘
```

- `PaneSlider` (built on SwiftUI `TabView` with `.page(indexDisplayMode: .never)` style + a tiny indicator dot row above the bottom nav) hosts the 2 pages.
- **Map page** (`PlanMapPage`):
  - `Map(position: $cameraPosition)` from MapKit, full-bleed under the top bar.
  - `Marker` per event of the selected day, color-coded by category. `Marker` per idea (smaller, slate). Tap a marker → focuses the map; the corresponding timeline row scrolls into view in the drawer.
  - On first render, fit camera to the union of markers (`MKMapRect`).
  - `BottomDrawer` overlaid: 3 detents — **minimised** (140pt visible), **medium** (60% screen), **large** (90% screen). User drag-to-snap. Map remains interactive at minimised and medium.
- **TimelineDrawerContent** (the drawer body):
  - `DayTabsBar` — pill row at top: `[Overview][Day 1][Day 2]…` Selected = filled indigo pill with white text (matches screenshot the user sent). Horizontally scrollable.
  - Below: scrollable `LazyVStack` of section headers + `TimelineRow`s.
  - **Overview** = all days flattened with section headers per day.
  - **Day N** = filtered to that day only; section header reads e.g. "Day 2 — 30 activities".
- **TimelineRow** (card):
  - Left: 56×56 photo (RoundedRectangle 14pt corner) loaded via `AsyncImage` from `photo_url`, placeholder = indigo-tint gradient with category SF Symbol.
  - Right: title (semibold), category pill (color from `categoryColor`), time text (formatted `h:mm a` or "TBD"), rating with star if present.
  - Trailing: vote control (up/down arrows + my-vote indicator) — only if `canVote`.
  - Tap row → bottom sheet with full detail (photo large, description, address, added by, edit time, move to bin).
- **Idea Bin page** (`IdeaBinView`):
  - Header row: "X ideas" count + "Select" toggle button (right side).
  - List of `IdeaRow`s (1-col, full-width). Each row: 56×56 photo, title, category pill, address, time-or-"No time", trailing vote control + delete button (visible on swipe-left action).
  - Long-press an idea → context menu with "View details" and "Add to Day…" (single-item add shortcut).
  - When "Select" is active: rows get circular checkbox on the left, a bottom sticky bar appears "Add 3 to Timeline" + "Cancel". Tap → opens `AddToTimelineSheet`.
- **AddToTimelineSheet**:
  - Medium detent sheet.
  - Title "Add X ideas to which day?"
  - List of days for the trip with day-number + date.
  - Optional "Pick a start time for the first item" `DatePicker` (toggle).
  - "Add to Timeline" CTA → for each selected idea: `POST /events/` (copying the idea's place fields + chosen day_date) then `DELETE /trips/{id}/ideas/{ideaId}`. Run in parallel via `TaskGroup`. On success: dismiss sheet, refresh `TripDetailStore.eventsByDay` + `ideas`, exit selection mode, light success haptic.

### 3. BrainstormPane

```
┌─ page 0 (Chat) ───────────┬─ page 1 (Bin) ──────────┐
│  ┌ assistant ────────┐    │ N items   [Select][⋯]   │
│  │ Hi! Where to?    │    │                         │
│  └───────────────────┘    │ ┌─────────────────────┐ │
│                  ┌user ┐  │ │ Mont-Saint-Michel   │ │
│                  │Paris│  │ │ Culture • Normandy  │ │
│                  └─────┘  │ └─────────────────────┘ │
│  ⋯                        │   …                     │
│ ┌───────────────────────┐ │                         │
│ │ Type something…  ↗   │ │ [Send all] [Send 3]     │
│ └───────────────────────┘ │                         │
└───────────────────────────┴─────────────────────────┘
```

- `BrainstormPaneView` is a 2-page `PaneSlider`.
- **BrainstormChatView**:
  - On appear: `GET /trips/{id}/brainstorm/messages` to hydrate `BrainstormStore.messages`.
  - User message bubble: right-aligned, indigo gradient → indigo-dark.
  - Assistant bubble: left-aligned, white surface, sparkle avatar circle on the left, bottom-left corner sharper to mimic web.
  - Typing indicator (3 bouncing dots, `.symbolEffect(.pulse)`).
  - Input bar pinned to bottom: rounded TextField + indigo `arrow.up.circle.fill` send. Disabled when empty or `isSending`.
  - Below the input, a small "Extract ideas from chat" pill button (only visible after a few messages) → `POST /trips/{id}/brainstorm/extract` → on success show toast "Added X ideas to your brainstorm bin" + auto-swipe to Bin page.
- **BrainstormBinView**:
  - Header row: "X items" count chip (amber pill, matches web's `bg-amber-50 text-amber-600`) + Select toggle + overflow menu (Clear all → `DELETE /trips/{id}/brainstorm/items`).
  - 1-col list of `BrainstormRow`s (similar shape to IdeaRow but with a category-color left accent bar).
  - Each row has a trailing trash button → `DELETE /trips/{id}/brainstorm/items/{id}` (optimistic, animated row remove).
  - Bottom sticky toolbar with two buttons:
    - **Send all** → `POST /trips/{id}/brainstorm/promote` with `item_ids: null`.
    - **Send N** (only shown in selection mode) → `POST /trips/{id}/brainstorm/promote` with `item_ids: [...]`.
  - On success: toast "Sent X items to Idea Bin", refresh `TripDetailStore.ideas`, exit selection mode. Stay on this page.

### 4. PeoplePane

- Single scrolling view (no paging).
- Two sections:
  - **Travellers** (always shown): grouped list of accepted members. Each row: avatar (initials in indigo gradient), name, email, role pill (Admin = indigo, View w/ Vote = violet, View Only = sky). Admin can: swipe-left to remove (with confirm), tap row → change-role action sheet.
  - **Pending invitations** (only if any): each row: invitee name/email + role + amber "Pending" pill. Admin can revoke (delete member).
- Header CTA: `+` button (admin only) → reuses existing `InviteSheet` (email + role picker → `POST /trips/{id}/invite`).
- Empty state for pending invitations is just absent; for travellers it shouldn't occur (caller is always a member).
- Uses existing `TripDetailStore.members` (already loaded by Trip Landing); `PeoplePaneView` just observes it.

---

## Data layer changes

### Models (new `Models/Brainstorm.swift`)

```swift
struct BrainstormItemOut: Codable, Identifiable, Hashable { /* PlaceFields + id + tripId + userId + addedBy + createdAt */ }
struct BrainstormMessage: Codable, Identifiable, Hashable { /* id, role, content, createdAt */ }
struct BrainstormChatResponse: Codable { let assistantMessage: BrainstormMessage; let history: [BrainstormMessage] }
struct BrainstormExtractResponse: Codable { let items: [BrainstormItemOut]; let enrichment: JSONValue? }
struct BrainstormPromoteRequest: Encodable { let itemIds: [Int]? }
```

The `BrainstormItem` already in `PlanTrip.swift` stays — it's the bare PlaceFields request shape used by `plan-trip` and `bulk`. The new `BrainstormItemOut` is the full server response with id/user/timestamps.

### Service (new `Network/BrainstormService.swift`)

```swift
enum BrainstormService {
    static func getItems(tripId: Int) async throws -> [BrainstormItemOut]
    static func getMessages(tripId: Int) async throws -> [BrainstormMessage]
    static func chat(tripId: Int, message: String) async throws -> BrainstormChatResponse
    static func extract(tripId: Int) async throws -> BrainstormExtractResponse
    static func promote(tripId: Int, itemIds: [Int]?) async throws -> [IdeaBinItem]
    static func deleteItem(tripId: Int, itemId: Int) async throws
    static func clearAll(tripId: Int) async throws
}
```

### Store (new `Store/BrainstormStore.swift`)

```swift
@MainActor final class BrainstormStore: ObservableObject {
    let tripId: Int
    @Published var messages: [BrainstormMessage] = []
    @Published var items: [BrainstormItemOut] = []
    @Published var isSending = false
    @Published var isExtracting = false

    func load() async        // fetches messages + items in parallel
    func send(_ text: String) async
    func extract() async -> Int           // returns items added
    func promote(itemIds: [Int]?) async   // notifies TripDetailStore.refreshIdeas via callback
    func delete(itemId: Int) async
    func clearAll() async
}
```

Injected with `@StateObject` inside `TripSubPagesHost` (one instance per trip session). Disposed when host pops back to Dashboard.

### Existing reuse

- `TripDetailStore` — already provides `trip`, `days`, `eventsByDay`, `ideas`, `members`. Loaded on `TripLandingView`. `TripSubPagesHost` re-uses the same instance via `.environmentObject` injection (so all sub-pages see consistent state).
- `EventService.createEvent`, `EventService.deleteEvent`, `IdeaService.deleteIdea` — used by `AddToTimelineSheet`.
- `MemberService.invite / removeMember / updateRole` — used by `PeoplePaneView`.
- `VoteService.voteEvent / voteIdea` — used by row vote controls.
- `MapService.buildMarkers` — already exists, used by `PlanMapPage` to derive `MapMarker`s.

---

## Custom UI primitives

### `Theme/BottomDrawer.swift`
A reusable container that pins itself to the bottom of its parent with three drag-snapping detents. Spec:
- API: `BottomDrawer(detents: [.minimised(140), .fraction(0.6), .fraction(0.9)], current: $detent) { content }`
- Rounded top corners (28pt), thin grab handle, soft shadow, ultra-thin material background.
- `DragGesture` on the handle area; `translation.height` adjusts offset; on `.onEnded` snap to nearest detent with `.spring(response: 0.35, dampingFraction: 0.85)`.
- Content below the handle is a regular `ScrollView` — scroll gestures only kick in when drawer is at `.fraction(0.9)`, otherwise the drag is consumed by the drawer (so the user can grab anywhere to resize). Use `.simultaneousGesture` with priority handling.

### `Theme/PaneSlider.swift`
Thin wrapper around `TabView(selection:).tabViewStyle(.page(indexDisplayMode: .never))` with:
- A small two-dot pager indicator that fades in/out at the top of the pages.
- A `@Binding var page: Int` exposed so parents can programmatically swap pages (e.g., auto-jump from Chat to Bin after extract).

### `Theme/SideDrawer.swift`
Right-edge slide-in modal overlay:
- API: `.sideDrawer(isPresented: $bool) { content }`
- Implementation: ZStack overlay added via `.overlay` modifier with a backdrop tap-dismiss and a panel that animates `offsetX` from screen width → 0.

---

## Animation principles

- **Page swipe (PaneSlider)**: native `TabView .page` style — already feels great.
- **Drawer detent snap**: `.spring(response: 0.35, dampingFraction: 0.85)`.
- **Side drawer**: same spring.
- **Selection-mode enter/exit**: `.spring(response: 0.3, dampingFraction: 0.8)` on checkbox circle scale + the bottom toolbar slide-up.
- **Toast after promote / batch-add**: top-of-screen capsule, fades in/out, indigo success tint.
- **Map marker hover/scroll-into-view**: `.spring(.smooth)` on map camera + ScrollViewProxy `scrollTo`.
- **Brainstorm extract**: when items land, auto page-swipe to the Bin page with `.spring(.bouncy)`.

All native SwiftUI — no Lottie, no UIKit bridges beyond MapKit's `Map`.

---

## Implementation order (one batch per chunk; rebuild between)

1. **Primitives** — `BottomDrawer`, `PaneSlider`, `SideDrawer`, category-color helper in Theme.
2. **TripSubPagesHost shell** — top bar, side drawer, currentPage switching, popToRoot threading through Dashboard + TripLanding.
3. **Plan: Map page** — `PlanMapPage` with `Map` + MapKit markers + camera fit. No drawer yet.
4. **Plan: Timeline drawer** — `BottomDrawer` + `DayTabsBar` + `TimelineDrawerContent` + `TimelineRow`. Read-only display first.
5. **Plan: Idea Bin** — `IdeaBinView` + `IdeaRow` + selection mode + `AddToTimelineSheet` (batch add flow).
6. **Brainstorm models / service / store** — `Models/Brainstorm.swift`, `Network/BrainstormService.swift`, `Store/BrainstormStore.swift`.
7. **Brainstorm pane** — `BrainstormChatView`, `BrainstormBinView` (with multi-select + send all / send N), `BrainstormMessageBubble`, extract auto page-swipe.
8. **People pane** — `PeoplePaneView` using existing `TripDetailStore.members` + `InviteSheet`.
9. **Vote controls + row detail sheets** — small polish pass on Timeline rows and Idea rows.
10. **Clean up old stubs** — delete `TripPlanView.swift`, `TripBrainstormView.swift`, `TripPeopleView.swift`; rewire `TripLandingView` four cards to push `TripSubPagesHost(initialPage:)`.
11. **Regenerate Xcode project** — `cd ios && xcodegen generate`.
12. **Smoke test** on simulator (see verification below).

---

## Verification

End-to-end smoke test after all chunks:

1. `cd /Users/aman.gupta1/roammate-app && docker compose up -d` (backend running).
2. `cd ios && xcodegen generate && open Roammate.xcodeproj`. `⌘R` on iPhone 15 Pro simulator.
3. Log in, tap a real trip on Dashboard.
4. **Trip Landing**: tap "Plan" → push to `TripSubPagesHost`. Top bar shows trip name, back chevron on left, hamburger on right.
5. **Side drawer**: tap ☰ → drawer slides in from right with 4 items, current ("Plan") highlighted. Tap "Brainstorm" → drawer dismisses, content swaps to Brainstorm pane (no nav push).
6. **Brainstorm Chat**: type a message, hit send → assistant replies. Tap "Extract ideas" → items land, auto page-swipe to Bin.
7. **Brainstorm Bin**: select 2 items → "Send 2" → toast "Sent to Idea Bin". Switch to Plan via menu → swipe right to Idea Bin page → see the 2 promoted items.
8. **Plan / Idea Bin selection**: tap "Select", pick 3 ideas, "Add 3 to Timeline" → pick "Day 2" → confirm. Sheet dismisses, ideas removed from bin, events appear under Day 2 in the timeline drawer.
9. **Plan / Map**: swipe left back to Map page. See pins for events + smaller pins for remaining ideas. Drawer shows day tabs ("Overview / Day 1 / Day 2 …"); tap "Day 2", drawer shows the 3 new events plus any existing.
10. **Drawer detents**: drag handle down → minimised (only top 140pt visible, map fully usable). Drag up → 60%. Drag up again → 90%.
11. **Pop**: tap top-left ◁ from any sub-page → returns directly to Dashboard (skipping Trip Landing).
12. **People**: from a trip with members, navigate via side drawer → People → see members with role badges, pending invites; admin can tap `+` to invite, swipe-left to remove.

If all 12 pass, the Trip Sub-Pages frontend is complete.
