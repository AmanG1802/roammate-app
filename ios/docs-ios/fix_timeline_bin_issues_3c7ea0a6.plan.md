---
name: Fix Timeline Bin Issues
overview: "Fix 5 bugs in the iOS Trip Plan Timeline: smart day-delete confirmation, day renumbering after deletion, items lost on day-delete-to-bin, timeline items not rendering, and ideas not removed after transfer to timeline."
todos:
  - id: issue1-day-delete-confirm
    content: In TimelineDrawerContent.swift, conditionally show bin confirmation only when day has events; skip dialog for empty days
    status: completed
  - id: issue2-day-renumber
    content: In TimelineDrawerContent.swift, clamp selectedDayIndex after deleteDay completes for both bin and delete actions
    status: completed
  - id: issue3-ideas-refresh
    content: In TripDetailStore.deleteDay(), add explicit reloadIdeas() call after loadAll() when itemsAction is bin
    status: completed
  - id: issue4-event-encoding
    content: "Add custom encode(to:) to EventCreate in Event.swift: encode dayDate as YYYY-MM-DD string, use encodeIfPresent for optionals"
    status: completed
  - id: issue4-error-surfacing
    content: In AddToTimelineSheet.addToTimeline(), log errors from EventService.createEvent and call store.loadAll() after task group
    status: completed
  - id: issue5-backend-delete-idea
    content: In backend events.py create_event(), delete the source idea after transferring votes when source_idea_id is provided
    status: completed
  - id: issue5-ios-delete-idea
    content: In AddToTimelineSheet.addToTimeline(), call IdeaService.deleteIdea() after successful event creation as defense in depth
    status: completed
isProject: false
---

# Fix Timeline Bin Issues in iOS Trip Plan Page

## Issue 1: Day delete should only ask for bin option if day has events

**File:** [TimelineDrawerContent.swift](ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift)

**Root Cause:** The trash button always sets `dayToDelete`, which triggers a `confirmationDialog` with "Send items to Idea Bin" / "Delete permanently" options regardless of whether the day has any events.

**Fix:** Before presenting the dialog, check if the day has events. If the day is empty, skip the confirmation and delete directly (or show a simpler "Delete empty day?" confirmation). Compute `eventsForDay(day)` using the same `normalizedDay()` lookup used by `currentEvents`.

```swift
// In daySectionHeader, when trash is tapped:
let key = TripDetailStore.normalizedDay(day.date)
let hasEvents = !(store.eventsByDay[key] ?? []).isEmpty
if hasEvents {
    dayToDelete = day  // shows existing confirmation dialog
} else {
    Task { await store.deleteDay(id: day.id, itemsAction: "delete") }
}
```

---

## Issue 2: Day pills don't renumber / left-shift after deletion

**Files:** [TimelineDrawerContent.swift](ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift), [TripDetailStore.swift](ios/Roammate/Store/TripDetailStore.swift)

**Root Cause:** Two problems:
1. `selectedDayIndex` is not clamped after a day is deleted. If the user deletes the last day, the index points out of range and nothing is highlighted.
2. After `deleteDay` removes the local day and calls `loadAll()`, the `loadAll()` fetches fresh days with updated `dayNumber` values from the backend (the backend properly left-shifts). However, there is no adjustment of `selectedDayIndex`.

**Fix:**
- In `TimelineDrawerContent`, after the `deleteDay` call completes, clamp `selectedDayIndex`:

```swift
Button("Send items to Idea Bin") {
    if let day = dayToDelete {
        Task {
            await store.deleteDay(id: day.id, itemsAction: "bin")
            let count = store.days.count
            if selectedDayIndex >= count {
                selectedDayIndex = max(0, count - 1)
            }
        }
    }
}
```

- Apply the same clamping for the "Delete permanently" button.

---

## Issue 3: Items lost when deleting day with "send to Idea Bin"

**File:** [TripDetailStore.swift](ios/Roammate/Store/TripDetailStore.swift)

