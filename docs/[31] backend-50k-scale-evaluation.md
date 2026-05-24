# Backend Scale Evaluation — 50k Users

**Date:** 2026-05-22
**Scope:** Async patterns, function design, DB CRUD — Roammate FastAPI backend
**Reference (stale, last week):** `docs/[20] async-evaluation-backend.md`

---

## Context

Roammate has matured from a prototype into a multi-surface product (iOS + Web) backed by a single FastAPI service. The async architecture, DB schema, and LLM/Maps integration were built for tens-of-users correctness, not thousands of concurrent users. This document re-evaluates the backend assuming **50k total users / ~7–10k DAU / 500–1500 concurrent peak**, identifies the failure modes that emerge at that scale, and lays out a prioritized enhancement plan.

The 50k benchmark is not arbitrary: at this size, single-process state (in-memory caches, circuit breakers, fire-and-forget tasks) stops being "good enough" and connection-pool defaults, N+1 queries, and synchronous LLM endpoints become user-visible failures.

---

## Executive Summary

The backend is **architecturally sound** (async-first, AsyncSession, AsyncClient, async LLM SDKs, bounded concurrency for Maps). The issues are concentrated in three layers:

1. **Process-local state that should be shared** — caches, circuit breakers, rate limits, fire-and-forget trackers. Multi-replica deployment multiplies API costs and weakens protection.
2. **Synchronous request lifetime for slow operations** — LLM endpoints (5–40s), trip cascade deletes, webhook handlers each hold a pooled DB connection (and socket) for the full duration. At 1k concurrent users this exhausts the connection pool and is the dominant latency source. (Note: with async handlers the *worker* is not pinned during the `await` — the held resource is the connection, not a worker slot. See A4.)
3. **DB ergonomics built for small trips** — unbounded list endpoints, N+1 vote/actor/group queries, default pool size, full-table dedup scans. Each is a future timeout.

The roadmap below is ordered by **risk-adjusted impact** — the work that prevents an outage or hard-failure mode comes before latency polish.

---

## Section 1 — Async & Concurrency Issues

### A1. Process-local Google Maps cache (HIGH at scale)
**File:** `backend/app/services/google_maps/cache.py:40–44`

`TTLCache` is module-level; each uvicorn worker / Railway replica has its own copy. At 50k users with N workers, Maps API spend scales **linearly with N** despite identical query distributions. At 4 workers × 5 replicas (20 processes), expect ~20× the Google bill the cache *should* prevent.

**Solution:** Move to **Redis-backed cache** (`redis.asyncio`, already in `requirements.txt`, `settings.REDIS_URL` already wired).

Key schema:
```
gmap:find_place:{sha1(query|bias_fp)}    TTL 86400
gmap:place_details:{place_id}:{fields}    TTL 604800
gmap:directions:{mode}:{wp_hash}          TTL 3600
gmap:timezone:{lat,lng}                   TTL 2592000
gmap:negative:{kind}:{key}                TTL 3600
```

Implementation pattern (preserve current interface):
- Create `app/services/cache/redis_cache.py` with `get_json` / `set_json` / `delete` helpers using `redis.asyncio.Redis.from_url(settings.REDIS_URL)` stored on `app.state`.
- Convert each `_<name>_cache` accessor in `cache.py` to call Redis, falling back to TTLCache **only when Redis is unreachable** (graceful degradation — never block enrichment on Redis).
- Drop `asyncio.Lock()` — Redis ops are atomic and the lock was only needed for the dict's non-atomic check-then-set.

**Evaluation:** Reduces Maps spend roughly proportional to (N_workers − 1). Adds one network hop (~1ms LAN) but removes a global asyncio.Lock serialization point that becomes contended at >100 concurrent requests. Mandatory before scaling past 1 replica.

---

### A2. Process-local circuit breaker (MEDIUM at scale)
**File:** `backend/app/services/google_maps/breaker.py:43, 98`

One breaker per process means quota-exhaustion damage scales with worker count: 20 workers can each fire 5 failed requests before independently tripping = 100 failed calls before fleet-wide protection kicks in.

