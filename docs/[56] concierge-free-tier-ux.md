# [56] Concierge — Free-tier UX, Date-gating Removal, Enrichment Fix, Web Parity

## Context

This plan bundles four related improvements to the Concierge feature:

1. **Free-tier UX** — Replace the "Concierge actions need Roammate Plus" banner with a
   full-width gradient pill button. Free-tier users can read the chat but can't post.
2. **Date-gating removal** — Concierge should be usable anytime by Plus subscribers.
   Remove all date-range banners. Chips are hidden pre-trip (contextually meaningless)
   but intent validation moves to the backend via an explicit whitelist.
3. **`add_event` enrichment fix** — Events added via Concierge land without coordinates,
   making them invisible to route rendering. Fix: run `enrich_item()` on params during
   the dry-run phase (before the action card is shown to the user).
4. **Sender avatars** — Every bubble gets an avatar corner icon (sparkle circle for AI,
   user photo/initials for humans) on both iOS and Web.
5. **Web parity** — All of the above mirrored to `ConciergeChatDrawer.tsx`.

---

## Changes

### A. Backend — `concierge_executor.py`

#### A1. Intent whitelist (three tiers)

Add three `frozenset` class-level constants to `ConciergeExecutor` (top of class body):

```python
# Pure conversation and read-only explanation — no trip-date restriction.
ANYTIME_INTENTS: frozenset[ConciergeIntent] = frozenset({
    ConciergeIntent.chat_only,
    ConciergeIntent.explain_plan,
})

# Schedule mutations valid for trip planning (pre-trip) and live editing (during trip).
# Not meaningful post-trip.
PLANNING_INTENTS: frozenset[ConciergeIntent] = frozenset({
    ConciergeIntent.add_event,
    ConciergeIntent.move_event,
})

# Real-time, trip-in-progress-only actions — only available while today is
# between trip.start_date and trip.end_date (inclusive).
ACTIVE_TRIP_ONLY_INTENTS: frozenset[ConciergeIntent] = frozenset({
    ConciergeIntent.shift_timeline,
    ConciergeIntent.skip_event,
    ConciergeIntent.find_nearby,
})
```

In the intent validation path (wherever the executor checks the intent before running
`_dry_run`/`_execute`), add a guard:

```python
today = today_in_tz(trip.timezone)  # already available in executor context
if intent in self.ACTIVE_TRIP_ONLY_INTENTS:
    if not (trip.start_date <= today <= trip.end_date):
        return {
            "success": False,
            "message": "That action is only available while the trip is running.",
        }
```

#### A2. `add_event` enrichment at dry-run time

In `_add()` (lines ~331–404), immediately after parsing params but **before**
creating the `EventModel`:

```python
# Enrich with Maps data so the new event is route-eligible from the start.
# Uses trip destination as the location bias for find_place.
loc = LocationContext(lat=trip.lat, lng=trip.lng) if (trip.lat and trip.lng) else None
params = await maps_service.enrich_item(
    dict(params), client=client, location=loc
)
```

`enrich_item()` is idempotent — skips if `place_id` already present. It calls
`find_place(title, location=loc)` → `place_details(pid)` → merges `lat`, `lng`,
`place_id`, `address`, `photo_url`, `rating`, `price_level`, `types` into the params
dict. The enriched dict is then used to construct `EventModel`, so the committed event
carries full Maps data.

Because enrichment happens at dry-run (the LLM dispatch step before the action card is
shown), the preview already displays the real address and location, and the event is
route-eligible immediately after the user confirms.

**Files**: `backend/app/services/concierge_executor.py`, `backend/app/services/maps/base.py`

---

### B. iOS — `TripConciergeView.swift`

#### B1. Remove availability banners entirely

Delete `private var plusBanner` and `private func availabilityBanner`.
Remove all usages in `chat`:
- `if let banner = store.availabilityBanner { availabilityBanner(banner) }`
- `if store.canWrite && !canUseConcierge { plusBanner }`

#### B2. Refactor `chat` footer — three-way branch

```swift
private var chat: some View {
    VStack(spacing: 0) {
        messageList
        if store.canWrite {
            if tripHasStarted { chipRow }
            inputBar.tutorialAnchor("concierge-input")
        } else if isAdmin && !canUseConcierge {
            unlockConciergeButton           // free-tier admin
        } else {
            readOnlyComposer                // non-admin member
        }
    }
}
```

