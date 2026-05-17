---
name: iOS Bug Fixes and Enhancements
overview: Fix 10 bugs and implement enhancements across trip management, tab bar visibility, profile picture upload, idea bin cards, day management, widget styling, and manual trip creation in the iOS app.
todos:
  - id: delete-trip
    content: "Add delete trip: swipe action in TripsTabView + destructive option in TripSubPagesHost dropdown"
    status: completed
  - id: tab-bar-trip-landing
    content: Hide tab bar on TripLandingView and fix Profile sub-page tab bar hiding
    status: completed
  - id: profile-picture
    content: Add profile picture upload via PhotosPicker in EditProfileView + avatar display
    status: completed
  - id: trip-landing-style
    content: Larger/dramatic trip title with gradient text, bigger date, dark invite popup
    status: completed
  - id: add-day-fix
    content: "Fix Add Day not working: recompute sortedDays after await in addNextDay()"
    status: completed
  - id: menu-button-round
    content: Make menu toggle button fully circular in TripSubPagesHost
    status: completed
  - id: idea-bin-restructure
    content: "Restructure IdeaRow: category icon, remove collapsed address, add time row with edit, votes in time row"
    status: completed
  - id: brainstorm-bin-restructure
    content: "Restructure BrainstormBinView rows: category icon, remove collapsed address"
    status: completed
  - id: edit-date-fix
    content: "Fix edit date on TripLandingView: use dateValue for display + reload after save"
    status: completed
  - id: widget-fixes
    content: "Widget: remove top-right icons, title/stats at top, match web color scheme"
    status: completed
  - id: trip-create-fix
    content: "Fix manual trip creation 500 error: encode startDate as yyyy-MM-dd string"
    status: completed
isProject: false
---

# iOS Bug Fixes and UI Enhancements (Round 2)

## 1. Delete Trip Functionality

**Placement**: Add a swipe-to-delete action on each `TripRow` in `TripsTabView`, plus a destructive "Delete Trip" button inside the overlay dropdown menu on `TripSubPagesHost`.

**Files**:
- [TripsTabView.swift](ios/Roammate/Views/Trips/TripsTabView.swift) -- Add `.swipeActions` with a red trash button to each `TripRow` `ForEach` item. Call `tripStore.delete(id:)` with a confirmation alert.
- [TripSubPagesHost.swift](ios/Roammate/Views/Trips/TripSubPagesHost.swift) -- Add a "Delete Trip" destructive option at the bottom of `dropdownMenu`, separated by a divider. On confirm, call `TripService.deleteTrip`, then `popToRoot()`.
- [TripRow.swift](ios/Roammate/Views/Trips/TripRow.swift) -- No structural change, but the row already exists as the unit to swipe on.

The `TripStore.delete(id:)` and `TripService.deleteTrip(id:)` already exist and work.

---

## 2. Tab Bar Still Visible on Trip Landing Page and Profile Sub-pages

**Root cause**: `TripLandingView` does not inject or manipulate `tabBarVisibility`. The `ProfileTabView` uses `NavigationDepthTracker` which has a timing/lifecycle issue -- `viewWillAppear`/`viewDidAppear` may not fire reliably for all SwiftUI-driven navigation pushes.

**Fix for Trip Landing Page**:
- [TripLandingView.swift](ios/Roammate/Views/Trips/TripLandingView.swift) -- Add `@EnvironmentObject var tabBarVisibility: TabBarVisibility`. In `.onAppear { tabBarVisibility.isVisible = false }` and `.onDisappear { tabBarVisibility.isVisible = true }`.

**Fix for Profile Sub-pages**:
- [ProfileTabView.swift](ios/Roammate/Views/Profile/ProfileTabView.swift) -- The `NavigationDepthTracker` (`UIViewControllerRepresentable`) approach is unreliable. Replace with the simpler pattern used in `TripSubPagesHost`: wrap each destination in a container that sets `tabBarVisibility.isVisible = false` on appear and `true` on disappear. Create a small `TabBarHidingWrapper<Content: View>` modifier that encapsulates this.

---

## 3. Profile Picture Upload

