---
name: iOS Fixes Round 2
overview: Fix 11 bugs and enhancements across Brainstorm Bin, Idea Bin, Plan Trip Page, Dashboard Widget, and Notifications Panel in the iOS app.
todos:
  - id: category-colors
    content: Expand categoryColor/categoryTint/categoryIcon in RoammateTheme.swift to match web's 13 category groups with broad keyword matching
    status: completed
  - id: send-all-button
    content: Rename 'Send all' to 'Send all to Idea Bin' and change to RoammatePrimaryButtonStyle in BrainstormBinView.swift
    status: completed
  - id: brainstorm-delete-speed
    content: "Speed up brainstorm delete animation: spring response 0.15, sleep 150ms in BrainstormBinView.swift"
    status: completed
  - id: vote-buttons-position
    content: Move trash icon to title row in IdeaRow.swift so VStack expands fully and votes reach the right edge
    status: completed
  - id: time-hint-promotion
    content: Ensure promoted ideas with time defaults are reflected in TripDetailStore after BrainstormStore applies them
    status: completed
  - id: edit-time-fix
    content: Add custom encode(to:) on IdeaUpdate to skip nil fields; fix date picker day component in IdeaRow
    status: completed
  - id: idea-delete-animation
    content: Add slide-left delete animation to IdeaBinView/IdeaRow matching brainstorm pattern
    status: completed
  - id: timeline-not-rendering
    content: Normalize Date keys in TripDetailStore.eventsByDay to fix UTC vs local mismatch
    status: completed
  - id: day-tab-simplify
    content: Remove date and stop count subtitle from DayTabsBar day pills
    status: completed
  - id: widget-today-events
    content: Fix InTripCard.todayEvents to use UTC calendar for dayDate comparison
    status: completed
  - id: notification-animation
    content: Replace dropdown transition with scale-from-bell animation anchored at topTrailing
    status: completed
isProject: false
---

# iOS App Bug Fixes & Enhancements (Round 2)

## Brainstorm Bin

### 1. Grey categories — missing keyword coverage in color mapping

**Root Cause:** The iOS `categoryColor()` / `categoryTint()` in [RoammateTheme.swift](ios/Roammate/Theme/RoammateTheme.swift) uses exact-match on ~7 groups with few keywords each. The web's [categoryColors.ts](frontend/lib/categoryColors.ts) uses regex matching across **13 groups** with dozens of keyword variants per group. When the LLM returns categories like `"sightseeing"`, `"adventure"`, `"entertainment"`, `"temple"`, etc., iOS falls through to the grey default.

**Fix:** Rewrite `categoryColor()`, `categoryTint()`, and `categoryIcon()` in `RoammateTheme.swift` to use broad keyword matching (via `localizedCaseInsensitiveContains` or a helper) ported from the web's 13 category groups:

- Food/Dining (amber) — add: `eat`, `pub`, `bistro`, `bakery`, `cuisine`, `brunch`, `breakfast`, `lunch`, `dinner`, `snack`, `dessert`, `pizza`, `sushi`, `ramen`, `seafood`, `buffet`
- Culture/Arts (violet) — add: `gallery`, `theater`, `theatre`, `monument`, `exhibit`, `heritage`, `palace`, `castle`, `ruin`
- Nature/Outdoors (emerald) — add: `garden`, `trail`, `waterfall`, `lake`, `forest`, `mountain`, `island`, `canyon`, `wildlife`, `jungle`, `cliff`, `valley`
- Shopping (pink) — add: `mall`, `boutique`, `store`, `souvenir`, `retail`, `bazaar`, `flea`
- Nightlife (purple) — add: `nightclub`, `lounge`, `rooftop`, `cocktail`, `party`, `disco`
- Transport (sky/slate) — add: `airport`, `train`, `bus`, `ferry`, `port`, `station`, `subway`, `metro`, `taxi`, `flight`
- Accommodation (blue) — add: `hostel`, `resort`, `airbnb`, `lodg`, `inn`, `motel`, `villa`, `apartment`, `rental`
- **NEW: Entertainment** (fuchsia) — `entertainment`, `theme park`, `amusement`, `cinema`, `movie`, `concert`, `show`, `perform`, `festival`, `zoo`, `aquarium`
- **NEW: Sports/Adventure** (teal) — `sport`, `adventure`, `surf`, `dive`, `scuba`, `snorkel`, `ski`, `climb`, `kayak`, `cycle`, `bike`, `swim`, `skydiv`, `bungee`, `trek`, `rafting`
- **NEW: Wellness/Spa** (pink variant) — `spa`, `wellness`, `massage`, `yoga`, `meditat`, `gym`, `fitness`, `sauna`, `thermal`, `hot spring`, `retreat`
- **NEW: Religious/Spiritual** (stone) — `church`, `cathedral`, `temple`, `mosque`, `shrine`, `monastery`, `chapel`, `religious`, `spiritual`, `sacred`, `pagoda`
- **NEW: Landmarks/Viewpoints** (yellow) — `landmark`, `viewpoint`, `view`, `lookout`, `panorama`, `observation`, `tower`, `bridge`, `square`, `plaza`, `sight`
- **NEW: Activities/Tours** (orange) — `activity`, `experience`, `tour`, `class`, `workshop`, `lesson`, `cooking`, `craft`

