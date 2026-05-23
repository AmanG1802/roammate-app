# Offline-First Sync Strategy — iOS + Web + Backend

## Context

Roammate's backend lives on Railway. The iOS app and the Next.js web app are pure clients — without internet they can do nothing today. Travelers (our core user) regularly lose connectivity (planes, foreign SIMs, subways, mountains, remote hotels). We need the app to keep working when the network drops, both for reading and editing.

This document defines a two-tier rollout:

- **Tier 1 — Read-while-offline.** Aggressive caching so users can *view* trips, days, events, idea bin, routes, and notifications without a connection. No write support.
- **Tier 2 — Edit-while-offline.** A durable mutation queue per client that drains to the backend when connectivity returns, plus the server-side primitives needed to handle concurrent edits from multiple trip members.

The server-side conflict-resolution design has to land before Tier 2 ships, because the backend currently has no `updated_at`, no version columns, no soft-delete, and no change feed.

---

## Current State (from exploration)

### iOS
- `ios/Roammate/Utils/DiskCache.swift` — JSON-on-disk cache, no TTL, stale-while-revalidate. Already used by `TripStore`, `TripDetailStore`, `GroupStore`, `NotificationStore`. Wiped on logout via `AuthManager`.
- `ios/Roammate/Network/APIClient.swift` — single client, JWT from Keychain, 401 refresh, network-error retry. **No `NWPathMonitor`, no offline queue.**
- Service enums (`TripService`, `EventService`, `IdeaService`, `TripDayService`, `VoteService`, `MemberService`, `NotificationService`, `GroupService`, `RouteService`) wrap mutations.
- Models (`Trip`, `TripDay`, `Event`, `IdeaBinItem`) carry **no `updated_at`/`version`/`etag`**.

### Web (Next.js)
- `frontend/lib/store.ts` — single Zustand store, **in-memory only**, no `persist` middleware.
- `frontend/lib/auth.ts` — token in localStorage; canonical session is the `rm_access` cookie.
- `frontend/lib/api.ts` — fetch wrapper, 401 refresh.
- **Dexie is in `package.json` but never imported.** Dead dependency.
- **TanStack Query is installed but no `QueryClient` exists.** Dead dependency.
- No service worker, no PWA manifest.
- Mutations are direct `fetch` calls inside store actions with optimistic updates and revert-on-failure (no queue).

### Backend (FastAPI)
- `backend/app/models/all_models.py` — `Trip` has `created_at` only; `TimelineItem`/`IdeaBinItem`/`TripDay` have no timestamps and no version column.
- `backend/app/api/endpoints/{trips,events,ideas,votes}.py` — last-write-wins on every PATCH/DELETE. Only conflict check is `_has_conflict` in `maps.py` for itinerary time overlap (validation, not multi-writer sync).
- `IdeaVote`/`EventVote` are upserts keyed by `(item_id, user_id)` — already idempotent and offline-safe.
- `notification_service.emit()` writes rows; **no WebSocket / SSE / Redis pubsub**. Clients poll.
- `DayRoute.waypoint_fingerprint` already used to detect stale routes — pattern worth reusing.

---

## Server-Side Foundation (prerequisite for Tier 2)

Before any client queue can sync safely, the backend needs four small but load-bearing changes. These are additive and backwards-compatible.

### 1. Add `updated_at` + `version` + `deleted_at` to mutable entities

Apply to `Trip`, `TripDay`, `TimelineItem`, `IdeaBinItem` (and on `BrainstormBinItem` for completeness):

```python
updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
version    = Column(Integer, nullable=False, server_default="1")  # bumped in service layer on every PATCH
deleted_at = Column(DateTime(timezone=True), nullable=True)        # soft delete
```

- `version` is incremented in the service-layer update (not just by trigger) so we can return `409 Conflict` on `If-Match` mismatch.
- `deleted_at` lets the delta sync endpoint surface tombstones (otherwise an offline client never learns about a delete done by another user).
- One Alembic migration; backfill `updated_at = created_at` where possible, else `now()`.

Files to touch: `backend/app/models/all_models.py`, plus a new migration under `backend/alembic/versions/`.

### 2. Optimistic concurrency on PATCH/DELETE