**Solution:** Promote to **Redis-backed breaker** using a `ZSET` of failure timestamps + a key for `opened_at`:
```
gmap:cb:failures (ZSET, score=ts)
gmap:cb:opened_at  TTL = cool-down
```
Atomic ops: `ZADD` failure, `ZREMRANGEBYSCORE` purge old, `ZCARD` count. Open the breaker when `ZCARD > threshold`. Half-open probe is the first request after `opened_at + cool_down`.

**Evaluation:** Same Redis dependency as A1. Implement together. Optional for Phase 1 if running single replica; mandatory before horizontal scaling.

---

### A3. Fire-and-forget GC vulnerability (HIGH — silent data loss)
**Files:** `token_tracker.py:82`, `google_maps/tracker.py:129`

`asyncio.create_task(coro)` without holding a reference can be GC'd. Loss is silent — token cost dashboard and Maps usage records drift downward under load.

**Solution:** Module-level task set with `add_done_callback`:
```python
_active_tasks: set[asyncio.Task] = set()
def _fire(coro):
    try:
        t = asyncio.create_task(coro)
        _active_tasks.add(t)
        t.add_done_callback(_active_tasks.discard)
    except RuntimeError:
        pass
```

**Better long-term:** Move both trackers to a **Celery task** or **Redis Streams** consumer so a worker crash doesn't lose in-flight metrics either. Phase 2.

**Evaluation:** 15-min fix. Stops dashboard drift today; the worker-crash hole remains until Celery/Streams lands.

---

### A4. Long LLM requests hold a pooled DB connection for their full duration (HIGH — capacity)
**Files:** `/api/llm/plan-trip`, `/api/brainstorm/chat`, `/api/brainstorm/extract`, `/api/concierge/chat`

These take **5–40 seconds**. The handlers are `async def`, so the slow `await ...chat(...)` does **not** pin the uvicorn worker — the event loop yields and services other requests while the LLM call is in flight. What *is* held for the full request lifetime is the **DB connection** acquired via `Depends(get_db)`, plus a TCP socket. At 1500 concurrent users and ~10% LLM-bound traffic = ~150 simultaneous slow requests, each holding a pooled connection for 5–40s. With `pool_size=20` (see D1), the pool is exhausted and every other request silently queues on connection acquisition. **The bottleneck is the connection pool, not worker slots.**

**Solution — two moves that address *different* problems:**

1. **Move `/extract` and `/plan-trip` to a job queue** (Celery + Redis broker) — *this is the capacity fix*. Return `{job_id, status: "pending"}` immediately; the handler releases its DB connection in <100ms while the Celery worker does the slow LLM + Maps + dedup work on its own connection. Mandatory for `/extract` because it does LLM + N Maps calls + dedup — easily 30s+. `/plan-trip` follows the same pattern.
   - Celery already has a natural home: Redis is configured, the worker process is cheap.
   - `BrainstormJob` and `PlanTripJob` tables track state.

2. **Stream the prose-only replies** (perceived-latency polish, *not* a capacity lever). This applies to **exactly two paths**:
   - `/api/brainstorm/chat` — returns only `assistant_message`, free text.
   - `/api/concierge/chat` **when `message_type == "text"`** — the conversational reply with no action/place card.

   For these, token-by-token `StreamingResponse` (SSE) lands the first token in <1s — perceived latency drops ~10× on replies that are pure prose.
   - `claude_model.py`, `openai_model.py`, `gemini_model.py`: add `stream_chat()` returning an `AsyncIterator[str]`.
   - Endpoint handlers yield SSE-formatted chunks; persist token tracking from the streaming finalizer, not after.

**Explicitly NOT streamed:**
- **`/extract`** — the LLM returns a single `{user_message, items[]}` object. The items are only usable once complete, the user-facing prose is a one-line confirmation, and the slow tail is the *post-generation* Maps enrichment + dedup, which streaming doesn't touch. Use the job queue.
- **`/plan-trip`** — structured itinerary output; same reasoning. Job queue.
- **Concierge `action_card` / `place_card` paths** — the value is the structured card, which must be complete to render. Streaming the short prose around it buys nothing.

**Evaluation:** Backgrounding `/extract` and `/plan-trip` is what keeps p99 bounded under burst — it returns the pooled DB connection in milliseconds instead of holding it for 30s+. Streaming the two prose paths is a UX win (first-token <1.5s) but does **not** change capacity: the event loop was already free during the await, and a streamed response holds its DB connection at least as long. Don't conflate the two.

---

