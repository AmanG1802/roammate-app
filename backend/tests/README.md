# Backend Test Suite

All backend tests live here — `backend/tests/` is the single home for anything that exercises FastAPI routes, SQLAlchemy models, or backend services.

## Layout (target)

```
backend/tests/
├── conftest.py                         # shared fixtures (SQLite in-memory, auth_headers, second_auth_headers)
├── api/                                # HTTP-level integration tests (hit the ASGI app)
│   ├── test_users.py                   # /api/users/*
│   ├── test_trips.py                   # /api/trips/*
│   ├── test_trip_members.py            # /api/trips/{id}/members, invitations
│   ├── test_trip_days.py               # /api/trips/{id}/days/*
│   ├── test_idea_bin_api.py            # /api/trips/{id}/ideas, /ingest
│   ├── test_events.py                  # /api/events/*
│   ├── test_ripple_api.py              # /api/events/ripple/{trip_id}
│   └── test_quick_add_api.py           # /api/events/quick-add/{trip_id}
├── services/                           # unit tests for service-layer logic (mocked DB where useful)
│   ├── test_idea_bin_service.py
│   ├── test_ripple_engine.py
│   ├── test_quick_add_service.py
│   ├── test_nlp_service.py
│   └── test_google_maps_service.py
├── core/                               # pure unit tests
│   ├── test_security.py                # password hash, JWT create/decode
│   └── test_deps.py                    # get_current_user token flow
├── cross/                              # multi-service / multi-entity integration
│   ├── test_trip_lifecycle.py          # create→invite→accept→plan→delete
│   ├── test_date_shift_cascade.py      # trip start_date change → days → events
│   ├── test_day_delete_cascade.py      # day delete → events to bin vs hard-delete
│   └── test_bin_to_timeline_roundtrip.py
└── schemas/                            # pydantic validation
    └── test_event_schema.py            # tz-strip validator, etc.
```

---

# What's Tested Where

All tests listed below are implemented and passing (164 passed). Each bullet is one test function (or parametrized group).

## `conftest.py`

Shared fixtures and helpers (no tests):

- `setup_db` (autouse) — per-test in-memory SQLite create/drop
- `client` — async HTTP client with `get_db` dependency override
- `db_session` — direct DB session for service/unit tests
- `auth_headers` (Alice), `second_auth_headers` (Bob), `third_auth_headers` (Carol)
- Helpers: `create_trip()`, `invite_and_accept()`

---

## `api/` — HTTP integration tests

### `api/test_users.py` — `/api/users/*`

- `test_register_returns_user_out` — shape, no `hashed_password` leak
- `test_register_duplicate_email` — 400
- `test_register_invalid_email` — 422 (Pydantic `EmailStr`)
- `test_register_missing_fields` — 422
- `test_login_returns_bearer_token`
- `test_login_unknown_email` — 401
- `test_login_wrong_password` — 401
- `test_me_returns_current_user`
- `test_me_requires_auth` — 401
- `test_me_malformed_token` — 401
- `test_me_expired_token` — 401 (short-lived token)
- `test_me_token_for_deleted_user` — 401

### `api/test_trips.py` — `/api/trips/*`

**Basic CRUD:**

- `test_create_trip_basic`
- `test_create_trip_sets_creator_as_admin`
- `test_create_trip_with_start_date_creates_day1`
- `test_create_trip_without_start_date_has_no_days`
- `test_create_trip_end_before_start_rejected` — 422 (validator)
- `test_get_trips_only_accepted` — excludes `status="invited"`
- `test_get_trip_forbidden_for_non_member` — 403
- `test_get_trip_allows_any_member`
- `test_patch_trip_name_by_admin`
- `test_patch_trip_by_non_admin_forbidden` — 403
- `test_patch_trip_by_non_member_forbidden` — 403
- `test_patch_trip_end_before_start_rejected` — 422

**Date-shift cascade:**

- `test_patch_trip_start_date_forward_shifts_days`
- `test_patch_trip_start_date_backward_shifts_days`
- `test_patch_trip_date_shift_moves_events` — event `day_date` moves in lock-step
- `test_patch_trip_same_start_date_is_noop`

**Delete + auth:**

- `test_delete_trip_by_admin_cascades` — events/ideas/days/members all gone
- `test_delete_trip_by_non_admin_forbidden` — 403
- `test_all_trip_routes_require_auth` — 401 across GET/POST/DELETE

### `api/test_trip_members.py` — invitations & membership

**Invite:**

- `test_admin_can_invite` — creates `status="invited"`
- `test_non_admin_cannot_invite` — 403
- `test_non_member_cannot_invite` — 403
- `test_invite_unknown_email` — 404
- `test_invite_already_member` — 409
- `test_invite_already_invited` — 409
- `test_invite_invalid_role` — 422
- `test_invite_default_role_view_only`

**Pending:**