Each PATCH/DELETE on `Trip`, `TimelineItem`, `IdeaBinItem`, `TripDay` accepts an `If-Match: <version>` header (or `expected_version` body field for clients that can't set headers easily).

- Match → apply, bump `version`, set `updated_at`, return new entity with new version.
- Mismatch → `409 Conflict` with the server's current entity in the body so the client can run a merge.

Service helpers go in `backend/app/services/` (new `concurrency.py` with `apply_with_version()` decorator/util).

### 3. Delta-sync endpoint per trip

New endpoint: `GET /trips/{trip_id}/sync?since=<ISO ts>&cursor=<opaque>`

Response:
```json
{
  "server_time": "2026-05-22T12:34:56Z",
  "next_cursor": null,
  "trip":     { ...latest..., "version": 14 },
  "days":     [ { ... } ],
  "events":   [ { ..., "deleted_at": null }, { ..., "deleted_at": "2026-..." } ],
  "ideas":    [ ... ],
  "members":  [ ... ]
}
```

- Returns only rows where `updated_at > since` (including tombstones via `deleted_at`).
- Cursor-based for trips with very large deltas (pagination).
- Used by both clients on app-foreground and on reconnect.

### 4. Idempotency keys on POST (create)

Creates can't use `If-Match`. Instead accept an optional header `Idempotency-Key: <client-uuid>` on `POST /events/`, `POST /trips/{id}/days`, `POST /trips/{id}/ingest`, `POST /trips/`.

- Store the key in a new `idempotency_keys` table (key, user_id, endpoint, response_body, created_at) with a 24h TTL.
- On replay (queue retry), return the cached response instead of creating duplicates.
- Cleanup job (Celery if/when introduced, or a simple cron endpoint) sweeps expired keys.

### 5. Conflict-resolution rules (per entity)

| Entity            | Strategy                                                                                                                          |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `Trip` metadata   | If-Match required. On 409, server wins; client shows toast "Trip was updated by <member>" and refetches.                          |
| `TripDay`         | If-Match required. Adds are idempotency-keyed. Deletes return tombstone.                                                          |
| `TimelineItem`    | **Field-level last-write-wins** with `version` gate. Server merges per-field: e.g. if client only changed `start_time` and server only changed `title`, both apply and version bumps. If both touched the same field → 409, return server entity, client surfaces conflict UI. |
| `IdeaBinItem`     | Same field-level merge as events.                                                                                                  |
| `EventVote` / `IdeaVote` | Upsert by `(item_id, user_id)`. Already conflict-free — no version check needed. Safe to drain freely from the queue.       |
| `sort_order` reorders | Special-case: client sends the full ordered list of event IDs for a day. Server replaces atomically. Last writer wins on order — acceptable since reorder is a low-stakes UX action. |
| Smart Ripple      | Admin-only, online-only. Don't queue these — refuse the action while offline.                                                      |

Field-level merge lives in `backend/app/services/event_service.py` and `idea_service.py` (new helpers).

### 6. (Optional, defer) Live push

Polling `/trips/{id}/sync` on app-foreground is enough for v1. WebSockets/SSE can come later — the data model above is push-ready (just stream `updated_at`-ordered rows).

---

## Tier 1 — Read-While-Offline

### iOS (Tier 1)

Most of the scaffolding already exists in `DiskCache`. Gaps to fill:

1. **Add `NWPathMonitor` wrapper** at `ios/Roammate/Network/Reachability.swift`:
   - `@Published var isOnline: Bool`
   - Injected into stores so views can render an "offline" pill.
2. **Pin the active trip's full graph.** When user opens a trip, cache:
   - Days, events, idea bin, members (already cached).
   - **Add: route polylines** (`legsByDay` analog) — currently fetched live from `RouteService`. Cache to `trip_{id}_routes`.
   - **Add: place enrichment thumbnails** — store photo URLs and let `URLCache.shared` (configure a 200 MB disk cap in `RoammateApp.swift`) hold the bytes.
3. **Cache versioning.** Each cached payload becomes `{ version, server_time, payload }` so Tier 2 can use `server_time` as the `since=` value for delta sync.
4. **TTL guidance, not enforcement.** Show a "Last synced: 2h ago" footer rather than forcing a refresh.
5. **Graceful failure in services.** `TripService.fetch*` and friends already swallow errors; ensure they fall back to the disk cache and don't clear the in-memory store on network error.

Files: `Utils/DiskCache.swift` (no API change), `Network/APIClient.swift` (add reachability hook), `Network/Reachability.swift` (new), every `Store` (consume reachability, expand cached keys to include routes).

### Web (Tier 1)

The web is starting from zero — no persistence, no Dexie usage, no PWA. The cheapest correct option:

1. **Wire up TanStack Query** (already installed). `frontend/lib/queryClient.ts`:
   - `staleTime: 5 * 60_000`, `gcTime: 24 * 60 * 60_000`.
   - Mount `QueryClientProvider` in `frontend/app/layout.tsx`.
2. **Add `@tanstack/query-sync-storage-persister` + `persistQueryClient`** backed by `localStorage` (or IndexedDB via `idb-keyval` if payload size grows past ~5 MB).
   - Persist only trip/day/event/idea queries — exclude auth, exclude routes initially.
3. **Migrate read paths in `lib/store.ts`** from raw `fetch` to `useQuery`. Zustand stays for UI state; server state moves to React Query. This deletes a lot of code rather than adding it.
4. **Online/offline indicator:** `navigator.onLine` + `online`/`offline` window events → small banner in the trip layout.
5. **Drop Dexie from `package.json`** — it's a dead dep adding 100KB to the install graph. (Confirm with Aman first.)
6. **Skip the service worker for v1.** A PWA-grade offline experience is a separate, larger project; query-persister gets us 90% of the read benefit at 5% of the work.

Files: `frontend/lib/queryClient.ts` (new), `frontend/app/layout.tsx`, `frontend/lib/store.ts` (strip server-state methods), new `frontend/lib/hooks/useTrip.ts` etc.

---

## Tier 2 — Edit-While-Offline

Lands only after the server foundation above is in place.

### Shared mental model (both clients)

A **mutation envelope**:

```ts
{
  id: string;              // client-side uuid; doubles as Idempotency-Key
  entity: "event" | "idea" | "trip" | "day" | "vote";
  op: "create" | "update" | "delete" | "reorder";
  target_id?: string;      // server id; absent for create
  payload: object;         // diff or full create body
  base_version?: number;   // for updates → sent as If-Match
  created_at: timestamp;
  trip_id: string;
  attempts: number;
  last_error?: string;
}
```

A **sync coordinator** with these states: `idle → draining → conflicted → idle`. Drains queue FIFO **per trip**. A 409 on an update pauses that envelope, runs a field-level merge against the latest server entity, and either auto-resolves (no field overlap) or surfaces a conflict prompt.

Optimistic local apply happens immediately on enqueue. If the envelope ultimately fails after a merge attempt, the local state is reconciled with the server response.

### iOS (Tier 2)

1. **Queue storage:** SwiftData (iOS 17+) or a single Codable array persisted via DiskCache under key `mutation_queue`. SwiftData is cleaner but DiskCache works fine and avoids a new dependency.
2. **`SyncCoordinator` actor** at `ios/Roammate/Sync/SyncCoordinator.swift`:
   - Observes `Reachability.isOnline`.
   - On `online → true`, drains the queue.
   - Per envelope: calls the right `*Service` method with `If-Match: base_version` / `Idempotency-Key: id` headers.
   - On `409`: fetches the server entity, runs merge (`SyncMerger.swift`), re-enqueues a new envelope with the merged diff and updated `base_version`. If fields overlap, pushes a `ConflictItem` into a `@Published` array consumed by a banner UI.
3. **APIClient changes:** accept optional `If-Match` and `Idempotency-Key` headers per request.
4. **Optimistic apply:** every store mutation method first writes to the in-memory + disk cache, then enqueues the envelope.
5. **Foreground delta sync:** on app foreground and on trip open, call `GET /trips/{id}/sync?since=<server_time of last sync>`; apply tombstones (`deleted_at`) by removing locally; bump cached versions; then drain queue.
6. **UI:** small "X changes queued" indicator in the trip header; conflict resolution sheet that shows "Your change → Their change" and lets the user pick.

Files: `ios/Roammate/Sync/SyncCoordinator.swift` (new), `ios/Roammate/Sync/MutationEnvelope.swift` (new), `ios/Roammate/Sync/SyncMerger.swift` (new), every mutation site in stores (route through coordinator), `APIClient.swift` (headers).

### Web (Tier 2)

1. **Queue storage:** IndexedDB via `idb-keyval` (light, no Dexie revival needed) — or honestly, this is the one place where Dexie's table model earns its keep. Given Dexie is already in `package.json`, **wake it up** for the queue only (one table: `mutations`). This costs nothing extra and gives proper indexing.
2. **`SyncCoordinator` module** at `frontend/lib/sync/coordinator.ts`:
   - Listens to `online`/`offline` events and to React Query's `onlineManager`.
   - On reconnect, drains the queue against the API client.
   - Same 409-merge logic as iOS.
3. **React Query integration:**
   - Wrap mutating actions in `useMutation` with `onMutate` (optimistic update) → `onError` (revert if not network-related) → `onSuccess` (invalidate).
   - If `navigator.onLine === false`, the mutation is enqueued instead of fired, and the optimistic state stays.
4. **API client:** add `If-Match` and `Idempotency-Key` header support in `frontend/lib/api.ts`.
5. **Foreground delta sync:** on `visibilitychange === "visible"` and on route entry to `/trips/[id]`, hit `/sync?since=...`, apply tombstones via `queryClient.setQueryData`, drain queue.
6. **UI:** Same "X queued" pill, same conflict resolution modal.

Files: `frontend/lib/sync/coordinator.ts` (new), `frontend/lib/sync/db.ts` (new — Dexie schema), `frontend/lib/sync/merger.ts` (new), `frontend/lib/api.ts` (headers), mutating hooks (`useUpdateEvent`, etc.).

### Things we explicitly do NOT queue
- Smart Ripple Engine (admin-only, has side-effects across the trip)
- Trip member invites/removal (auth-sensitive, needs round-trip)
- Auth flows (login, refresh, OAuth)
- Maps enrichment (`POST /trips/enrich`) — degrade gracefully to "Enrichment pending" UI when offline

---

## Rollout Sequence

1. **Backend foundation:** add `updated_at`/`version`/`deleted_at` + migration + service helpers (1 PR).
2. **`/sync` endpoint + idempotency table** (1 PR).
3. **Tier 1 iOS:** reachability + route cache + cache versioning (1 PR).
4. **Tier 1 Web:** TanStack Query + persister + migrate store read paths (1 PR — can run in parallel with #3).
5. **Tier 2 iOS:** queue + coordinator + merger + conflict UI (1 PR).
6. **Tier 2 Web:** queue (Dexie) + coordinator + merger + conflict UI (1 PR — parallel with #5).
7. (Later) WebSocket/SSE push, full PWA service worker, CRDT exploration if true co-editing becomes a goal.

---

## Verification

**Backend**
- Unit tests for `apply_with_version()`: hit/miss, 409 shape.
- `pytest backend/tests/test_event_service.py` — extend with field-level merge cases.
- `/sync` integration test: create/update/delete a mix of entities, ask for `since=<ts>` and assert response includes the right rows + tombstones.
- Idempotency: same `Idempotency-Key` twice → same response, one DB row.

**iOS**
- Toggle airplane mode mid-edit: edit an event title → reopen → edit again → restore network → confirm one envelope drains and server reflects final state.
- Two-device test: edit same event from two phones offline → bring both online → confirm conflict UI on second drain.
- Cold start offline: should render last cached trip fully (days, events, ideas, routes).

**Web**
- Chrome DevTools → Network → Offline. Edit event → reload tab → state persists → go online → queue drains, server updated.
- Multi-tab test: same user, two tabs, both offline, both edit. On reconnect, the second tab to drain should hit 409 and reconcile.

**Cross-client**
- iOS offline edits + Web online edits on the same trip → reconnect iOS → verify field-level merge keeps non-conflicting changes from both sides, surfaces only overlapping fields as conflicts.

---

## Open Questions (to confirm before kickoff)

1. Are we okay introducing Alembic migrations for `updated_at`/`version`/`deleted_at` on the four mutable entities? (Affects every existing trip in prod.)
2. Tier 2 conflict UI — do we want a blocking sheet, or a non-blocking banner with "Review conflicts" that the user can defer?
3. Web: wake Dexie up for the mutation queue, or use `idb-keyval`? (Recommend Dexie since it's already installed.)
4. iOS: SwiftData for the queue, or extend DiskCache? (Recommend DiskCache to avoid the iOS 17 floor and keep the surface area small.)