`tripHasStarted` (new computed property):

```swift
private var tripHasStarted: Bool {
    let today = store.todayString          // already tz-aware yyyy-MM-dd
    return today >= trip.startDate         // string compare is safe for ISO dates
}
```

Note: `trip.startDate` should already be `yyyy-MM-dd` format. Verify the `Trip` model
field name; `trip.startDate` may be `trip.start_date` — match whatever field exists.

#### B3. `unlockConciergeButton` (full-width pill)

```swift
private var unlockConciergeButton: some View {
    Button {
        HapticManager.light()
        postNeedsPlus()
    } label: {
        HStack(spacing: 8) {
            Image(systemName: "sparkles").font(.system(size: 13, weight: .bold))
            Text("Unlock Concierge")
                .font(.system(.body, design: .rounded, weight: .heavy))
        }
        .foregroundStyle(.white)
        .frame(maxWidth: .infinity)
        .padding(.vertical, 14)
        .background(RoammateGradient.plus, in: Capsule())
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, RoammateSpacing.sm)
    }
    .buttonStyle(.plain)
    .background(Color.roammateSurface.shadow(.drop(color: .black.opacity(0.06), radius: 8, y: -4)))
}
```

#### B4. Simplify `readOnlyComposer`

Strip it to the non-admin read-only state only (remove the admin+no-Plus branch, which
is now handled by `unlockConciergeButton`):

```swift
private var readOnlyComposer: some View {
    HStack(spacing: 8) {
        Image(systemName: "eye").font(.system(size: 13, weight: .bold))
        Text("Trip admins run the Concierge — you can follow along here")
            .font(.system(.caption, design: .rounded, weight: .heavy))
            .multilineTextAlignment(.leading)
        Spacer(minLength: 0)
    }
    .foregroundStyle(Color.roammateMuted)
    .padding(.horizontal, RoammateSpacing.md).padding(.vertical, 12)
    .background(Color.roammateSurface)
}
```

#### B5. Remove `isLiveDay` from chip/button guards

Currently `chip(...)` and the "Running late" Menu are disabled with `!store.isLiveDay`.
Remove those guards. Backend's intent whitelist now enforces `ACTIVE_TRIP_ONLY_INTENTS`
at the API level and returns a friendly message if the trip is not active.

#### B6. Remove `availabilityBanner` and `isLiveDay` from `ConciergeStore.swift`

Delete the `availabilityBanner` computed property (~lines 345–359) and `isLiveDay`
computed property (~line 361) from `ConciergeStore`.

---

### C. iOS — `ConciergeCards.swift` (sender avatars)

#### C1. `ConciergeMessageView` — resolve avatar URL

Add `@EnvironmentObject var detailStore: TripDetailStore`.

```swift
private var resolvedAvatarUrl: String? {
    guard let authorId = message.authorId else { return nil }
    return detailStore.members.first(where: { $0.userId == authorId })?.user.avatarUrl
}
```

In the `.text` case dispatch, pass it down:

```swift
case .text:
    ConciergeBubble(
        role: message.role,
        text: message.text,
        avatarUrl: resolvedAvatarUrl
    )
```

Remove `authorName` pass-through to `ConciergeBubble` — the text label is replaced by
the avatar icon.

Inject `detailStore` at the call site in `TripConciergeView.swift`:

```swift
ConciergeMessageView(message: message)
    .environmentObject(store)
    .environmentObject(detailStore)     // ADD
    .id(message.id)
```

#### C2. `ConciergeBubble` — corner avatar overlay

Add `var avatarUrl: String? = nil` parameter. Remove the `authorName` label (lines
~62–67) — attribution is now the avatar.

On the `Text(conciergeMarkdown(text))` bubble, add `.padding(.bottom, 11)` and an
`.overlay(alignment:)` for the avatar:

- **AI (`.assistant`)** → `.overlay(alignment: .bottomLeading)`:
  ```swift
  ZStack {
      Circle().fill(RoammateGradient.plus).frame(width: 22, height: 22)
      Image(systemName: "sparkles")
          .font(.system(size: 9, weight: .bold)).foregroundStyle(.white)
  }
  .offset(x: -6, y: 6)
  ```

- **User (`.user`)** → `.overlay(alignment: .bottomTrailing)`:
  ```swift
  ConciergeUserAvatar(avatarUrl: avatarUrl)
      .offset(x: 6, y: 6)
  ```