- `test_pending_invitations` — includes `trip` summary + `inviter`
- `test_pending_empty`

**Accept / decline:**

- `test_accept_invitation`
- `test_accept_nonexistent_invitation` — 404
- `test_accept_foreign_invitation` — 404 (filter by user_id)
- `test_accept_already_accepted` — 404
- `test_decline_invitation` — 204, no longer pending

**Members:**

- `test_get_members_by_member`
- `test_get_members_by_non_member` — 403
- `test_update_member_role`
- `test_update_role_by_non_admin` — 403
- `test_update_role_invalid` — 422
- `test_remove_member` — removed user loses read access
- `test_admin_cannot_remove_self` — 400
- `test_remove_by_non_admin` — 403
- `test_remove_nonexistent_member` — 404

### `api/test_trip_days.py` — `/api/trips/{id}/days/`*

- `test_get_days_ordered` — by date
- `test_get_days_non_member_forbidden` — 403
- `test_add_day_increments_number` — `day_number = max+1`
- `test_add_day_by_non_admin_forbidden` — 403
- `test_add_day_duplicate_date` — 409 (`uq_trip_day`)
- `test_first_day_when_no_start_date` — uses `coalesce(max,0)+1`
- `test_delete_day_items_action_bin` — events → `IdeaBinItem` with time_hint
- `test_delete_day_items_action_delete` — events hard-deleted
- `test_delete_day_left_shifts_subsequent` — day_number + date both shift -1
- `test_delete_day_left_shifts_event_dates` — events on later days follow
- `test_delete_day_nonexistent` — 404
- `test_delete_day_by_non_admin` — 403

### `api/test_idea_bin_api.py` — `/api/trips/{id}/ideas` + `/ingest`

**Ingest:**

- `test_ingest_success`
- `test_ingest_added_by_first_name` — split on whitespace
- `test_ingest_comma_and_newline` — mixed splitters
- `test_ingest_empty` — `[]`
- `test_ingest_whitespace_filtered`
- `test_ingest_google_maps_failure_falls_back` — item still created
- `test_ingest_source_url_persisted`
- `test_ingest_non_member_forbidden` — 403

**Idea CRUD:**

- `test_get_ideas`
- `test_get_ideas_non_member` — 403
- `test_patch_idea_title_and_time_hint`
- `test_patch_idea_non_member` — 403
- `test_patch_idea_wrong_trip` — 404 (trip_id mismatch)
- `test_delete_idea`
- `test_delete_idea_nonexistent` — 404

### `api/test_events.py` — `/api/events/`*

**CRUD:**

- `test_create_event`
- `test_create_event_non_member` — 403
- `test_create_event_missing_fields` — 422
- `test_create_event_strips_tz` — naive datetime stored
- `test_get_events_by_trip`
- `test_get_events_non_member` — 403
- `test_get_events_missing_trip_id` — 422
- `test_patch_event`
- `test_patch_event_non_member` — 403
- `test_patch_event_nonexistent` — 404
- `test_delete_event`
- `test_delete_event_nonexistent` — 404
- `test_delete_event_non_member` — 403

**Move-to-bin:**

- `test_move_to_bin` — preserves place_id/lat/lng/added_by + time_hint
- `test_move_to_bin_no_start_time` — `time_hint=None`
- `test_move_to_bin_non_member` — 403
- `test_move_to_bin_nonexistent` — 404

### `api/test_ripple_api.py` — `/api/events/ripple/{trip_id}`

- `test_ripple_shifts_future_events`
- `test_ripple_non_member` — 403
- `test_ripple_missing_delta` — 422
- `test_ripple_strips_tz_on_start_from_time`
- `test_ripple_isolated_to_trip` — no cross-trip leakage

### `api/test_quick_add_api.py` — `/api/events/quick-add/{trip_id}`

- `test_quick_add_success` — NLP + GMaps both mocked
- `test_quick_add_non_member` — 403
- `test_quick_add_nlp_failure_surfaces_500`

---

## `services/` — service-layer unit tests

### `services/test_idea_bin_service.py`

**Regex helpers (pure):**

- `test_extract_time_hint` (parametrized: `2pm`, `14:00`, `8:30 pm`, no-time)
- `test_strip_time_hint_removes_time`
- `test_strip_time_hint_no_change_if_no_time`
- `test_strip_time_hint_24h`

**Ingestion against real SQLite:**

- `test_ingest_creates_items_with_place`
- `test_ingest_falls_back_when_no_place`
- `test_ingest_handles_google_exception`
- `test_ingest_splits_commas_newlines`
- `test_ingest_empty_returns_empty`

### `services/test_ripple_engine.py`

- `test_shifts_future_events`
- `test_skips_past_events` — `start_time < start_from_time`
- `test_skips_locked` — `is_locked=True`
- `test_skips_events_with_none_start` — regression for bug fix
- `test_handles_none_end_time` — `end_time=None` preserved
- `test_negative_delta` — shifts earlier
- `test_zero_delta_is_noop`
- `test_returns_ordered_by_start_time`

