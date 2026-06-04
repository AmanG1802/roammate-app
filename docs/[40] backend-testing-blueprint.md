# Backend Testing Strategy & Implementation Blueprint: Roammate

This document serves as the comprehensive source of truth and architectural reference for building, structuring, and executing the backend test suite for **Roammate**.

Use this blueprint to scaffold tests, configure fixtures, establish boundaries, integrate code coverage, and maintain consistency across unit, integration, API/E2E, smoke, and scale testing tiers.

---

## 1. System Context & Testability Boundaries

Roammate is an asynchronous, AI-native, geospatial, and event-driven application. Because its architecture relies heavily on third-party services and background processing, the network boundary must be strictly controlled during automated test execution.

### Tech Stack Constraints
* **Runtime & Framework:** Python 3.13, FastAPI (fully async execution).
* **Data Layer:** PostgreSQL managed via SQLAlchemy (`asyncio` extension), Redis.
* **Task Queue:** Celery for heavy processing (Map enrichment, AI Concierge pipelines).
* **External APIs:** OpenAI, Anthropic, Google GenAI, Google Maps (v1 & v2), Apple Maps, Razorpay, StoreKit 2.

### Testing Principles & Environment Control
1. **Never Pollute Production/Local Dev Data:** All testing must execute against an isolated, distinct testing database (e.g., `roammate_test`).
2. **Zero Live Network Calls in Standard Suites:** No real HTTP requests may be made to external LLM providers, Google Maps, or payment gateways during Unit, Integration, or API tests.
3. **Deterministic Background Tasks:** For standard unit/integration cycles, background asynchronous behavior must be forced into a synchronous, predictable execution line.

---

## 2. Directory Structure & Architecture

The test suite is divided into five specialized tiers to isolate side effects, control test execution speed, and balance coverage.

```
backend/tests/
├── conftest.py                  # Global async fixtures, DB state, & client setups
├── unit/                        # Fast, isolated domain logic tests (Zero DB, Zero Network)
│   ├── test_intent_pipeline.py  # Regex/Zero-LLM pre-processor token extraction
│   └── test_ripple_engine.py    # Algorithmic schedule shifting verification
├── integration/                 # Service layers, ORM relationships, and database states
│   ├── test_maps_enrichment.py  # Mocked HTTP responses to test hydration pipelines
│   └── test_state_lifecycle.py  # Tracking item conversion: Chat -> Bin -> IdeaBinItem
├── api/                         # Endpoint HTTP routing, JSON validation, and RBAC
│   ├── test_auth.py             # JWT, OAuth flows, and Admin Panel isolation
│   └── test_trips.py            # Route protection, 403 Forbidden checks, and 422 payloads
├── smoke/                       # Post-deployment live sanity checks (Strictly isolated)
│   └── test_prod_health.py      # Real network pings to live dependencies, health check endpoints
└── scale/                       # Performance testing, rate limits, and connection soaking
    └── load_test_trips.py       # Locust/K6 simulation scripts for concurrency
```

---

## 3. The Core Execution Tiers

### Tier 1: Unit Tests & Code Coverage
Focus entirely on deterministic, pure-Python logic. These tests must execute in milliseconds and have no access to databases or external client objects.
* **The Intent Pre-processor:** Feed multiple text strings containing various formats of cities, dates, and intent signals to verify that the extraction algorithm behaves identically without needing an LLM.
* **Smart Ripple Engine:** Mock a rigid structured timeline array (`TripDays` and `Events`). Simulate moving an event forward or backward. Validate that all trailing events shift precisely by the delta duration and that immutable constraints (e.g., locked flight departure times) trigger custom domain exceptions.
* **Coverage Requirements:** Unit tests must meet a strict coverage threshold calculated via `pytest-cov`. Since unit tests assert the core stability of the system's business logic, target **90%+ branch coverage** exclusively on domain calculations, routing logic engines, and validation schemas.

### Tier 2: Integration Tests
Test the interaction between your business services and the PostgreSQL database layer via SQLAlchemy async sessions.
* **State Lifecycles:** Verify that an item extracted dynamically from a private `Brainstorm Chat` is safely written to the user's `Brainstorm Bin`. Assert that when elevated, it creates a synchronized `IdeaBinItem` visible to all members of the `Trip`.
* **Database Session Lifecycle:** Ensure every test runs inside an isolated database transaction block that automatically rolls back after execution, leaving the test tables completely pristine.

### Tier 3: API/E2E Tests
Validate HTTP layers, path parameters, payload structures, status codes, and security.
* **Role-Based Access Control (RBAC):** Assert that a non-member of a `Trip` attempting to alter an itinerary via `POST /api/v1/trips/{id}/events` is immediately rejected with a `403 Forbidden` status code.
* **Data Validation:** Validate that malformed payloads (e.g., longitude values exceeding bounds) are immediately caught by Pydantic, returning a `422 Unprocessable Entity` without executing downstream service logic.

