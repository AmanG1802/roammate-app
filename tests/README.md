g# Roammate Test Suite

## Structure

```
tests/
├── api/                   # API integration tests (pytest-asyncio, SQLite in-memory)
│   ├── conftest.py        # Shared fixtures: async client, test DB, auth helpers
│   ├── pytest.ini         # asyncio_mode = auto
│   ├── test_auth.py       # POST /register, POST /login, GET /me
│   ├── test_trips.py      # GET/POST /trips/, GET /trips/{id}, GET ideas, POST ingest
│   └── test_events.py     # GET /events/, POST /events/ripple, POST /events/quick-add
└── e2e/                   # Playwright end-to-end flows (TODO)
```

Backend unit tests live in `backend/tests/`:
- `test_ripple_engine.py` — Ripple Engine time-shifting logic
- `test_idea_bin.py`      — Idea Bin text ingestion service

Frontend tests live in `frontend/tests/`:
- `store.test.ts`         — Zustand store state management
- `IdeaBin.test.tsx`      — IdeaBin component interactions

## Running Tests

### API Integration Tests (no Docker needed)
```bash
# From repo root — uses SQLite in-memory, no Postgres required
PYTHONPATH=backend OPENAI_API_KEY=test \
  python -m pytest tests/api/ -v
```

### Backend Unit Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

### All Tests (CI)
```bash
# API tests
PYTHONPATH=backend OPENAI_API_KEY=test python -m pytest tests/api/ -v

# Backend unit tests
cd backend && pytest && cd ..

# Frontend unit tests
cd frontend && npm test && cd ..
```

## Test Design Notes

- **API tests** use `aiosqlite` (in-memory SQLite) via dependency override — no Postgres required.
  Each test gets a fresh database via the `setup_db` autouse fixture.
- **Auth fixtures** (`auth_headers`, `second_auth_headers`) register and log in real users so
  permission boundary tests are fully end-to-end through the auth stack.
- `OPENAI_API_KEY=test` is a stub — the NLP service lazy-initialises its client and falls back
  to a mock response when no real key is set.
