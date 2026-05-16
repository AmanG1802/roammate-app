# Async Pattern Evaluation — Roammate Backend

## Current Async Architecture (Summary)


| Layer               | Pattern                                      | Status |
| ------------------- | -------------------------------------------- | ------ |
| Route handlers      | `async def`, 100%                            | ✅      |
| DB sessions         | `AsyncSession` + asyncpg                     | ✅      |
| HTTP clients        | `httpx.AsyncClient`                          | ✅      |
| LLM SDKs            | `AsyncAnthropic`, `AsyncOpenAI`, `genai.aio` | ✅      |
| Concurrency control | `asyncio.Semaphore(5)` for map enrichment    | ✅      |
| Background work     | `asyncio.create_task()` fire-and-forget      | ⚠️     |
| In-process cache    | `cachetools.TTLCache` + `asyncio.Lock`       | ⚠️     |
| Circuit breaker     | In-process per-worker                        | ⚠️     |
| Connection pool     | Default pool, no explicit config             | ⚠️     |
| `httpx` client      | New context manager per call                 | ⚠️     |


---

## Issues Found

### Issue 1 — Fire-and-forget tasks can be silently GC'd (HIGH)

**Files:** `backend/app/services/google_maps/tracker.py:129`, `backend/app/services/llm/token_tracker.py:82`

```python
try:
    asyncio.create_task(_persist_maps_usage(fields))
except RuntimeError:
    pass
```

`asyncio.create_task()` returns a `Task` object. If no reference is held to it, CPython's garbage collector can collect and cancel it before it completes — usage records silently disappear. The Python docs explicitly warn about this. The `RuntimeError` catch handles the "no running event loop" edge case, but the GC problem is independent.

**Risk:** Token and Maps usage records are dropped under memory pressure or during shutdown, corrupting the admin cost dashboard.

---

### Issue 2 — `get_db()` commits unconditionally but lacks explicit rollback (MEDIUM)

**File:** `backend/app/db/session.py:20–23`

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
        await session.commit()  # only reached on clean exit
```

SQLAlchemy's `AsyncSession.__aexit__` does call `rollback()` + `close()` when an exception propagates, so the happy path is safe. However, the intent is invisible: a future dev may not know that the `async with` is what guards the rollback. More concretely: if a handler internally catches an exception (without re-raising) after partially modifying session state, those mutations will be committed by the trailing `await session.commit()` even though the handler's own logic considered the operation failed.

**Example of the silent-commit bug:**

```python
async def my_handler(db: AsyncSession = Depends(get_db)):
    db.add(SomeModel(...))
    try:
        await risky_operation()  # raises, caught below
    except Exception:
        pass  # absorbed — but db.add() is still pending
    return {"ok": True}  # get_db commits the dangling add
```

---

### Issue 3 — In-process cache not shared across workers (MEDIUM)

**File:** `backend/app/services/google_maps/cache.py:39–42`

```python
_find_place_cache: TTLCache = TTLCache(maxsize=4096, ttl=_FIND_PLACE_TTL)
```

These are module-level Python dicts. Each uvicorn worker process (or Railway replica) holds an independent cache. Cache hits in one process don't benefit other processes, so Google Maps API call count scales with the number of workers rather than plateauing. Redis is already listed in `requirements.txt` and configured in `settings.REDIS_URL` — a drop-in Redis backend would unify cache state across the fleet.

---

### Issue 4 — Circuit breaker is per-process (MEDIUM)

**File:** `backend/app/services/google_maps/breaker.py:98`

```python
breaker = CircuitBreaker()  # module-level singleton, per process
```

Same problem as Issue 3. If one worker exceeds Google's rate limit and trips the breaker, other workers continue making requests. Conversely, if the breaker opens due to a transient blip seen only by one worker, the other workers recover normally — which is fine but means the breaker doesn't protect against fleet-wide quota exhaustion.

---

### Issue 5 — `httpx.AsyncClient` opened per call, no connection reuse (LOW-MEDIUM)

**File:** `backend/app/services/google_maps/base.py:194`

The Maps service opens a new `httpx.AsyncClient` as a context manager on each API call:

```python
async with httpx.AsyncClient(...) as client:
    await client.request(...)