Also add corresponding tint colors and SF Symbol icons for each new group. Use a helper function that checks if the lowercased category string contains any keyword in an array, to keep the code DRY.

---

### 2. "Send all" button — rename and restyle

**File:** [BrainstormBinView.swift](ios/Roammate/Views/Trips/Brainstorm/BrainstormBinView.swift), `bottomToolbar` (line ~283)

- Change label from `"Send all"` to `"Send all to Idea Bin"`
- Change style from `RoammateSecondaryButtonStyle()` to `RoammatePrimaryButtonStyle()` (filled indigo)

---

### 3. Brainstorm delete animation — make faster

**File:** [BrainstormBinView.swift](ios/Roammate/Views/Trips/Brainstorm/BrainstormBinView.swift)

- Line ~47: Change `.animation(.spring(response: 0.4, dampingFraction: 0.75), ...)` to `.animation(.spring(response: 0.15, dampingFraction: 0.9), ...)`
- Line ~173: Reduce sleep from `300_000_000` (300ms) to `150_000_000` (150ms)

---

## Idea Bin

### 4. Voting buttons not at extreme right

**File:** [IdeaRow.swift](ios/Roammate/Views/Trips/Plan/IdeaRow.swift)

**Root Cause:** The trash button sits outside the inner `VStack` at the outer `HStack` level (lines 93-104), eating horizontal space. The `ThumbsVoteControl` is inside the `VStack`, so it can never reach the card's right edge.

**Fix:** Move the trash icon into the title row (first line, top-right — same pattern as `TimelineRow` uses with `tray.and.arrow.down`). Remove the separate trash button from the outer `HStack`. This lets the inner `VStack` expand fully, and `Spacer()` before `ThumbsVoteControl` will push votes to the true right edge.

---

### 5. Brainstorm-to-Idea promotion not using time_hint

**Files:** [BrainstormStore.swift](ios/Roammate/Store/BrainstormStore.swift), [TripDetailStore.swift](ios/Roammate/Store/TripDetailStore.swift)

**Root Cause:** `applyTimeCategoryDefaults()` fires in `BrainstormStore` and updates ideas on the backend, but the `onIdeasPromoted` callback has already fired with the **original** (time-less) promoted items. The local `TripDetailStore.ideas` array never receives the updated times.

**Fix:** After `applyTimeCategoryDefaults` completes its backend updates, trigger a reload of ideas in `TripDetailStore`. Options:
- Add an `onIdeasTimeUpdated` callback that tells `TripDetailStore` to re-fetch ideas
- Or simply call `await TripDetailStore.loadIdeas()` (a new lightweight method that re-fetches just ideas) after `applyTimeCategoryDefaults`
- Or have `applyTimeCategoryDefaults` return the updated items and pass them via a second callback

---

### 6. Edit time not applying on Idea Bin items

**Files:** [IdeaBinItem.swift](ios/Roammate/Models/IdeaBinItem.swift) (`IdeaUpdate`), [IdeaRow.swift](ios/Roammate/Views/Trips/Plan/IdeaRow.swift)

**Root Cause:** `IdeaUpdate` uses a standard `Encodable` conformance. When `title: nil` is encoded, Swift's default `encode(to:)` encodes it as `"title": null` in JSON. The backend PATCH endpoint may interpret `null` as "set title to null" rather than "leave title unchanged".

**Fix:**
- Add a custom `encode(to:)` on `IdeaUpdate` that uses `encodeIfPresent` for all optional fields, so nil values are omitted from the JSON payload entirely
- In `IdeaRow.timeEditSheet`, when initializing `editStart`/`editEnd`, preserve the day component from the idea's existing `startTime` if available (not just `Date()`)

---

### 7. Idea Bin delete animation (slide left)

**Files:** [IdeaBinView.swift](ios/Roammate/Views/Trips/Plan/IdeaBinView.swift), [IdeaRow.swift](ios/Roammate/Views/Trips/Plan/IdeaRow.swift)

**Current:** No animation on delete. `store.deleteIdea()` just removes the item from the array.

**Fix:**
- Add `@State private var deletingId: Int?` to `IdeaBinView`
- Pass `deletingId` and an `onDelete` closure to `IdeaRow`
- In `IdeaRow`, when trash is tapped: set `deletingId`, wait 150ms, then call `store.deleteIdea()`
- Wrap each `IdeaRow` in a conditional `if deletingId != idea.id` with `.transition(.asymmetric(insertion: .opacity, removal: .move(edge: .leading).combined(with: .opacity)))`
- Use `.animation(.spring(response: 0.15, dampingFraction: 0.9), value: store.ideas.map(\.id))`

---

## Plan Trip Page

### 8. Timeline items not rendering