### `services/test_quick_add_service.py`

- `test_quick_add_with_nlp_time` — `start_iso` honored
- `test_quick_add_default_duration` — 60 min fallback
- `test_quick_add_without_start_iso_uses_today_10am`
- `test_quick_add_gmaps_exception_falls_back` — regression for bug fix
- `test_quick_add_default_event_type` — `"activity"`

### `services/test_nlp_service.py`

- `test_no_api_key_returns_stub`
- `test_with_api_key_calls_openai` — mocked `AsyncOpenAI`
- `test_client_is_lazy` — not initialized until needed

### `services/test_google_maps_service.py`

- `test_no_key_returns_mock` — Rome coordinates
- `test_with_key_ok_response` — first candidate returned
- `test_with_key_non_ok_returns_none`
- `test_with_key_no_candidates_returns_none`

---

## `core/` — core library unit tests

### `core/test_security.py`

- `test_hash_verify_roundtrip`
- `test_verify_wrong_password`
- `test_hashes_have_different_salts` — bcrypt salt
- `test_token_contains_sub_and_exp`
- `test_token_custom_expiry`
- `test_token_wrong_secret_fails`

### `core/test_deps.py` — `get_current_user` via `/api/users/me`

- `test_wrong_signature_rejected` — 401
- `test_missing_sub_rejected` — 401
- `test_wrong_algorithm_rejected` — HS512 vs HS256, 401

---

## `cross/` — multi-service integration

### `cross/test_trip_lifecycle.py`

- `test_full_trip_lifecycle` — register → create → invite → accept → add day → ingest → event → ripple → remove → delete
- `test_view_only_cannot_mutate` — view_only role blocked from invite/add-day
- `test_idor_across_trips` — no cross-trip reads or event lookups
- `test_ripple_then_day_delete_bin_reflects_shifted_time` — time_hint reflects post-ripple time

---

## `schemas/` — pydantic validation

### `schemas/test_event_schema.py`

`**_strip_tz` helper:**

- `test_strip_tz_none`
- `test_strip_tz_utc`
- `test_strip_tz_non_utc` — UTC offset applied

**Schema validators:**

- `test_event_create_strips_tz_on_both_times`
- `test_event_update_strips_tz`
- `test_ripple_request_strips_tz`

**Trip validators (end_date ≥ start_date — regression for bug fix):**

- `test_trip_create_rejects_end_before_start`
- `test_trip_create_accepts_equal_dates`
- `test_trip_update_rejects_end_before_start`
- `test_trip_create_only_name_ok`

**Request shape:**

- `test_invite_request_default_role` — `view_only`
- `test_ingest_request_requires_text` — 422 without text

---

# Not Yet Written (future scope)

Documented in the plan but not yet implemented — these are cases where the current behavior is surprising, out of scope for this pass, or needs a product decision:

- Pagination on list endpoints (`GET /events/`, `/ideas`, `/members`) — currently unbounded
- Concurrency: two admins editing same trip simultaneously
- Large `delta_minutes` / datetime overflow on ripple
- Unicode + very long strings in titles
- CORS smoke test
- `freezegun`-based `datetime.now()` assertion for `quick_add`'s 10 AM fallback
- Removing last admin leaves orphaned trip — product decision
- `PATCH /events/{id}` cannot change `trip_id` — schema-level assertion
- Empty-string `current_user.name` falls back to `added_by=None` on ingest — edge case
- `test_date_shift_cascade.py`, `test_day_delete_cascade.py`, `test_bin_to_timeline_roundtrip.py` under `cross/` — currently covered inline in `api/test_trips.py`, `api/test_trip_days.py`, and `cross/test_trip_lifecycle.py`; split out if/when they grow

---

# Running

```bash
cd backend
pytest tests/ -v

# one directory
pytest tests/api -v

# single file
pytest tests/api/test_trips.py -v

# single test
pytest tests/api/test_trips.py::test_create_trip_basic -v
```

Configuration lives in `tests/pytest.ini` (`asyncio_mode = auto`). No `@pytest.mark.asyncio` needed on individual tests.

Environment:

- `OPENAI_API_KEY` unset or stub → NLP service returns stub
- `GOOGLE_MAPS_API_KEY` unset → GMaps service falls back to Rome mock
- `SECRET_KEY` — uses default from `app.core.config` if not set

## Conventions

- HTTP tests use the `client` + `auth_headers` / `second_auth_headers` / `third_auth_headers` fixtures from `conftest.py`.
- Service tests prefer real in-memory SQLite via `db_session` when ORM behavior matters; mock only the outbound I/O (OpenAI, Google Maps).
- Every new endpoint gets: happy path, auth required, authz boundary (non-member/non-admin), not-found, validation error.