```

Each context manager creates and destroys a TCP connection pool. For burst enrichment (5 concurrent items via `asyncio.gather`), this means 5 independent TLS handshakes to Google's servers. A shared application-scoped client would reuse connections and reduce latency by 50–100 ms per enrichment call.

---

### Issue 6 — No explicit pool size on async engine (LOW)

**File:** `backend/app/db/session.py:5–10`

```python
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    future=True,
    echo=False,
    pool_pre_ping=True,
    # no pool_size, max_overflow, pool_timeout
)
```

asyncpg's default pool size is 5 connections. Under concurrent brainstorm/concierge traffic, each request holds a DB connection for its entire lifetime (from dependency injection to request end). With 5+ concurrent LLM-backed requests, connection starvation is possible. Explicit `pool_size=10, max_overflow=20` and `pool_timeout=30` would surface this as a clear 503 instead of a silent hang.

---

### Issue 7 — LLM client lazy init has a race window (LOW)

**Files:** `backend/app/services/llm/models/claude_model.py`, `openai_model.py`, `gemini_model.py`

Each model class holds `_client = None` and initializes on first call. In async Python, two concurrent requests can both reach `if self._client is None` before either has set `_client`, causing two SDK client objects to be created (the old one is immediately orphaned). The clients are cheap to create and initialization is idempotent, so no data is corrupted — but the orphaned client holds an open connection/socket that's never closed.

---

## Enhancement Plan

### Enhancement A — Fix fire-and-forget task lifetime (addresses Issue 1)

**Files:** `backend/app/services/google_maps/tracker.py`, `backend/app/services/llm/token_tracker.py`

Maintain a module-level `set` of active tasks. Add each created task to the set; remove it via an `add_done_callback`. This is the pattern recommended in the Python docs.

```python
_active_tasks: set[asyncio.Task] = set()

def _fire(coro):
    try:
        task = asyncio.create_task(coro)
        _active_tasks.add(task)
        task.add_done_callback(_active_tasks.discard)
    except RuntimeError:
        pass
```

Replace both `asyncio.create_task(...)` calls with `_fire(...)`.

---

### Enhancement B — Make `get_db()` rollback explicit (addresses Issue 2)

**File:** `backend/app/db/session.py`

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

This makes the contract explicit — any exception, including those from `HTTPException`, triggers an explicit rollback before the session closes.

---

### Enhancement C — Redis-backed Maps cache (addresses Issues 3 and 4)

**Files:** `backend/app/services/google_maps/cache.py`, optionally `backend/app/services/google_maps/breaker.py`

Replace `cachetools.TTLCache` with Redis using `redis[asyncio]` (already in requirements). Key schema:

- `gmap:find_place:{sha1(query)}` → serialized result, TTL 86400
- `gmap:place_details:{place_id}:{fields_sig}` → serialized result, TTL 604800
- `gmap:directions:{mode}:{waypoint_hash}` → serialized result, TTL 3600

Drop `asyncio.Lock()` — Redis operations are already atomic.

Circuit breaker can share state via a Redis sorted set (failure timestamps) and a key for `opened_at`. This is optional for Phase 1; the cache is higher value.

**Note:** Only needed when running multiple workers/replicas. Single-worker Railway deployments don't require this.

---

### Enhancement D — Shared `httpx.AsyncClient` (addresses Issue 5)

**Files:** `backend/app/main.py`, `backend/app/services/google_maps/base.py`

Create one `httpx.AsyncClient` in the FastAPI lifespan and store it on `app.state`. Pass it into `_request_with_retry`.

```python
# main.py lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    # ... existing startup ...
    yield
    await app.state.http_client.aclose()
```

---

### Enhancement E — Explicit DB pool configuration (addresses Issue 6)

**File:** `backend/app/db/session.py`

```python
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    future=True,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)
```

Tune `pool_size` against Railway's PostgreSQL connection limit (hobby: ~100 total; 10 workers × 10 pool = ceiling).

---

### Enhancement F — LLM timeout guard (bonus)

**Files:** `backend/app/services/llm/models/claude_model.py`, `openai_model.py`, `gemini_model.py`

Wrap each provider's `create()` call with `asyncio.wait_for(..., timeout=60)`. LLM APIs can hang indefinitely on transient failures; without a timeout, a stalled request holds a DB connection and a uvicorn worker slot until the OS TCP timeout fires (often 10+ minutes).

---

## Priority Order


| Priority | Enhancement                 | Effort  | Impact                           |
| -------- | --------------------------- | ------- | -------------------------------- |
| 1        | **A** — Task GC fix         | 15 min  | High — stops silent data loss    |
| 2        | **B** — Explicit rollback   | 10 min  | Medium — correctness/clarity     |
| 3        | **E** — Pool config         | 5 min   | Medium — prevents silent hangs   |
| 4        | **F** — LLM timeout         | 20 min  | Medium — reliability             |
| 5        | **D** — Shared httpx client | 30 min  | Low-medium — latency improvement |
| 6        | **C** — Redis cache         | 2–4 hrs | Medium — only if multi-worker    |


---

## Verification (when implementing)

1. Run full test suite: `cd backend && pytest -x -q`
2. Confirm token tracker writes persist: check `TokenUsage` rows after `/api/llm/plan-trip`
3. Confirm Maps tracker writes persist: check `GoogleMapsApiUsage` rows after a brainstorm extract
4. Trigger mid-handler exception; verify no partial DB state is committed (Issue 2 regression)
5. Under load, confirm no DB connection starvation with new pool settings