### Tier 4: Smoke Tests
Run independently from the main test suite, typically executed post-deployment or during a deployment pipeline stage. Unlike earlier tiers, **smoke tests talk directly to live systems.**
* **Health and Connectivity Check:** Target the live environment (`/health` or `/status` endpoints).
* **Live Dependency Ping:** Verify that backend service workers can securely authenticate with Redis, PostgreSQL, and external APIs (using safe echo/ping endpoints provided by OpenAI or Google Maps where possible) to ensure credentials haven't expired or misconfigured in production variables.
* **Read-Only Probing:** Verify basic read routing on a designated production-safe test entity to confirm that migrations executed successfully on the live database.

### Tier 5: Scale & Performance Tests
Executed standalone and kept completely isolated from regular CI pipelines to prevent resource starvation. Scale tests measure infrastructure performance under heavy concurrent usage.
* **Concurrent Write Saturation:** Simulate hundreds of simultaneous client requests executing mutations on the same `Trip` resource to verify that SQLAlchemy's connection pool doesn't exhaust and that PostgreSQL Row-Level Locks or pessimistic locking schemas handle concurrent edits gracefully.
* **The Ripple Engine Soak:** Stress-test the `Smart Ripple Engine` by triggering cascading changes on a trip containing hundreds of days and events to profile CPU and query execution bottlenecks.
* **Rate-Limit Safeguards:** Assert that automated malicious bursts of requests trigger HTTP `429 Too Many Requests` at your gateway or FastAPI middleware layer before overwhelming backend resource limits.

---

## 4. Engineering Guidelines & Mocking Strategy

When writing or interpreting code within this suite, adhere strictly to these technical implementations:

### Framework & Plugins
* Use `pytest` as the principal framework runner.
* Utilize `pytest-asyncio` for executing async functions and managing async fixtures.
* Configuration values must be driven dynamically via `pytest-env`, utilizing a `.env.test` file.

### Syncing the Asynchronous Queue (Celery)
To test asynchronous workflows without setting up local background workers during unit and integration runs, configure Celery to run tasks immediately in the current execution thread:
```python
# Forced synchronous execution setting for testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

### Mocking Interfaces over Network Adaptors
Do not mock low-level HTTP network sockets directly using libraries like `responses` or `urllib` wrappers for your primary app services. Instead, intercept requests cleanly at your abstracted code boundaries:

* **LLM Calls:** Mock the unified service class (`BaseLLMService`). Provide static, pre-formatted mock JSON strings that resemble realistic model responses to verify that your data translation layers function properly under valid and corrupted JSON responses.
* **Maps Enrichment:** Mock the high-level routing class functions (`find_place`, `place_details`, `hydrate_fields`). Isolate and test how your application behaves when Google Maps returns an empty result set or a broken response structure.

---

## 5. Coverage Calculation Configuration

To automate coverage calculation without cluttering the CLI runtime, add a configuration footprint to your backend root directory.

### Step 1: Add configuration to `pyproject.toml`
Configure `pytest-cov` and the base coverage engine inside your `pyproject.toml` file to track branch-level path coverage, skip execution plumbing files, and enforce quality gates.

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
# Automatically measure coverage on the backend source app folder during runs
addopts = "--cov=app --cov-report=term-missing --cov-report=html:htmlcov"

[tool.coverage.run]
branch = true # Enable conditional branch coverage execution analysis
omit = [
    "app/main.py",          # Application entry point setup
    "app/config/*",         # Environment variable schemas
    "tests/*"               # Do not calculate coverage over test code itself
]

[tool.coverage.report]
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "raise NotImplementedError"
]
```

### Step 2: Isolation Execution Command & Quality Gates
When targeting unit-only code coverage calculations in localized workflows or CI steps, enforce an execution threshold constraint using `--cov-fail-under`.

```bash
# Execute only unit tests, display missing lines, and fail if total coverage falls under 90%
pytest tests/unit --cov=app/core --cov-fail-under=90
```

---

## 6. Instructions

When implementing or editing tests based on this document, comply with the following instructions:

1. **Do not create real API connections** unless explicitly inside the `smoke/` directory.
2. **Always ensure async dependencies are properly resolved** using `await` syntax within fixtures or test blocks when dealing with database engines, HTTP clients, or repository layers.
3. **Keep tests isolated.** Do not let state or variables from one test affect subsequent executions. Wrap all database operations in transaction rollbacks.
4. **Follow the structural layout precisely.** Place domain-specific test code into its correct designated category (`unit/`, `integration/`, `api/`, `smoke/`, `scale/`).
5. **Maintain and run test code against coverage.** When creating new domain core features or altering components like the Smart Ripple Engine, immediately write matching test paths to satisfy the branch coverage parameters without dropping beneath the designated fail-under margins.