**Root Cause:** `deleteDay()` calls `loadAll()` which should fetch fresh ideas (including ones the backend just created from the deleted day's events). The backend endpoint at [trips.py L911-927](backend/app/api/endpoints/trips.py) correctly creates `IdeaBinItem` rows from events when `items_action == "bin"`. However, `loadAll()` uses `async let` for 5 parallel requests -- if ANY one fails (e.g., the trip fetch), the entire block throws and `self.ideas` is never updated.

**Fix:** Make the post-delete refresh more resilient. Instead of relying solely on `loadAll()`, add an explicit `reloadIdeas()` call after deletion with `items_action == "bin"`:

```swift
func deleteDay(id: Int, itemsAction: String = "bin") async {
    do {
        try await TripDayService.deleteDay(tripId: tripId, dayId: id, itemsAction: itemsAction)
        days.removeAll { $0.id == id }
        DiskCache.shared.store(days, key: daysCacheKey)
    } catch let e as APIError {
        error = e.errorDescription
        return
    } catch {
        self.error = error.localizedDescription
        return
    }
    // Refresh all data; reload ideas separately as a safety net
    await loadAll()
    if itemsAction == "bin" {
        await reloadIdeas()
    }
}
```

This ensures ideas are refreshed even if other parts of `loadAll()` fail.

---

## Issue 4: Timeline items not rendering (CRITICAL)

**Root Cause:** This is intertwined with Issue 5. When items are "added to timeline" from the Idea Bin via [AddToTimelineSheet.swift](ios/Roammate/Views/Trips/Plan/AddToTimelineSheet.swift), the backend's `create_event` endpoint is called. However, `EventCreate` uses the default Swift `Encodable` conformance, which encodes `dayDate: Date?` as a full ISO 8601 datetime string (e.g., `"2026-05-15T00:00:00Z"`). The backend schema expects `day_date: Optional[date]` (Python `date`). While Pydantic v2 lax mode should accept this, any encoding failure or response decoding error is silently caught:

```swift
// AddToTimelineSheet.swift L148-152
do {
    let event = try await EventService.createEvent(create)
    return (event, idea.id)
} catch {
    return (nil, idea.id)  // <-- silently swallows ALL errors
}
```

If the API call fails or response decoding fails, `event` is `nil`, so neither is the event added to `eventsByDay` nor the idea removed from `ideas`.

**Fix (multi-part):**

**4a.** Add custom `encode(to:)` to `EventCreate` in [Event.swift](ios/Roammate/Models/Event.swift) that encodes `dayDate` as a "YYYY-MM-DD" date-only string (matching the backend's `date` type), and uses `encodeIfPresent` for optional fields to avoid sending nulls:

```swift
func encode(to encoder: Encoder) throws {
    var container = encoder.container(keyedBy: CodingKeys.self)
    try container.encode(tripId, forKey: .tripId)
    try container.encode(title, forKey: .title)
    // ... encodeIfPresent for all optionals ...
    if let dayDate {
        let fmt = DateFormatter()
        fmt.calendar = Calendar(identifier: .iso8601)
        fmt.timeZone = TimeZone(identifier: "UTC")
        fmt.dateFormat = "yyyy-MM-dd"
        try container.encode(fmt.string(from: dayDate), forKey: .dayDate)
    }
    // encode startTime/endTime as ISO 8601 datetime
    // ...
}
```

**4b.** Surface errors from `addToTimeline()` instead of silently returning nil. Add an error state or at least print the error for debugging:

```swift
} catch {
    print("[AddToTimeline] Event creation failed: \(error)")
    return (nil, idea.id)
}
```

**4c.** After the `withTaskGroup` completes in `addToTimeline()`, call `store.loadAll()` as a safety net to ensure the local state matches the backend:

```swift
// After withTaskGroup block:
await store.loadAll()
```

---

## Issue 5: Ideas not removed from Idea Bin after transfer to Timeline (CRITICAL)

**Root Cause:** The backend's `create_event` endpoint at [events.py L70-93](backend/app/api/endpoints/events.py) copies fields from the source idea and transfers votes, but **does NOT delete the source idea**. The iOS client removes it locally (`store.ideas.removeAll { $0.id == ideaId }`), but:
- On app reload, `loadAll()` fetches fresh ideas from the backend, and the "deleted" idea reappears
- If the event creation throws (see Issue 4), even the local removal doesn't happen

**Fix (two-pronged):**

**5a. Backend fix:** In [events.py](backend/app/api/endpoints/events.py) `create_event()`, after transferring votes from the source idea, delete the source idea:

```python
# After vote transfer (around line 93):
if event_in.source_idea_id is not None:
    src_idea_del = (await db.execute(
        select(IdeaBinItemModel).where(
            IdeaBinItemModel.id == event_in.source_idea_id
        )
    )).scalars().first()
    if src_idea_del:
        await db.delete(src_idea_del)
        await db.commit()
```

**5b. iOS fallback:** In `addToTimeline()`, after successfully creating each event, also call the delete-idea API to ensure backend consistency:

```swift
if let event {
    store.eventsByDay[key, default: []].append(event)
    // Delete idea from backend (server-side)
    try? await IdeaService.deleteIdea(tripId: store.tripId, ideaId: ideaId)
    store.ideas.removeAll { $0.id == ideaId }
}
```

If fix 5a is applied, this call becomes a no-op (idea already deleted), but it provides defense in depth.

---

## Files to Modify

| File | Issues |
|------|--------|
| `ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift` | 1, 2 |
| `ios/Roammate/Store/TripDetailStore.swift` | 3 |
| `ios/Roammate/Models/Event.swift` (`EventCreate`) | 4a |
| `ios/Roammate/Views/Trips/Plan/AddToTimelineSheet.swift` | 4b, 4c, 5b |
| `backend/app/api/endpoints/events.py` | 5a |