#### C3. `ConciergeUserAvatar` helper (new struct in `ConciergeCards.swift`)

```swift
struct ConciergeUserAvatar: View {
    var authorName: String?
    var avatarUrl: String?

    var body: some View {
        if avatarUrl != nil || (authorName?.isEmpty == false) {
            AvatarCircle(name: authorName ?? "", avatarUrl: avatarUrl, size: 22)
        } else {
            ZStack {
                Circle().fill(Color.roammateIndigoTint).frame(width: 22, height: 22)
                Image(systemName: "person.fill")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(Color.roammateIndigo)
            }
        }
    }
}
```

#### C4. Long-press to copy

Add `.contextMenu` to the `Text(conciergeMarkdown(text))` in `ConciergeBubble`
(assistant and user roles only):

```swift
.contextMenu {
    Button {
        UIPasteboard.general.string = text
    } label: {
        Label("Copy", systemImage: "doc.on.doc")
    }
}
```

---

### D. Web — `ConciergeChatDrawer.tsx`

#### D1. Replace `!canWrite` follow-along box with gradient pill

Find the current `!canWrite` branch (lines ~723–761) that shows a plain grey box.
Replace it with a gradient pill CTA:

```tsx
{!canWrite ? (
  <div className="px-4 pb-4 pt-2">
    <button
      onClick={() => requirePlus('concierge')}
      className="w-full py-3.5 rounded-full text-white font-black text-sm
                 bg-gradient-to-r from-violet-600 to-orange-400
                 flex items-center justify-center gap-2 shadow-sm"
    >
      <Sparkles className="w-4 h-4" />
      Unlock Concierge
    </button>
  </div>
) : (
  {/* existing chip row + textarea + send */}
)}
```

Match the gradient to `RoammateGradient.plus` colours (violet → orange).

Also hide the chips row from within the `canWrite` branch when trip hasn't started
(equivalent to iOS `tripHasStarted`):

```tsx
{canWrite && tripHasStarted && (
  <div className="px-4 py-2 border-t border-slate-50 overflow-x-auto flex gap-2">
    {/* existing chips */}
  </div>
)}
```

Where `tripHasStarted = today >= trip.startDate` (ISO string comparison, same logic
as iOS).

#### D2. Remove "Concierge activates on [Date]" banner

In `trips/page.tsx` (lines ~605–611), delete the `{!isCurrentDay && liveDay && ...}`
banner block entirely. Do not replace it with anything.

#### D3. Avatar circles on web message bubbles

In `ConciergeChatDrawer.tsx`, find the `MessageBubble` component (lines ~854+).

For **AI messages** (assistant role), add a 22 px sparkle gradient circle overlaid at
the bottom-left corner of the bubble div (use `absolute bottom-0 left-0 -translate-x-1/3 translate-y-1/3`):

```tsx
<div className="relative inline-block">
  {/* existing bubble content */}
  <div className="absolute bottom-0 left-0 -translate-x-1/3 translate-y-1/3
                  w-5 h-5 rounded-full flex items-center justify-center
                  bg-gradient-to-br from-violet-600 to-orange-400 shadow-sm">
    <Sparkles className="w-2.5 h-2.5 text-white" />
  </div>
</div>
```

For **user messages**, add a 22 px avatar circle at bottom-right. Resolve avatar from
the trip member list using `msg.authorId`. Use a component analogous to `AvatarCircle`:
photo if available, initials if name exists, `User` icon fallback.

Remove the existing `{msg.authorName && <span ...>}` text label above user bubbles —
the avatar corner replaces it.

---

## Key files

| File | Change |
|---|---|
| `backend/app/services/concierge_executor.py` | Intent whitelist constants; enrich_item call in `_add()` |
| `ios/Roammate/Store/ConciergeStore.swift` | Remove `availabilityBanner`, `isLiveDay` |
| `ios/Roammate/Views/Trips/SubPages/TripConciergeView.swift` | Remove banners; pill button; `tripHasStarted` chip gate; remove `isLiveDay` guards |
| `ios/Roammate/Views/Trips/SubPages/Concierge/ConciergeCards.swift` | Avatar overlay; `ConciergeUserAvatar`; contextMenu copy; remove authorName label |
| `frontend/components/trip/ConciergeChatDrawer.tsx` | Pill button; avatar circles; pre-trip chip hide |
| `frontend/components/trip/ConciergeActionBar.tsx` | Gate "Running Late"; disable Running Late + Skip Next + Find Coffee outside tripIsActive |
| `frontend/app/(authenticated)/trips/page.tsx` | Remove "Concierge activates" banner; remove `isCurrentDay` from action bar render guard |