### A5. Per-call `httpx.AsyncClient` (MEDIUM — latency)
**File:** `backend/app/services/google_maps/v1.py:54, 77, 104, 127`

Each Maps call opens a new TCP+TLS connection (~50–100ms handshake). `enrich_items` already reuses a client; the bare endpoint hits (single `find_place`, `place_details`, route polyline) don't.

**Solution:** App-scoped client on `app.state.http_client`, created in lifespan:
```python
app.state.http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=3, read=10, write=5, pool=5),
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
)
```
Pass into `_request_with_retry`. Close in lifespan shutdown.

**Evaluation:** Saves 50–100ms per single Maps call. Compounds for `/whats-next`, `/find-nearby`, `/route`. Trivial diff; do it.

---

### A6. LLM client lazy init race (LOW — resource leak)
**Files:** `claude_model.py`, `openai_model.py`, `gemini_model.py`

Double-init under concurrent first-request bursts leaves orphaned SDK clients (open sockets, never closed).

**Solution:** Initialize all three clients **eagerly** in FastAPI lifespan and attach to `app.state`. Models receive the client via constructor/DI rather than lazy property.

**Evaluation:** Trivial. Aligns with shared-client pattern from A5.

---

### A7. No LLM timeout guard (MEDIUM — reliability)
**Files:** all three model classes

Anthropic/OpenAI/Gemini SDKs *should* time out internally, but transient TCP black-holes can hang indefinitely. A hung request holds a worker until OS TCP keep-alive fires (10+ min).

**Solution:** Wrap `create()` calls in `asyncio.wait_for(..., timeout=60)`. Surface `asyncio.TimeoutError` as 504 with provider tag.

**Evaluation:** Cheap insurance. For the two streamed prose paths (A4), the `wait_for` wraps the stream open / first chunk rather than the whole call — streaming has its own per-chunk idle-timeout consideration.

---

### A8. Sync work in async handlers (LOW)
The only meaningful blocking call is `google_id_token.verify_oauth2_token()` — CPU-bound RSA verification, ~10–50ms. Acceptable; if it ever becomes hot, wrap in `asyncio.to_thread()`.

---

## Section 2 — Database & CRUD Issues

### D1. DB pool not configured (HIGH — silent stalls)
**File:** `backend/app/db/session.py:5–10`

Default async engine = 5 connections + 10 overflow. At 200+ concurrent users each holding a connection for the full request lifetime (FastAPI dependency injection pattern), requests **silently queue** behind connection acquisition for tens of seconds.

**Solution:**
```python
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    future=True, echo=False, pool_pre_ping=True,
    pool_size=20, max_overflow=20, pool_timeout=10,
    pool_recycle=1800,  # recycle connections every 30 min (matches PgBouncer)
)
```
Tune against Railway Postgres ceiling (hobby ~100, pro ~500). Formula: `replicas × workers × pool_size ≤ 0.7 × pg_max_connections`.

**Evaluation:** Without this, "the app is slow" complaints at 500 concurrent users will be DB-pool starvation that looks like every other latency issue. Mandatory. 5-minute fix.

---

### D2. `get_db()` silent commit on absorbed exceptions (MEDIUM — correctness)
**File:** `backend/app/db/session.py:20`

Trailing `await session.commit()` runs even when a handler catches and absorbs an exception mid-mutation. Edge case but real.

**Solution:**
```python
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Evaluation:** Defensive. Matches industry standard. 10-min fix.

---

### D3. Unbounded list endpoints (HIGH — payload + latency)
**Files (representative):**
- `GET /api/trips/` — `trips.py:57` (all user trips)
- `GET /api/events?trip_id=X` — `events.py:306` (all events of a trip)
- `GET /api/trips/{id}/ideas` — `trips.py:497` (all shared ideas)
- `GET /api/brainstorm/{trip_id}/items` & `/messages` — `brainstorm.py:97`
- `GET /api/admin/users` (no pagination)

At 50k users, "power users" with 50+ trips × 200+ messages per brainstorm will start hitting JSON payloads >1MB and DB result sets >10k rows.

**Solution:** Standardize cursor-based pagination across list endpoints:
```python
class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None
    has_more: bool