**File:** [TripDetailStore.swift](ios/Roammate/Store/TripDetailStore.swift), `loadAll()` (line ~53)

**Root Cause:** `eventsByDay` is built via:
```swift
Dictionary(grouping: events, by: { $0.dayDate ?? .distantPast })
```
But `dayDate` is decoded from `"2026-05-15"` using the UTC `dateOnly` formatter, producing `2026-05-15T00:00:00Z`. Meanwhile, `TripDay.date` is decoded from the same `"2026-05-15"` string but may go through a different formatter path (e.g., `iso` or `dateTimeNoTZ`), producing a slightly different `Date` value. When `store.eventsByDay[day.date]` does the lookup, the keys don't match.

**Fix:** Normalize all date keys to `Calendar(identifier: .iso8601)` with UTC timezone's `startOfDay`. Add a helper:
```swift
private static func normalizedDay(_ date: Date) -> Date {
    var cal = Calendar(identifier: .iso8601)
    cal.timeZone = TimeZone(identifier: "UTC")!
    return cal.startOfDay(for: date)
}
```
Use it when grouping events and when looking up by `TripDay.date`.

---

### 9. Remove date and stops from Day Tab pills

**File:** [DayTabsBar.swift](ios/Roammate/Views/Trips/Plan/DayTabsBar.swift), `dayTab()` (lines ~111-118)

**Fix:** Remove the subtitle `Text` line that shows `"\(dateStr) · \(stopCount) stops"`. Keep only `"Day \(day.dayNumber)"`. Can also remove the `eventCounts` property and `dateFormatter` since they become unused. Clean up callers that pass `eventCounts`.

---

## Widget on Dashboard

### 10. Widget not showing scheduled items for ongoing trip

**File:** [TodayWidgetCards.swift](ios/Roammate/Views/Dashboard/TodayWidgetCards.swift), `InTripCard.todayEvents` (lines ~160-169)

**Root Cause:** Same UTC vs local timezone mismatch. `event.dayDate` is UTC midnight, but `Calendar.current.isDate(dayDate, inSameDayAs: todayStart)` uses the device's local calendar. In UTC+5:30, `2026-05-15T00:00:00Z` is actually `2026-05-14T18:30:00 IST`, so it matches May 14 instead of May 15.

**Fix:** Use a UTC calendar for the date comparison:
```swift
private var todayEvents: [Event] {
    var utcCal = Calendar(identifier: .iso8601)
    utcCal.timeZone = TimeZone(identifier: "UTC")!
    let todayUTC = utcCal.startOfDay(for: Date())
    return events.filter { event in
        guard let dayDate = event.dayDate else { return false }
        return utcCal.isDate(dayDate, inSameDayAs: todayUTC)
    }
    .sorted { $0.sortOrder < $1.sortOrder }
}
```

---

## Notifications Panel

### 11. Scale-from-bell animation (replace dropdown)

**File:** [DashboardView.swift](ios/Roammate/Views/Dashboard/DashboardView.swift), `notificationsOverlay` (lines ~213-216)

**Current:** `.transition(.asymmetric(insertion: .opacity.combined(with: .move(edge: .top)), removal: .opacity.combined(with: .move(edge: .top))))`

**Fix:** Replace with a scale+opacity transition anchored at the bell icon's position (top-trailing):
```swift
.transition(.asymmetric(
    insertion: .scale(scale: 0.01, anchor: .topTrailing).combined(with: .opacity),
    removal: .scale(scale: 0.01, anchor: .topTrailing).combined(with: .opacity)
))
```
Also update the wrapping `withAnimation` calls (bell tap, mark-all-read, background tap) to use a smooth spring: `.spring(response: 0.35, dampingFraction: 0.8)` for a flowy feel.

---

## Files to Modify (Summary)

- `ios/Roammate/Theme/RoammateTheme.swift` — expand category color/tint/icon matching (issue 1)
- `ios/Roammate/Views/Trips/Brainstorm/BrainstormBinView.swift` — button text + style, animation speed (issues 2, 3)
- `ios/Roammate/Views/Trips/Plan/IdeaRow.swift` — vote button position, delete animation, time edit fix (issues 4, 6, 7)
- `ios/Roammate/Views/Trips/Plan/IdeaBinView.swift` — delete animation state (issue 7)
- `ios/Roammate/Models/IdeaBinItem.swift` — IdeaUpdate custom encoding (issue 6)
- `ios/Roammate/Store/BrainstormStore.swift` — reload ideas after time defaults applied (issue 5)
- `ios/Roammate/Store/TripDetailStore.swift` — normalize date keys, add ideas reload (issues 5, 8)
- `ios/Roammate/Views/Trips/Plan/DayTabsBar.swift` — remove date/stops subtitle (issue 9)
- `ios/Roammate/Views/Dashboard/TodayWidgetCards.swift` — UTC calendar for today filter (issue 10)
- `ios/Roammate/Views/Dashboard/DashboardView.swift` — scale-from-bell animation (issue 11)