#### D4. `ConciergeActionBar.tsx` — subscription gate + date-aware button state

Two bugs and one gating change:

**Bug 1 — "Running Late" is not subscription-gated.** `handleRunningLate` calls the
ripple API directly without going through `gateConcierge`. Free-tier users can tap it
and shift their timeline today. Fix: wrap the menu item `onClick` with `gateConcierge`:

```tsx
// Before (ungated):
onClick={() => handleRunningLate(min)

// After:
onClick={() => gateConcierge(() => handleRunningLate(min))}
```

**Bug 2 — Action bar visibility is tied to `isCurrentDay`.** In `trips/page.tsx`
(lines ~602–604) the action bar only renders when `isCurrentDay && currentUserIsAdmin`.
With date gating removed, the action bar should render whenever `currentUserIsAdmin`
(or even always, since the "Unlock Concierge" CTA is useful to all admins regardless
of day). Remove the `isCurrentDay` condition from the render guard.

**Date-aware disable for ACTIVE_TRIP_ONLY buttons.** "Running Late" (`shift_timeline`),
"Skip Next" (`skip_event`), and "Find Coffee" (`find_nearby`) are all `ACTIVE_TRIP_ONLY`
intents — disable all three outside the active trip window:

```tsx
const tripIsActive = tripStartDate && tripEndDate
  ? (today >= tripStartDate && today <= tripEndDate)
  : false;

// "Running Late" menu items:
disabled={isProcessing || events.length === 0 || !tripIsActive}

// "Skip Next" button:
disabled={!tripIsActive || !events.some(...)}

// "Find Coffee" button:
disabled={!tripIsActive || isProcessing}
```

"Chat Now / Unlock Concierge" remains always available (ANYTIME / paywall CTA).

**Files**: `frontend/components/trip/ConciergeActionBar.tsx`,
`frontend/app/(authenticated)/trips/page.tsx`

---

## Future Scope

### Cross-day event move

**Today**: `move_event` is same-day only. When a user asks to move an event to a
different day, the executor (`concierge_executor.py` ~lines 274–286) returns a friendly
refusal: *"Cross-day moves aren't supported via chat yet — drag the event to the new day
from the timeline."* Same-day time changes (`move_event` with `new_start_time: "HH:MM"`)
work correctly.

**What's needed to support it**: Two viable approaches —

- **Extend `move_event`**: Add an optional `new_day_date: str` param to the existing
  intent. If present and different from the event's `day_date`, the executor updates
  `day_date`, validates the target `TripDay` belongs to the trip, then re-runs Smart
  Ripple on *both* the source day (backfill the vacated gap) and the target day (make
  room at the insertion point). The LLM prompt needs an updated example showing
  `new_day_date`.

- **New `move_event_day` intent**: Cleaner routing logic — keeps same-day time
  adjustments and cross-day relocations in separate executor paths. Costs a new intent
  enum value and prompt entry.

Either way requires: executor path, updated prompt, iOS/web model update, and ripple
recalculation across two days.

---

## Verification

1. **Free-tier admin (iOS + Web)**: Open Concierge → no banner → pill button in footer → no chips → messages readable. Tap pill → paywall opens.
2. **Plus admin (iOS + Web)**: Full chips + input. Pre-trip: no chips, input only. During trip: all chips + input.
3. **Non-admin (iOS + Web)**: Read-only footer, no pill.
4. **ACTIVE_TRIP_ONLY gate**: Send "I'm running late" before trip starts → backend returns "That action is only available while the trip is running." (graceful message, no 4xx).
5. **add_event enrichment**: Say "Add a coffee stop at 10am tomorrow" → action card preview shows real address/place. After confirm, event appears in route on "Refresh Route".
6. **Avatars**: AI bubbles show sparkle gradient circle bottom-left; user bubbles show photo/initials/person icon bottom-right. Long-press any text bubble → Copy context menu.
7. **No banners**: Open Concierge before/after trip dates → no banner appears anywhere.