```
Default `limit=50`, max `limit=200`. Cursor = base64(`{last_id}|{last_sort_key}`). Add `created_at DESC, id DESC` index on each listed table where missing.

**Evaluation:** Combine with frontend infinite-scroll. Mandatory for `/admin/users`, `/brainstorm/messages`, `/trips/`. Optional for `/events?trip_id` since trips have natural cap. Estimated 1–2 days for backend + frontend pagination plumbing.

---

### D4. Vote tally = 3 count queries per call (MEDIUM — chatty)
**Files:** `votes` endpoints + `events.py:328`, `trips.py:511`

Each idea/event vote read triggers `COUNT(up) + COUNT(down) + my_vote`. Acceptable for one item; bulk listing (50 events) = 150 count queries.

**Solution — pick one:**

**Option (a) — single SQL with conditional aggregation:**
```sql
SELECT
  vote_target_id,
  SUM(CASE WHEN value=1 THEN 1 ELSE 0 END) AS up,
  SUM(CASE WHEN value=-1 THEN 1 ELSE 0 END) AS down,
  MAX(CASE WHEN user_id=:me THEN value END) AS my_vote
FROM vote
WHERE vote_target_id = ANY(:ids)
GROUP BY vote_target_id;
```
Returns all tallies for an event list in one round-trip.

**Option (b) — denormalized counters:**
Add `upvotes_count`, `downvotes_count` columns to `event` and `idea_bin_item`; update via DB trigger or app-layer post-write. Read is free; write does +1 update. *Recommended* if voting becomes a leaderboard pattern.

**Evaluation:** Start with (a) — pure refactor, no schema change. Move to (b) when an endpoint surfaces vote counts at scale (homepage leaderboard, popular ideas digest).

---

### D5. N+1 actor/inviter/group queries (MEDIUM)
- `GET /trips/invitations/pending` — loops over invites to load inviter
- `GET /groups/` — per-group queries for member/trip counts
- `GET /dashboard/today` — per-trip queries for days/events

**Solution:** Apply `selectinload()` / `joinedload()` or rewrite as one SQL with aggregations. For groups specifically:
```python
stmt = (
    select(
        Group,
        func.count(distinct(GroupMember.user_id)).label("member_count"),
        func.count(distinct(GroupTrip.trip_id)).label("trip_count"),
    )
    .join(GroupMember).outerjoin(GroupTrip)
    .where(GroupMember.user_id == current_user.id)
    .group_by(Group.id)
)
```

**Evaluation:** Each fix is 10–30 min. Cumulative effect on dashboard load is ~10× speedup at the upper end.

---

### D6. Brainstorm dedup scans all user items (HIGH — degrades over time)
**File:** `backend/app/api/brainstorm.py:307`

`existing_rows = (await db.execute(existing_stmt)).scalars().all()` loads every brainstorm bin item the user owns, in Python memory, for dedup. A heavy user with 1000 items pays 1000-row hydration every `/extract` call.

**Solution:** Move dedup into SQL:
```sql
INSERT INTO brainstorm_bin_item (...)
SELECT ... FROM unnest(:proposed) AS p(name, city)
WHERE NOT EXISTS (
    SELECT 1 FROM brainstorm_bin_item b
    WHERE b.user_id = :uid AND b.trip_id = :tid
      AND lower(b.name) = lower(p.name)
      AND lower(coalesce(b.city,'')) = lower(coalesce(p.city,''))
);
```
Or simpler: a partial unique index `(user_id, trip_id, lower(name), lower(city))` + `ON CONFLICT DO NOTHING`. Add index `brainstorm_bin_item(user_id, trip_id)` if absent.

**Evaluation:** Removes O(N_items) scan per extract. Mandatory before opening Plus to power users.

---

### D7. Loop-based cascade deletes (MEDIUM)
**Files:** `trips.py:484` (delete trip), `trips.py` (delete day)

Looping `await db.delete(event)` over 1000 events = 1000 round-trips. Worst case: 5s for a large trip delete.

**Solution:** Single statements:
```python
await db.execute(delete(EventModel).where(EventModel.trip_id == trip_id))
await db.execute(delete(IdeaBinItem).where(IdeaBinItem.trip_id == trip_id))
# ... etc
```
Better: define `ON DELETE CASCADE` foreign keys on the related tables and `await db.delete(trip)` does it in one shot DB-side.

**Evaluation:** Pair with backgrounding the delete itself (Celery job) for very large trips so the API returns in <100ms.

---

### D8. Missing indexes (MEDIUM)
- `brainstorm_message(trip_id, user_id, extracted_at)` — composite for extract filter
- `brainstorm_bin_item(user_id, trip_id)` — pairs with D6
- `timeline_item(trip_id, is_skipped)` — ripple engine scan
- `vote(target_kind, target_id)` — already implied by FK but verify a composite index exists
- `notification(user_id, read_at, created_at DESC)` — paginated feed

**Solution:** Add via Alembic migration. Verify with `EXPLAIN ANALYZE` on the actual query before/after.

**Evaluation:** Each ~5 min to add. Verify under realistic data volumes.

---

### D9. Date-shift cascade in `PATCH /trips/{id}` (MEDIUM)
On trip start-date change, every day + every event shifts. For 14-day trips with 50 events, that's 64 row updates per PATCH. Currently synchronous; latency spike visible to user.

**Solution:**
- Single `UPDATE` statement with computed offset rather than per-row Python loop.
- Move to a Celery job for trips with >20 events; return 202 + job_id.

**Evaluation:** SQL approach captures 90% of the win. Backgrounding is for the long-tail.

---

### D10. JSONB columns not indexed (LOW — currently fine)
`personas`, `metadata_`, `raw_payload` are JSON. Currently no `->` queries against them. If/when we add "users who selected persona X" or filter token usage by `extra->>'source'`, add a GIN index on the relevant column.

---

## Section 3 — Architectural Redesigns (Beyond Tactical Fixes)

These are the redesigns that pay off **only** at 50k scale and would be premature today, but the team should plan for them now.

### R1. Introduce Celery + Redis broker
**Why:** Three categories of work belong off the request path:
1. **Slow LLM jobs** — `/extract`, `/plan-trip` enrichment, large `/concierge` actions
2. **Email & webhook side-effects** — auth verify, password reset, Razorpay webhook acknowledgments
3. **Cascade writes** — trip delete with thousands of events, persona-driven re-enrichment

**Stack:** Celery 5 + Redis broker + result backend (or DB). One worker process per replica. `celery-beat` for scheduled cleanup (purge expired tokens, archive old brainstorm messages).

**Migration order:**
- Phase A: email sends (`auth.py` verify/reset/change)
- Phase B: Razorpay webhook follow-ups
- Phase C: `/extract` job + status polling endpoint
- Phase D: trip cascade delete

**Evaluation:** Each phase independently shippable. Phase A alone removes 200–500ms from auth flows.

---

### R2. Pull cache, breaker, rate-limits, fire-and-forget metrics into a shared Redis tier
Tactical fixes A1, A2, A3, plus new rate limiting:
- Per-user LLM rate: `user:{id}:llm:{date}` INCR with EX 86400
- Per-IP signup rate: `ip:{addr}:signup` token bucket
- Maps daily quota: `maps:{date}:count`

Use `slowapi` or a custom `Depends(rate_limit("plan-trip", 10, 60))`.

**Evaluation:** Without rate limits, one malicious or buggy client can torch the LLM budget. Mandatory before public launch beyond beta.

---

### R3. Streaming for prose-only LLM replies
Already in A4 — listing here for completeness. **Scope: only the two prose-only paths** — `/api/brainstorm/chat` and `/api/concierge/chat` when `message_type == "text"`. Structured-output endpoints (`/extract`, `/plan-trip`) and the concierge card paths are deliberately excluded — they go through the Celery job queue (R1), not SSE. Requires:
- Backend: `StreamingResponse` + provider `.stream()` adapters **on the two prose paths only**
- Frontend: SSE consumer + incremental rendering — **gated on client work** (iOS `URLSession.bytes`, Web `fetch().body.getReader()`); neither client is SSE-ready today (see Decisions Locked In)
- Token tracking: persist on stream finalize, not on first response

**Evaluation:** Largest perceived-latency improvement available *for conversational replies* — p95 first-token <1.5s vs current p95 full-response ~12s. **Not a capacity lever** (see A4): the async event loop is already free during the LLM await, and the capacity unlock is backgrounding the structured endpoints, not streaming.

---

### R4. Read-replica or read-through cache for hot reads
At 50k users, dashboard + trip-detail + notifications make up 70%+ of traffic and are all read-mostly. Two options:

**Option (a) — Postgres read replica:** Route `GET` endpoints with `?fresh=false` semantics to a replica. Adds replication lag concern (~100ms) but no app-layer cache invalidation problem.

**Option (b) — Application-level read-through cache:** Cache `GET /trips/{id}`, `/dashboard/today`, `/notifications` payloads in Redis keyed by user+resource, invalidate on writes via SQLAlchemy event hooks.

**Evaluation:** Defer until measurement shows DB read saturation. Don't prematurely cache — the invalidation logic is where bugs hide.

---

### R5. Connection pooling at the boundary (PgBouncer)
At 20+ Python processes each with `pool_size=20`, raw Postgres connection count hits 400+. PgBouncer in transaction-pooling mode lets each Python process target an unlimited "virtual" pool while the bouncer multiplexes onto ~50 real Postgres connections. Railway supports this; if not, deploy a sidecar.

**Evaluation:** Mandatory above ~5 backend replicas. Compatible with asyncpg but **incompatible with prepared statements**, so verify SQLAlchemy isn't relying on server-side prepare cache (it doesn't by default with async engine).

---

### R6. Observability that survives 50k scale
Current: log lines like `token_usage op=... provider=... tokens_total=...`.
At 50k users this becomes unparseable. Need:
- **Structured logs** (JSON formatter) — drop into Loki/Datadog
- **Per-endpoint p50/p95/p99 latency histograms** (Prometheus or Datadog APM)
- **DB connection pool metrics** (saturation, wait time)
- **LLM/Maps cost dashboards** — already partially there via TokenUsage / GoogleMapsApiUsage tables; just need a daily aggregation job + admin UI tile

**Evaluation:** Without this, every incident at 50k scale is a guess-and-check exercise. 2–3 days of infra work; pays back on the first outage.

---

## Section 4 — Prioritized Roadmap

Ordered by **risk-adjusted value** (impact ÷ effort, weighted by severity of failure mode).

### Phase 1 — Same-week wins (cheap, defensive)
| # | Item | Effort | Notes |
|---|------|--------|-------|
| 1 | **D1** Pool config | 5 min | Prevents silent stalls — do today |
| 2 | **A3** Task-set for fire-and-forget | 15 min | Stops metric drift |
| 3 | **D2** Explicit rollback in `get_db` | 10 min | Correctness |
| 4 | **A7** LLM `asyncio.wait_for(60)` | 20 min | Stops hung workers |
| 5 | **D8** Missing indexes | 30 min | One Alembic migration |
| 6 | **A5/A6** Shared `httpx` + eager LLM clients | 1 hr | Bonus latency |

**Total: half a day. Ship as one PR.**

### Phase 2 — Pagination & query fixes (1 week)
| # | Item | Effort | Notes |
|---|------|--------|-------|
| 7 | **D3** Cursor pagination on list endpoints | 1–2 days | Backend + frontend |
| 8 | **D4** Vote tallies in one query | 2 hrs | Pure refactor |
| 9 | **D5** Fix N+1 in invites, groups, dashboard | 4 hrs | `selectinload` pass |
| 10 | **D6** SQL-side brainstorm dedup | 3 hrs | + partial unique index |
| 11 | **D7/D9** Bulk delete + bulk date shift | 3 hrs | DB cascade FKs |

### Phase 3 — Redis tier (1 week)
| # | Item | Effort | Notes |
|---|------|--------|-------|
| 12 | **A1** Redis-backed Maps cache | 1 day | Drop-in for current cache.py |
| 13 | **A2** Redis-backed circuit breaker | 0.5 day | After A1 |
| 14 | **R2** Rate limiting | 1 day | `slowapi` + Redis |

### Phase 4 — Streaming + queueing (2 weeks)
| # | Item | Effort | Notes |
|---|------|--------|-------|
| 15 | **A4 / R3** Streaming prose-only replies | 1 week | Brainstorm chat + concierge `text` reply only; NOT extract/plan-trip |
| 16 | **R1** Celery + email/webhook offload | 0.5 week | Phase A only |
| 17 | **R1** Celery for `/extract` + `/plan-trip` jobs | 1 week | Frontend polling/SSE |

### Phase 5 — Pre-scale (when DAU > 3k)
| # | Item | Effort | Notes |
|---|------|--------|-------|
| 18 | **R5** PgBouncer | 0.5 day | Infra change |
| 19 | **R6** Structured logs + APM | 2–3 days | Observability |
| 20 | **R4** Read-through cache | 1 week | Only if metrics demand it |

---

## Verification Plan

Each phase ships with verification gates. Don't skip these — silent regressions are the most expensive bugs at scale.

1. **Phase 1 sanity:** Full pytest pass (~480 tests). Hand-verify token_usage rows persist after `/api/llm/plan-trip` under simulated load (`ab -n 50 -c 10`).
2. **Phase 2 query plans:** `EXPLAIN ANALYZE` the rewritten dedup and vote-tally queries on a seeded DB of 10k users × 50 trips × 200 ideas. Latency budget: <50ms p95.
3. **Phase 3 Redis:** Bring up two backend replicas locally via docker-compose, confirm cache hits cross-process. Kill Redis mid-request — verify graceful fallback path.
4. **Phase 4 streaming:** First-token <1.5s p95 on `/brainstorm/chat` and the concierge `message_type == "text"` path — the only two streamed endpoints. Verify token tracker still persists on stream completion *and* on client disconnect. Confirm `/extract` and `/plan-trip` were **not** converted to SSE — they must return via the job-polling path. Streaming is verified as a perceived-latency win, not a capacity win (capacity is covered by the job-queue gate).
5. **Phase 5 load test:** k6 or Locust script — ramp to 1500 concurrent virtual users hitting dashboard/today + brainstorm/messages + concierge/chat. Acceptance: p95 < 2s for cached reads, p95 < 5s first-token for chat.

---

## Out of Scope (Explicitly Deferred)

- **Multi-region deployment** — single Railway region is fine through 50k users.
- **Sharding / Citus** — Postgres on Railway pro handles 50k easily; revisit at 500k.
- **GraphQL / batched APIs** — REST + pagination is sufficient.
- **CDC pipelines / event sourcing** — overkill at this scale.
- **Replace SQLAlchemy with raw asyncpg** — driver isn't the bottleneck.

---

## Decisions Locked In (2026-05-22)

- **Single replica today** → A1 (Redis Maps cache) and A2 (Redis breaker) stay in Phase 3, **not** urgent. Process-local state is acceptable at current scale; revisit the day we add a second replica.
- **Celery + Redis** is the chosen job runner. R1 phases (A → D) proceed as written.
- **Neither iOS nor Web client is SSE-ready today.** Streaming (A4 / R3) is **deferred to Phase 4b** behind a frontend prerequisite, and is **scoped to the two prose-only paths only** — `/api/brainstorm/chat` and the concierge `message_type == "text"` reply. `/extract` and `/plan-trip` are never streamed; they go through the job queue. Phase 4a stays focused on Celery offload (`/extract`, `/plan-trip`, emails, webhooks) using request-response + job polling — which already relieves the connection-pool pressure without needing streaming. Streaming becomes a perceived-latency polish layer for conversational replies once clients are updated.

## Revised Phase 4

| # | Item | Effort | Notes |
|---|------|--------|-------|
| 15a | **R1** Celery + email/webhook offload (Phase A) | 0.5 week | Auth verify, password reset, Razorpay webhook follow-ups |
| 15b | **R1** Celery for `/extract` + `/plan-trip` as polling jobs | 1 week | Endpoint returns `{job_id}`; client polls `/jobs/{id}` |
| 15c | **R1** Trip cascade delete as background job | 2 days | After 15b infra lands |
| 16 (deferred) | **A4 / R3** Streaming prose-only replies (brainstorm chat + concierge `text`) | 1 week BE + 1 week FE | Blocked on iOS `URLSession.bytes` + Web SSE reader work; NOT extract/plan-trip |

The polling-job pattern (15b) is the capacity unlock — the handler hands off to Celery and releases its DB connection in milliseconds. Streaming provides **no** capacity benefit (the async event loop is already free during the LLM await, and a streamed response holds its DB connection at least as long); it is purely perceived-latency polish, and only for the two prose-only replies — `/api/brainstorm/chat` and the concierge `message_type == "text"` path.

## Still Open

- **Migration windows for D8 indexes:** prefer `CREATE INDEX CONCURRENTLY` via raw SQL in Alembic to avoid table locks; confirm before Phase 1 ships.