**Files**:
- [EditProfileView.swift](ios/Roammate/Views/Profile/EditProfileView.swift) -- Replace the static gradient circle avatar with a tappable `PhotosPicker` or `ImagePicker` overlay. On selection, upload the image via a new `AuthService.uploadAvatar(imageData:)` API call that posts multipart form data to the backend. If the backend does not support image upload, use a presigned URL or base64 encoding flow.
- [AuthService.swift](ios/Roammate/Network/AuthService.swift) -- Add `uploadAvatar(imageData: Data) async throws -> User` that POSTs to `/users/me/avatar` (or updates `avatar_url` via `updateMe` if the backend expects a URL).
- [User.swift](ios/Roammate/Models/User.swift) -- Already has `avatarUrl: String?`.

The avatar hero section will:
1. Show the actual profile image if `avatarUrl` is set (using `AsyncImage`).
2. Show a camera overlay icon on the circle.
3. Open `PhotosPicker` (from `PhotosUI`) on tap.
4. Upload and update `authManager.currentUser`.

---

## 4. Trip Landing Page -- Larger Title, Dramatic Font, Dark Invite Popup

**Files**:
- [TripLandingView.swift](ios/Roammate/Views/Trips/TripLandingView.swift)

**Changes**:
- **Title font**: Increase from `size: 34` to `size: 42` or larger. Add a multicolor gradient overlay using `.foregroundStyle(...)` with a `LinearGradient` of white-to-violet tones (similar to web's gradient text effect):

```swift
Text(trip.name)
    .font(.system(size: 44, design: .serif).weight(.black))
    .foregroundStyle(
        LinearGradient(colors: [.white, Color.roammateViolet.opacity(0.8), .white],
                       startPoint: .leading, endPoint: .trailing)
    )
```

- **Date font**: Increase from `.subheadline` to `.title3` or `.headline` weight.
- **Invite overlay**: Change the popup background from `Color.roammateSurface` (white) to the dark spectrum. Replace with `Color(red: 30/255, green: 30/255, blue: 60/255)` fill, and update the text colors inside (labels white/light, inputs with dark bg style, role pills adjusted). The `TextField` and role buttons get dark-mode-compatible styling.

---

## 5. Add Day Not Working on Plan Page

**Root cause**: In [TimelineDrawerContent.swift](ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift), the `addNextDay()` function calls `await store.addDay(date: nextDate)` and then immediately sets `selectedDayIndex = sortedDays.count - 1`. However, `sortedDays` is a computed property derived from `store.days`, and the `@Published` update from `addDay` may not have reflected in the computed property by the time the index is set.

**Fix**:
- In `addNextDay()`, after `await store.addDay(date: nextDate)`, recompute from `store.days` directly:

```swift
private func addNextDay() async {
    let nextDate: Date
    if let lastDay = sortedDays.last {
        nextDate = Calendar.current.date(byAdding: .day, value: 1, to: lastDay.date) ?? Date()
    } else if let tripStart = store.trip?.startDate {
        nextDate = tripStart
    } else {
        nextDate = Date()
    }
    await store.addDay(date: nextDate)
    let updatedDays = store.days.sorted { $0.dayNumber < $1.dayNumber }
    withAnimation {
        selectedDayIndex = max(0, updatedDays.count - 1)
    }
}
```

Also verify that `TripDetailStore.addDay(date:)` correctly parses the server response. The `TripDayService.addDay` sends a date string -- confirm it matches what the backend expects (ISO date `yyyy-MM-dd`). Check that the `trip.startDate` is not nil when there are no days yet (it could be causing an incorrect date to be sent).

---

## 6. Menu Button Not Fully Rounded

**File**: [TripSubPagesHost.swift](ios/Roammate/Views/Trips/TripSubPagesHost.swift)

The menu toggle button (line 109-118) uses a raw `Image(systemName:)` without an explicit circular frame and clip shape.

**Fix**: Wrap the menu button icon in a circle:

```swift
Image(systemName: showMenu ? "xmark" : "line.3.horizontal")
    .font(.system(size: 16, weight: .semibold))
    .foregroundStyle(Color.roammateInk)
    .frame(width: 36, height: 36)
    .background(
        Circle().fill(Color.roammateSurface)
    )
    .overlay(Circle().stroke(Color.roammateBorder, lineWidth: 0.5))
```

---

## 7. Idea Bin and Brainstorm Bin Card Restructuring

### 7a. IdeaRow -- Remove address from collapsed view, add time row, category icon in left square

**File**: [IdeaRow.swift](ios/Roammate/Views/Trips/Plan/IdeaRow.swift)

**Changes**:
- **Left square icon**: Replace `"mappin.fill"` with `Color.categoryIcon(idea.category)` so it shows the correct category-specific icon (fork.knife, building.columns, etc.) using the existing `categoryIcon()` function in `RoammateTheme.swift`.
- **Remove address from collapsed card** (line 49-54): Delete the address `Text` from the second row.
- **Add time row** (third row in collapsed card): Show `startTime` and `endTime` formatted as "h:mm a" with an edit option (small pencil icon that opens a time picker sheet or inline picker). The votes (`ThumbsVoteControl`) stay on the right of this time row, always visible (not in expanded section).
- **Move votes to third row**: Instead of a separate `HStack` below everything, place `ThumbsVoteControl` in the same row as the time display. Remove the separate vote section that only appears when not selecting.
- **Expanded section**: Address now moves here (it was already shown in expanded, but also remove the duplicate from collapsed).

**File**: [IdeaBinView.swift](ios/Roammate/Views/Trips/Plan/IdeaBinView.swift) -- May need to pass an `onUpdateTime` closure.

**File**: [TripDetailStore.swift](ios/Roammate/Store/TripDetailStore.swift) -- Add `updateIdea(ideaId: Int, fields: IdeaUpdate) async` method calling `IdeaService.updateIdea(...)` and updating the local array.

### 7b. BrainstormBinView -- Same restructuring

**File**: [BrainstormBinView.swift](ios/Roammate/Views/Trips/Brainstorm/BrainstormBinView.swift)

Same changes as IdeaRow:
- Left square uses `Color.categoryIcon(item.category)` instead of `"mappin.fill"`.
- Remove address from collapsed view.
- No time row needed for brainstorm items (they don't have time fields).
- No voting (already the case).

---

## 8. Edit Date on Trip Landing Page Not Working

**File**: [TripLandingView.swift](ios/Roammate/Views/Trips/TripLandingView.swift)

**Root cause**: `saveDate()` calls `TripService.updateTrip(id: trip.id, update: ...)` but the `trip` is a `let` constant passed into the view. After saving, the local `trip` object is not updated, and the displayed `startDateText` still reads from the original `trip.startDate`.

**Fix**:
- After the `saveDate()` call, update the displayed date. Since `trip` is a `let`, we need to either:
  1. Read the date from `dateValue` (the `@State` binding) for display instead of `trip.startDate`, OR
  2. Reload `store.trip` after saving and use `store.trip?.startDate`.

Simplest fix: Change `startDateText` to use `dateValue` as the source of truth (it's already initialized from `trip.startDate` in `onAppear`):

```swift
private var startDateText: String {
    let f = DateFormatter()
    f.dateFormat = "MMM d, yyyy"
    return f.string(from: dateValue)
}
```

Also, call `store.loadAll()` after saving to refresh the trip data.

---

## 9. Dashboard Widget Fixes

**Files**:
- [TodayWidget.swift](ios/Roammate/Views/Dashboard/TodayWidget.swift)
- [TodayWidgetCards.swift](ios/Roammate/Views/Dashboard/TodayWidgetCards.swift)

**Changes**:

- **Slidable**: The `TabView` with `.tabViewStyle(.page)` should already be swipeable. If the issue is that all upcoming trips aren't shown (only one per category), modify the `cards` computed property to include multiple upcoming trips (not just the nearest one), or at minimum show all categorizable trips.

- **Remove top-right icons entirely**: Remove the airplane icon from `PreTripCard`, the sun icon from `InTripCard`, and the sparkles icon from `PostTripCard`. The user explicitly says "I don't want the stars icon on top right of the widget."

- **Trip title and stats at top**: Restructure each card so the trip name, date, and summary stats appear at the **top** of the card (right after the badge pill), matching the web layout where `<h2>` trip name comes first.

- **Color scheme matching web app exactly**: The web app uses `HeroShell` with a `tone` parameter. All three tones use **light pastel gradient backgrounds** (not dark/bold), with dark text for the title:
  - **Pre-trip (tone="indigo")**: `bg-gradient-to-br from-indigo-50 to-white` with `text-indigo-600` badge. iOS equivalent: `LinearGradient(colors: [Color.roammateIndigoTint, .white])` with indigo-colored badge and **dark slate text** for the trip name (not white).
  - **In-trip (tone="amber")**: `bg-gradient-to-br from-amber-50 to-white` with `text-amber-600` badge. iOS equivalent: `LinearGradient(colors: [Color.roammateAmberTint, .white])` with amber-colored badge and **dark slate text** for the trip name.
  - **Post-trip (tone="rose")**: `bg-gradient-to-br from-rose-50 to-white` with `text-rose-600` badge. iOS equivalent: `LinearGradient(colors: [Color(red: 255/255, green: 241/255, blue: 242/255), .white])` with rose/danger-colored badge and **dark slate text** for the trip name.

  Key differences from current iOS implementation:
  - Current iOS uses **dark/bold full-color gradients** (indigo-to-indigoDark, amber-to-danger, ink-to-indigo) with **white text**
  - Web uses **very light pastel-to-white gradients** with **dark text** (`text-slate-900` for titles, `text-slate-500` for secondary)
  - CTA buttons: Pre-trip has an indigo CTA, In-trip has a dark slate CTA, Post-trip has a rose CTA
  - The border is `border-slate-100` (very subtle light border)

- **Widget layout per web**: Each card should have:
  1. **Top**: Badge pill (e.g. "X days to go", "Day N of M", "Wrapped X days ago") -- small uppercase text
  2. **Below badge**: Trip name (large, bold, `slate-900` / `.roammateInk` colored)
  3. **Below name**: Date or stats subtitle (small, `slate-500` / `.roammateMuted` colored)
  4. **Bottom-right**: CTA button (e.g. "Plan Itinerary", "Open Trip", "See Recap") as a small pill
  5. For In-trip specifically: 3 event slots below the header (ongoing/next/upcoming) -- can simplify to showing event count and a progress bar for iOS
  6. The countdown number ("48 days to go") stays but text color should be dark, not white

---

## 10. Manual Trip Creation Internal Server Error

**File**: [CreateTripView.swift](ios/Roammate/Views/Trips/CreateTripView.swift)

**Root cause**: The `TripCreate` sends `endDate: nil` via `encodeIfPresent`, which omits the key entirely. However, the backend may be expecting `end_date` as a required field or null-encoded.

**Investigation/Fix**:
- Check whether the backend requires `end_date` to be present (even as `null`). If so, change `TripCreate.encode(to:)` to use `try container.encodeNil(forKey: .endDate)` when `endDate` is nil instead of skipping it.
- Alternatively, the error may be from the `startDate` format. The `JSONEncoder` with `.iso8601` encodes as a full datetime string (`2026-05-15T00:00:00Z`), but the backend might expect only a date string (`2026-05-15`). If so, use a custom date formatter for `startDate` in the encoder.

The most likely fix (based on FastAPI backend patterns) is that the backend expects a date-only string for `start_date`, not an ISO datetime. Change the `TripCreate` encoding to format dates as `yyyy-MM-dd`:

```swift
func encode(to encoder: Encoder) throws {
    var container = encoder.container(keyedBy: CodingKeys.self)
    try container.encode(name, forKey: .name)
    try container.encode(timezone, forKey: .timezone)
    if let startDate {
        try container.encode(dateString(startDate), forKey: .startDate)
    }
    // Omit endDate entirely when nil
}

private func dateString(_ date: Date) -> String {
    let f = DateFormatter()
    f.calendar = Calendar(identifier: .iso8601)
    f.timeZone = TimeZone(identifier: "UTC")
    f.dateFormat = "yyyy-MM-dd"
    return f.string(from: date)
}
```

This matches the pattern already used in `TripDayService.isoDate()`.
