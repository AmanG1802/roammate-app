# Backend Test Suite

All backend tests live under `backend/tests/`. The suite is organized into three
tiers — **unit**, **integration**, and **api** — plus two root-level smoke tests.

**Test count:** ~769 test functions across 88 files.

---

## Layout

```
backend/tests/
├── conftest.py                         # shared fixtures (SQLite in-memory, auth headers, helpers)
├── pytest.ini                          # asyncio_mode = auto, log settings
├── test_openapi_spec.py                # OpenAPI schema smoke tests
├── test_enrichment_status.py           # enrichment pipeline checks
├── api/                                # HTTP-level tests against the ASGI app (17 files, ~120 tests)
├── unit/                               # pure unit tests — no DB, no network (34 files, ~307 tests)
└── integration/                        # multi-layer tests with in-memory SQLite (35 files, ~330 tests)
```

### api/ — endpoint contract tests

Each file maps to a REST domain and exercises HTTP verbs, status codes, auth
requirements, and authz boundaries through the `httpx` `AsyncClient`.

| File | Domain |
|---|---|
| `test_api_admin.py` | Admin panel |
| `test_api_auth.py` | Signup / login / OAuth / tokens |
| `test_api_billing.py` | Razorpay / subscription |
| `test_api_brainstorm.py` | Brainstorm chat + bin |
| `test_api_concierge.py` | AI Concierge |
| `test_api_dashboard.py` | Dashboard aggregation |
| `test_api_events.py` | Timeline events |
| `test_api_groups.py` | Groups CRUD |
| `test_api_health.py` | Health check |
| `test_api_ideas.py` | Idea bin |
| `test_api_llm.py` | LLM plan-trip |
| `test_api_maps.py` | Maps / geocoding endpoints |
| `test_api_notifications.py` | Notification list + read |
| `test_api_trips.py` | Trips CRUD + lifecycle |
| `test_api_tutorial.py` | Tutorial flow |
| `test_api_users.py` | User profile / personas |
| `test_api_votes.py` | Voting |

### unit/ — pure logic tests

No database, no ASGI app. External I/O is mocked. Covers LLM pipeline modules,
maps utilities, security helpers, Pydantic schema validation, ripple engine math,
roles, pagination, coupons, entitlements, and more.

### integration/ — cross-layer tests

Hit the ASGI app or use a real `db_session` (in-memory SQLite) to verify
multi-service flows: lifecycle scenarios, notification fanout, vote transfer,
brainstorm enrichment, concurrency, caching, role gating, etc.

---

## Running Tests

All commands are run from `backend/`.

```bash
# full suite
pytest tests/

# single tier
pytest tests/api -v
pytest tests/unit -v
pytest tests/integration -v

# single file
pytest tests/api/test_api_trips.py -v

# single test function
pytest tests/api/test_api_trips.py::test_create_trip_basic -v

# keyword filter
pytest tests/ -k "brainstorm" -v

# stop on first failure
pytest tests/ -x

# show local variables on failure
pytest tests/ -l --tb=short

# run with verbose + short traceback (good default for debugging)
pytest tests/ -v --tb=short
```

### Parallel execution (optional)

Install `pytest-xdist` and run with `-n auto` to use all CPU cores:

```bash
pip install pytest-xdist
pytest tests/ -n auto
```

> **Note:** each worker gets its own in-memory SQLite, so parallelism is
> safe but total memory usage scales linearly.

---

## Coverage Report

Install `pytest-cov` (not included in `requirements.txt` by default):

```bash
pip install pytest-cov
```

### Terminal summary

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

### HTML report

```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html        # macOS
```

### Combined (terminal + HTML + XML for CI)

```bash
pytest tests/ \
  --cov=app \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=xml:coverage.xml
```

### Checking a minimum threshold

```bash
pytest tests/ --cov=app --cov-fail-under=80
```

> `htmlcov/` and `coverage.xml` are already in `.gitignore`.

---

## Configuration

Test configuration lives in `tests/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
testpaths = .
python_files = test_*.py
log_cli = false
log_level = ERROR
```

`asyncio_mode = auto` means no `@pytest.mark.asyncio` decorator is needed on
individual test functions.

---

## Environment Variables

| Variable | Default / Behavior |
|---|---|
| `OPENAI_API_KEY` | Unset or stub → NLP service returns stub |
| `GOOGLE_MAPS_API_KEY` | Unset → GMaps service falls back to Rome mock |
| `SECRET_KEY` | Uses default from `app.core.config` if not set |
| `LLM_ENABLED` | `False` → brainstorm / LLM tests use deterministic Bangkok fallback |

No real API keys or network access are needed to run the full suite.

---

## Fixtures & Conventions

- HTTP tests use `client` + `auth_headers` / `second_auth_headers` / `third_auth_headers` / `admin_headers` fixtures from `conftest.py`.
- `db_session` provides a direct async SQLAlchemy session for unit/integration tests that don't need HTTP.
- `tracker_db` monkeypatches fire-and-forget tracker writes to the test SQLite engine.
- Google Maps `find_place` is globally stubbed to `None` in conftest so no network calls are made.
- SQLite `PRAGMA foreign_keys = ON` is enabled per-connection so cascade behavior matches Postgres.
- Every new endpoint should get: happy path, auth required, authz boundary (non-member / non-admin), not-found, validation error.

---

## Known Infrastructure Gaps

- **SQLite vs Postgres behavioral differences** — some edge cases (e.g., JSON operators, `RETURNING` quirks) only reproduce on Postgres; the suite uses SQLite for speed.

## Explicit Non-Goals

- Unicode / very long group names, tag names, idea titles
- Concurrent same-user vote (last-write-wins is current behavior)
- Removing last group admin — prevented by 400; revisit if admin handoff is added
- Notification `payload` shape drift — don't pin exact keys per type beyond `trip_name` / `self`
- `before_id` pagination with tombstones
- Large library (>1000 ideas) performance
- `freezegun`-based assertion for `quick_add`'s 10 AM fallback
- CORS smoke test
- Large `delta_minutes` / datetime overflow on ripple
- Real LLM integration tests (`LLM_ENABLED=True`) — requires API key; covered by manual QA
- Concurrent brainstorm promotion by two users — last-write-wins
- Chat message size limits / adversarial input to LLM facade
