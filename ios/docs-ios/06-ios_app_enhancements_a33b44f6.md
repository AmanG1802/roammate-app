---
name: iOS App Enhancements
overview: Comprehensive enhancements across My Trips, Profile, Dashboard, and Plan Trip pages in the iOS app, covering UX fixes, UI refactors, and feature additions to match the web app's functionality.
todos:
  - id: trips-fix-create-error
    content: Fix 'Internal Server Error' on manual trip create in CreateTripView (date format mismatch + error handling)
    status: completed
  - id: trips-fix-swipe-delete
    content: Fix swipe-to-delete in TripsTabView (swipeActions doesn't work in ScrollView, switch to List or custom gesture)
    status: completed
  - id: trips-tabs-upcoming-past
    content: Add floating pill toggle for Upcoming/Ongoing vs Past trips tabs in TripsTabView
    status: completed
  - id: trips-fab-and-multiselect
    content: Add floating '+' FAB at center bottom, replace top-right '+' with '3 dots' menu for multi-select delete
    status: completed
  - id: trips-random-icons
    content: Replace hardcoded airplane icon in TripRow with 8-icon collection using trip.id % count
    status: completed
  - id: profile-avatar-everywhere
    content: Fix profile picture rendering in ProfileTabView header and AvatarCircle to use avatarUrl with AsyncImage
    status: completed
  - id: widget-dots-color
    content: Fix page indicator dots color in TodayWidget using UIPageControl appearance
    status: completed
  - id: widget-ongoing-items
    content: Show Ongoing/UpNext/Next timeline items in InTripCard (fetch events for active trip)
    status: completed
  - id: widget-card-ordering
    content: "Reorder widget cards: Past(left) -> Ongoing(center, default) -> Upcoming(right)"
    status: completed
  - id: notif-rich-text
    content: Port web app's renderMessage() emoji-based notification text to iOS DashboardView
    status: completed
  - id: notif-panel-ux
    content: "Notification panel: 80% width from right, dropdown animation, auto-dismiss on mark-all-read"
    status: completed
  - id: plan-day-tabs-date-stops
    content: Show actual date and stop count below each day pill in DayTabsBar
    status: completed
  - id: plan-day-delete
    content: Add trash icon per day with bin/permanent delete confirmation dialog
    status: completed
  - id: timeline-card-refactor
    content: "Refactor TimelineRow: vertical color bar, 3-row layout, time pill, vote bottom-right, move-to-bin top-right"
    status: completed
  - id: timeline-hour-dots
    content: Add centered hour dots between timeline items (capped at 8 dots)
    status: completed
  - id: timeline-drag-reorder
    content: Implement hold-and-drop reorder for timeline cards with sort_order conflict resolution
    status: completed
  - id: timeline-card-expand
    content: Add tap-to-expand on timeline cards (like IdeaRow expanded content)
    status: completed
  - id: idea-card-refactor
    content: "Refactor IdeaRow: vertical color bar, time pill bubble, flush-right voting buttons"
    status: completed
  - id: brainstorm-card-refactor
    content: "Refactor brainstorm card: vertical color bar, 3 rows (title, category, time_hint), delete swoosh animation"
    status: completed
  - id: brainstorm-promote-time
    content: Use timeCategory from brainstorm items to set default times during promotion to idea bin
    status: completed
isProject: false
---

# iOS App Enhancements Plan

---

## 1. My Trips Page

### 1.1 Fix "Internal Server Error" on Manual Trip Create

**Root cause:** In [CreateTripView.swift](ios/Roammate/Views/Trips/CreateTripView.swift), the `create()` method calls `TripService.createTrip(payload)` which sends a POST and attempts to decode the response as a `Trip`. The trip is successfully created on the server, but the response likely includes fields that fail decoding (possibly the `my_role` field or a different response shape). The error surfaces as "Failed to parse response" which is the `decodingError` case in `APIError`, but the generic `.localizedDescription` renders it as "Internal Server Error."

**Fix:**
- Add debug logging in the `catch` block to surface the actual error.
- Inspect the API response shape from `POST /trips/` and ensure `Trip` model handles all optional fields gracefully. The `my_role` field is optional so that's fine, but the `endDate` from a manual create is `nil`, and if the server returns `null` vs omitting the field, the decoder should handle both (it does via `Optional`).
- Most likely fix: the `TripCreate` sends `startDate` via `dateTimeString` which formats as `yyyy-MM-dd'T'HH:mm:ss` (no timezone). If the server expects a date-only string for `start_date`, this mismatch causes a 500 on the server. Change the date format to `yyyy-MM-dd` for `CreateTripView` or handle both formats.
- Add a fallback: after the trip is created but decoding fails, still call `onCreated()` and dismiss so the UI stays consistent. Use `TripStore.create()` instead of calling `TripService` directly, so the store stays in sync.

**Files:** [CreateTripView.swift](ios/Roammate/Views/Trips/CreateTripView.swift), [Trip.swift](ios/Roammate/Models/Trip.swift)

### 1.2 Fix Swipe-to-Delete

**Root cause:** The `.swipeActions` modifier only works inside a `List` view, not inside a `LazyVStack` within a `ScrollView`. Currently `TripsTabView` uses `ScrollView > LazyVStack > ForEach > NavigationLink.swipeActions(...)` which silently does nothing.

**Fix:** Replace the custom swipe with a proper SwiftUI approach. Two options:
- **Option A (recommended):** Add a `.contextMenu` on each `TripRow` with a "Delete" option, plus implement a custom swipe gesture using `.gesture(DragGesture(...))` on each row that reveals a delete button.
- **Option B:** Switch the inner `ScrollView` + `LazyVStack` to a `List` styled with `.listStyle(.plain)` and `.listRowBackground(Color.clear)`.

Either way, the existing `.alert("Delete trip?")` confirmation dialog is already wired up correctly and will work once the swipe triggers `tripToDelete = trip`.

**Files:** [TripsTabView.swift](ios/Roammate/Views/Trips/TripsTabView.swift)

### 1.3 Ongoing/Upcoming vs Past Trips Tabs

Add a floating segmented pill at the top to toggle between "Upcoming" (ongoing + upcoming) and "Past" tabs.

**Implementation:**
- Add `@State private var selectedTab: TripTab = .upcoming` enum with `.upcoming` and `.past` cases.
- Add computed properties to filter `tripStore.trips`:
  - `upcomingTrips`: trips where `endDate == nil` or `endDate >= today`
  - `pastTrips`: trips where `endDate != nil && endDate < today`
- Add a floating `Picker` or custom `HStack` pill at the top of the scroll view with capsule-style toggle.
- Display only the relevant filtered list in each tab.

**Files:** [TripsTabView.swift](ios/Roammate/Views/Trips/TripsTabView.swift)

### 1.4 Floating "+" Button and Multi-Select Delete

**Changes:**
- **Remove** the `ToolbarItem(placement: .primaryAction)` "+" button from the top-right toolbar.
- **Add** a "3 dots" (`ellipsis.circle`) button in the top-right toolbar. When tapped, show a `Menu` with "Delete Trips" option.
- **Add** a floating "+" FAB at center bottom (just above the tab bar) that appears only when on the "Upcoming" tab. Use a `ZStack` overlay similar to the `ChatFAB` pattern on the Dashboard.
- When "Delete Trips" is tapped, enter a multi-select mode (`@State private var isDeleting = false`):
  - Show checkmarks on each trip row.
  - Replace the "3 dots" icon in toolbar with a trash icon.
  - Tapping trash confirms deletion of selected trips with a confirmation alert.
  - Cancel button to exit multi-select mode.

**Files:** [TripsTabView.swift](ios/Roammate/Views/Trips/TripsTabView.swift)

### 1.5 Random Trip Icons

Replace the hardcoded `airplane` icon in `TripRow` with one from a collection of 8 icons, selected deterministically based on the trip's `id`.

**Icon collection:**
```swift
static let tripIcons = [
    "airplane", "map.fill", "globe.americas.fill", "mountain.2.fill",
    "beach.umbrella.fill", "building.2.fill", "tent.fill", "sailboat.fill"
]
```

Selection: `tripIcons[trip.id % tripIcons.count]`

This also applies to trips created via Plan Trip AI chat (they go through the same `TripRow`).

**Files:** [TripRow.swift](ios/Roammate/Views/Trips/TripRow.swift)

---

## 2. Profile Page - Profile Picture Everywhere

**Root cause:** `ProfileTabView.header` renders initials in a `Circle` and never checks `authManager.currentUser?.avatarUrl`. Similarly, `AvatarCircle` (used in `TravellersStrip`, `PeoplePaneView`) ignores the `avatarUrl` parameter and always shows initials.

**Fix:**
- **`ProfileTabView.header`**: Add `AsyncImage` loading from `authManager.currentUser?.avatarUrl` with the initials circle as fallback (same pattern as `EditProfileView.avatarHero`).
- **`AvatarCircle`**: Add `AsyncImage` loading from the `avatarUrl` parameter. Currently the struct accepts `avatarUrl: String?` but never uses it. Add the image rendering with initials as fallback.

**Files:**
- [ProfileTabView.swift](ios/Roammate/Views/Profile/ProfileTabView.swift) - `header` computed property (lines 89-125)
- [TravellersStrip.swift](ios/Roammate/Views/Trips/TravellersStrip.swift) - `AvatarCircle` struct (lines 49-72)

---

## 3. Dashboard

### 3.1 Widget Page Indicator Dots Color

**Root cause:** The `TabView` with `.tabViewStyle(.page(indexDisplayMode: .always))` uses the system default white dots. The widget cards have light backgrounds, making the dots invisible.

**Fix:** Add `.indexViewStyle(.page(backgroundDisplayMode: .always))` (already present, but this doesn't help with the dot color). Instead, use UIKit appearance proxy on `.onAppear`:

```swift
.onAppear {
    UIPageControl.appearance().currentPageIndicatorTintColor = UIColor(.roammateIndigo)
    UIPageControl.appearance().pageIndicatorTintColor = UIColor(.roammateMuted.opacity(0.3))
}
```

**Files:** [TodayWidget.swift](ios/Roammate/Views/Dashboard/TodayWidget.swift)

### 3.2 Ongoing Trip Widget - Show Timeline Items

Enhance `InTripCard` to display the current day's timeline events:
- Show "Now" item (ongoing based on time), "Up Next" item, and the next item after that.
- If no "Now" item, show the next 3 upcoming items for the day.
- Each row: Name + start time icon on the right. No address.
- This requires passing events data into the widget. Update `TodayWidget` to accept or fetch the current day's events from `TripDetailStore`.

**Approach:** Since `TodayWidget` is on the Dashboard and doesn't have `TripDetailStore`, add a lightweight events fetch in `TodayWidget` or pass events from `DashboardView`. The simplest approach is to fetch events for the active trip in `DashboardView` and pass them down.

**Files:** [TodayWidgetCards.swift](ios/Roammate/Views/Dashboard/TodayWidgetCards.swift), [TodayWidget.swift](ios/Roammate/Views/Dashboard/TodayWidget.swift), [DashboardView.swift](ios/Roammate/Views/Dashboard/DashboardView.swift)

### 3.3 Widget Card Ordering

**Current:** The `cards` computed property builds: upcoming first, then current, then post.
**Required:** Past (left), Ongoing (center, default), Upcoming (right).

**Fix:** Reorder the `cards` array construction in `TodayWidget`:
1. Past trip card first (`.post`)
2. Ongoing trip card second (`.current`) - set as default selection
3. Upcoming trip card third (`.pre`)

Cap at 1 past, 1 ongoing, 1 upcoming.

**Files:** [TodayWidget.swift](ios/Roammate/Views/Dashboard/TodayWidget.swift)

### 3.4 Notifications - Rich Emoji Text

Port the web app's `renderMessage` function from [NotificationBell.tsx](frontend/components/layout/NotificationBell.tsx) (lines 54-117) to Swift. Create a `notificationTitle(_:)` function that:
- Extracts `actor_name`, `trip_name`, etc. from `notif.payload`
- Returns a single rich title string with emoji prefix matching the web app's pattern
- Each notification row shows only: Title (with emoji) and relative time
- Remove the separate actor name line and the icon circle

Notification types to support (from web):
- `trip_created` -> "You created {trip_name}."
- `trip_renamed` -> "You renamed {from} to {to}." / "{actor_name} renamed..."
- `trip_date_changed` -> "You changed dates for {trip_name}."
- `trip_deleted` -> "You deleted {trip_name}."
- `invite_received` -> "{inviter_name} invited you to {trip_name}."
- `invite_accepted` -> "You accepted {trip_name}." / "{joined_user_name} joined {trip_name}."
- `invite_declined` -> "{declined_user_name} declined the invite to {trip_name}."
- `member_removed`, `member_role_changed`, `group_created`, etc.
- `idea_bin_item_added`, `event_added`, `event_moved`, `event_removed`, `ripple_fired`

**Files:** [DashboardView.swift](ios/Roammate/Views/Dashboard/DashboardView.swift) (notification rendering functions)

### 3.5 Notification Panel UX

**Changes to the notification overlay:**
- Cover 80% width from the right instead of full width. Change `.padding(.horizontal, RoammateSpacing.md)` to `.frame(width: UIScreen.main.bounds.width * 0.8)` and align to `.topTrailing`.
- Add a dropdown animation from the bell icon position: use `.transition(.move(edge: .top).combined(with: .opacity))` and `.matchedGeometryEffect` or manual offset animation from the bell's position.
- On "Mark all read": auto-dismiss the notification panel after a short delay (0.8s) by setting `showNotifications = false` with animation.

**Files:** [DashboardView.swift](ios/Roammate/Views/Dashboard/DashboardView.swift) (lines 129-198)

---

## 4. Plan Trip Page

### 4.1 Day Tabs - Show Date and Stop Count

Refactor `DayTabsBar` and `TimelineDrawerContent`:
- Each day pill button shows "Day N" as the main label.
- Below each pill, show the actual date (e.g., "May 15") and stop count (e.g., "3 stops") in a subtitle row.
- Remove the current "Day 1 - 3 stops" section header text format.

**Implementation:** Change `dayTab` in `DayTabsBar` to accept the `TripDay` object and events count. Add a `VStack` inside the pill with the day number on top and "May 15 - 3 stops" below in a smaller font.

Requires passing `eventsByDay` counts to `DayTabsBar`.

**Files:** [DayTabsBar.swift](ios/Roammate/Views/Trips/Plan/DayTabsBar.swift), [TimelineDrawerContent.swift](ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift)

### 4.2 Day Delete Button

Add a trash icon button on the right side of the `<Date> - <Number of Stops>` row (the day section header in `TimelineDrawerContent`). On tap, show a `confirmationDialog` with two options:
- "Send items to Idea Bin" -> calls `store.deleteDay(id:, itemsAction: "bin")`
- "Delete permanently" -> calls `store.deleteDay(id:, itemsAction: "delete")`

This mirrors the web app behavior.

**Files:** [TimelineDrawerContent.swift](ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift)

### 4.3 Timeline Card Refactor

Redesign `TimelineRow`:
- **Remove** the photo/placeholder square icon on the left.
- **Add** a 4px-wide vertical color bar on the left edge of the card, colored by category using `Color.categoryColor(event.category)`.
- **Row 1:** Title
- **Row 2:** Category pill (colored by category - already using `Color.categoryTint`/`Color.categoryColor`)
- **Row 3:** Time (start + end) in a pill/bubble. Add pencil icon on the right to edit time.
- **Bottom Right:** Voting buttons (`ThumbsVoteControl`)
- **Top Right:** "Move to Idea Bin" button (calls `store.moveEventToBin(eventId:)`)
- **Hour dots between cards:** Add centered dots between each `TimelineRow` representing hours between items. Cap at 8 dots max. No dots before first or after last item.
- **Tap to expand:** Add expand/collapse behavior (like `IdeaRow`) to show description, address, rating, photo.
- **Drag and drop:** Add `.onMove` or long-press gesture + `MoveCommand` for reordering. On drop, update `sortOrder` via `EventService.updateEvent` and resolve time conflicts.

**Files:** [TimelineRow.swift](ios/Roammate/Views/Trips/Plan/TimelineRow.swift), [TimelineDrawerContent.swift](ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift)

### 4.4 Idea Bin Card Refactor

Redesign `IdeaRow`:
- **Remove** the square icon/image on the left (`ZStack` with `RoundedRectangle` and category icon, lines 37-44).
- **Add** a 4px-wide vertical color bar on the left edge using category color.
- **Category pill** is already colored by category (good).
- **Time row:** Wrap the time text in a pill-like bubble (`Capsule` background).
- **Voting buttons:** Move to the extreme right of the third row. Currently they have a `Spacer()` before them but there's also a gap from the right edge. Ensure they're flush to the trailing edge.

**Files:** [IdeaRow.swift](ios/Roammate/Views/Trips/Plan/IdeaRow.swift)

### 4.5 Brainstorm Bin Card Refactor

Redesign `brainstormRow` in `BrainstormBinView`:
- **Remove** the square icon on the left.
- **Add** a 4px-wide vertical color bar on the left edge using category color.
- **Category pill** already colored by category (good).
- **Show 3 rows:** Title, Category pill, Time hint (`item.timeCategory` or a formatted time category string from the AI response).
- **Delete animation:** On delete, add a `withAnimation(.spring) { }` transition that slides the card to the left (`.transition(.move(edge: .leading).combined(with: .opacity))`). Use `.animation` modifier on the `ForEach` with an `id`.

**Files:** [BrainstormBinView.swift](ios/Roammate/Views/Trips/Brainstorm/BrainstormBinView.swift)

### 4.6 Brainstorm-to-Idea Promotion: Use Time Hints

When promoting items from brainstorm bin to idea bin, the `timeCategory` field from the AI response should be used to set default times for each idea bin item. Currently `BrainstormStore.promote()` calls `BrainstormService.promote()` which is a backend operation. The backend should already handle this based on the web app's behavior - verify and fix if needed.

If the backend doesn't automatically set times from `timeCategory`, the iOS app should pass `timeCategory` in the promotion request or post-process after promotion by updating each new idea's time fields based on `timeCategory` mapping (e.g., "morning" -> 9:00 AM, "afternoon" -> 2:00 PM, "evening" -> 7:00 PM, "night" -> 9:00 PM).

**Files:** [BrainstormStore.swift](ios/Roammate/Store/BrainstormStore.swift), [BrainstormBinView.swift](ios/Roammate/Views/Trips/Brainstorm/BrainstormBinView.swift)

---

## Shared Utility: Category Color Vertical Bar

Create a reusable `CategoryColorBar` view used by Timeline, Idea Bin, and Brainstorm Bin cards:

```swift
struct CategoryColorBar: View {
    let category: String?
    var body: some View {
        RoundedRectangle(cornerRadius: 2)
            .fill(Color.categoryColor(category))
            .frame(width: 4)
    }
}
```

---

## File Change Summary

| Area | Files to Modify |
|------|----------------|

- **My Trips**: `TripsTabView.swift`, `CreateTripView.swift`, `TripRow.swift`, `Trip.swift`
- **Profile**: `ProfileTabView.swift`, `TravellersStrip.swift` (AvatarCircle)
- **Dashboard Widget**: `TodayWidget.swift`, `TodayWidgetCards.swift`, `DashboardView.swift`
- **Notifications**: `DashboardView.swift`
- **Plan Trip Day Tabs**: `DayTabsBar.swift`, `TimelineDrawerContent.swift`
- **Timeline**: `TimelineRow.swift`, `TimelineDrawerContent.swift`
- **Idea Bin**: `IdeaRow.swift`
- **Brainstorm Bin**: `BrainstormBinView.swift`, `BrainstormStore.swift`
- **Theme**: `RoammateTheme.swift` (add `CategoryColorBar` view)
