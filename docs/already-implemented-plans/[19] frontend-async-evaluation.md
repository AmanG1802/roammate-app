# Async Evaluation: Frontend Data Loading

Audit of all async data-loading patterns across the Roammate frontend. The app is functionally correct but has several patterns causing UX degradation (content flashes, unnecessary latency) and correctness risks (race conditions, memory leaks on unmount).

---

## Issue 1 — IdeaBin extras split (High severity, Low effort)

**File:** `frontend/components/trip/IdeaBin.tsx:67`

`extras` (category, photo_url, rating, address, description) lives in local `useState`, which resets on every component mount. `ideas` (skeleton data) lives in Zustand and persists. On SPA navigation, cards render from Zustand immediately but `extras = {}` — enrichment fields only appear after the fetch resolves (~0.5s).

**Fix:** Merge extras fields into `IdeaBinItem` in Zustand. See `docs/idea-bin-state-enhancement.md` for full spec.

---

## Issue 2 — Sequential fetches in `refreshTripData()` (High severity, Low effort)

**File:** `frontend/app/trips/page.tsx:167-183`

Trip metadata, events, and trip days are fetched one after another. Total page load latency = sum of 3 round trips instead of the max of any one.

```ts
// Current: sequential
fetch(`${API}/trips/${tripId}`)...
loadTripDays(tripId, token);   // waits for above to finish? no, but fired after
loadEvents(tripId, token);
```

**Fix:** Use `Promise.all()`:
```ts
await Promise.all([
  fetch(`${API}/trips/${tripId}`).then(...),
  loadTripDays(tripId, token),
  loadEvents(tripId, token),
]);
```

Estimated savings: 100–300ms on initial Plan page load.

---

## Issue 3 — Sequential fetches on dashboard (High severity, Low effort)

**File:** `frontend/app/dashboard/page.tsx`

`fetchTrips()` and `fetchInvitations()` called sequentially in the same `useEffect`. They are fully independent.

**Fix:** `await Promise.all([fetchTrips(), fetchInvitations()])`

---

## Issue 4 — No AbortController on any fetch (Medium severity, High effort)

Every `fetch()` call in the app lacks an AbortController. When a component unmounts before a fetch resolves, the `.then()` callback calls `setState` on an unmounted component — a memory leak and React warning.

Affected sites:
- `IdeaBin.tsx` — `loadIdeas()` useEffect
- `Timeline.tsx` — `loadEvents()` useEffect  
- `store.ts` — `loadEvents()`, `loadTripDays()`, `moveIdeaToTimeline()`
- `dashboard/page.tsx` — `fetchTrips()`, `fetchInvitations()`
- `BrainstormChat.tsx` — message fetch, message POST
- `TodayWidget.tsx` — dashboard today fetch

**Fix pattern:**
```ts
useEffect(() => {
  const controller = new AbortController();
  fetch(url, { signal: controller.signal })
    .then(...)
    .catch((err) => { if (err.name !== 'AbortError') throw err; });
  return () => controller.abort();
}, [deps]);
```

For Zustand async actions (not in components), pass the signal through or accept that fire-and-forget store actions won't abort — but optimistic mutations (moveIdeaToTimeline, toggleEventSkip) are safe regardless.

---

## Issue 5 — Stale state flash on trip switch (Medium severity, Low effort)

**File:** `frontend/lib/store.ts` — `setActiveTrip()`, `events`, `ideas`, `tripDays`

When the user navigates to a different trip, Zustand retains the previous trip's `events`, `ideas`, and `tripDays` arrays until the new fetches resolve. Cards from the old trip are briefly visible.

**Fix:** Clear arrays in `setActiveTrip()`:
```ts
setActiveTrip: (tripId) => set({
  activeTrip: tripId,
  events: [],
  ideas: [],
  tripDays: [],
}),
```

Or: add an `isLoadingTrip` flag and render a skeleton while it's true.

---

## Issue 6 — Token read from localStorage on every callback (Low severity, Medium effort)

**Affected:** 10+ locations including `IdeaBin.tsx:96`, `Timeline.tsx:283`, `trips/page.tsx:71`, `dashboard/page.tsx:121`, `BrainstormChat.tsx` via `authHeaders()`

`localStorage.getItem('token')` is a synchronous read called inside every fetch callback. Not a correctness problem, but unnecessary on every call.

**Fix:** Store the token in Zustand auth state (`useAuthStore`) on login and read it once per action. This also enables reactive logout (clearing the token from Zustand automatically cancels auth-gated operations).

---

## Issue 7 — No loading skeletons on Timeline and IdeaBin (Medium severity, Medium effort)

Timeline and IdeaBin render empty (or stale from Zustand) while their fetches are in flight. Dashboard has a spinner for trips and invitations; these components do not.

**Fix:** Track a `isLoadingIdeas` / `isLoadingEvents` boolean in Zustand or local state. Show 3–4 skeleton cards during the first load when the array is empty.

---

## Issue 8 — Race condition on BrainstormChat rapid sends (Low severity, Medium effort)

**File:** `frontend/components/trip/BrainstormChat.tsx`

No debounce or request queuing on the message POST. Rapid sends produce concurrent requests; responses arrive out of order and can overwrite each other's state.

**Fix:** Disable the send button while `sending === true` (appears to already be partially done) and ensure the POST is strictly sequential by awaiting the previous one before allowing a new send.

---

## Issue 9 — DOM CustomEvent coordination for IdeaBin refresh (Low severity, Low effort)

**File:** `frontend/lib/store.ts:348`, `frontend/components/trip/IdeaBin.tsx:145-149`

`moveEventToIdea()` dispatches a DOM `CustomEvent('idea-bin:refresh')` to trigger a reload in IdeaBin. The listener has no debounce — if multiple events fire rapidly (e.g. moving several events at once), concurrent fetches will race.

**Fix:** Replace the event-based pattern with a Zustand `ideasLastUpdated: number` timestamp. IdeaBin's useEffect depends on it and re-fetches when it changes. Debounce naturally handled by React's batched state updates.

---

## Issue 10 — BrainstormChat full history re-fetch per message (Low severity, Medium effort)

**File:** `frontend/components/trip/BrainstormChat.tsx`

After each message POST, the component re-fetches the entire message history from the server. For long sessions this grows linearly.

**Fix:** The POST response should return the new assistant message. Append it to the local messages array instead of re-fetching all history.

---

## Priority Matrix

| Issue | Severity | Effort | Recommended Action |
|-------|----------|--------|--------------------|
| IdeaBin extras split | High | Low | Fix now (see idea-bin-state-enhancement.md) |
| Sequential refreshTripData | High | Low | Fix now |
| Sequential dashboard fetches | High | Low | Fix now |
| Stale state on trip switch | Medium | Low | Fix now |
| No loading skeletons | Medium | Medium | Next sprint |
| No AbortController | Medium | High | Future sprint |
| Token localStorage reads | Low | Medium | Auth refactor sprint |
| BrainstormChat rapid send | Low | Medium | Next sprint |
| idea-bin:refresh race | Low | Low | Fix with IdeaBin enhancement |
| BrainstormChat history re-fetch | Low | Medium | Next sprint |
