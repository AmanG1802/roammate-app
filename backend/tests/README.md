# Backend Test Suite

All backend tests live here — `backend/tests/` is the single home for anything that exercises FastAPI routes, SQLAlchemy models, or backend services.

**Status:** 482 + ~55 new brainstorm/LLM tests, all passing.

---

## Layout

```
backend/tests/
├── conftest.py                         # shared fixtures (SQLite in-memory, auth headers, helpers)
├── api/                                # HTTP-level integration tests (hit the ASGI app)
│   ├── test_users.py                   (12)
│   ├── test_trips.py                   (19)
│   ├── test_trip_members.py            (24)
│   ├── test_trip_days.py               (18)
│   ├── test_idea_bin_api.py            (19)
│   ├── test_brainstorm_api.py          (32) ← NEW
│   ├── test_llm_plan_trip.py           (5)  ← NEW
│   ├── test_events.py                  (21)
│   ├── test_ripple_api.py              (7)
│   ├── test_quick_add_api.py           (3)
│   ├── test_dashboard.py               (38)
│   ├── test_groups.py                  (65)
│   ├── test_group_library.py           (21)
│   ├── test_ideas_tags_copy.py         (22)
│   ├── test_votes.py                   (35)
│   └── test_notifications.py           (26)
├── services/                           # service-layer unit tests
│   ├── test_idea_bin_service.py        (12)
│   ├── test_llm_client.py             (5)  ← NEW
│   ├── test_ripple_engine.py           (8)
│   ├── test_quick_add_service.py       (5)
│   ├── test_nlp_service.py             (3)
│   ├── test_google_maps_service.py     (4)
│   ├── test_notification_service.py    (10)
│   └── test_roles.py                   (9)
├── core/                               # pure unit tests
│   ├── test_security.py                (6)
│   └── test_deps.py                    (3)
├── cross/                              # multi-service / multi-entity integration
│   ├── test_trip_lifecycle.py          (4)
│   ├── test_vote_transfer.py           (19)
│   ├── test_brainstorm_lifecycle.py    (8)  ← NEW
│   ├── test_group_trip_lifecycle.py    (5)
│   ├── test_notification_fanout.py     (21) ← UPDATED (+3 brainstorm promotion)
│   └── test_ripple_gating.py           (4)
└── schemas/                            # pydantic validation
    ├── test_event_schema.py            (14)
    ├── test_brainstorm_schema.py       (5)  ← NEW
    ├── test_votes_schema.py            (14)
    ├── test_library_schema.py          (7)
    └── test_group_schema.py            (7)
```

---

# What's Tested Where

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

- Register: shape + no password leak, duplicate email (400), invalid email (422), missing fields (422)
- Login: bearer token happy path, unknown email (401), wrong password (401)
- `/me`: happy path, missing/malformed/expired token (401), token for deleted user (401)

### `api/test_trips.py` — `/api/trips/*`

**CRUD:** create (basic / with start_date / without / end-before-start 422), list excludes invited, get (member / non-member 403), patch name (admin / non-admin 403 / non-member 403 / end-before-start 422), delete (admin cascade / non-admin 403), all routes require auth (401).

**Date-shift cascade:** forward, backward, events lock-step, same-date noop.

### `api/test_trip_members.py` — invitations & membership

**Invite:** admin ok, non-admin/non-member 403, unknown email 404, duplicate / already-invited 409, invalid role 422, default role `view_only`.

**Pending / Accept / Decline:** pending list shape, empty, accept (happy / nonexistent / foreign / already-accepted 404), decline (204).

**Members:** list (member / non-member 403), role update (admin / non-admin 403 / invalid 422), remove (happy / non-admin 403 / admin-self-remove 400 / nonexistent 404).

### `api/test_trip_days.py` — `/api/trips/{id}/days/*`

Ordered GET, non-member 403, add-day increments number, duplicate date 409, non-admin 403, first-day when no start-date, delete with action=bin (events→bin + time_hint), delete with action=delete, left-shift subsequent day_numbers + event dates, nonexistent 404, non-admin 403.

**`_sync_trip_end_date`:** create-with-start-date auto-sets end_date, add-day increments end_date, add-three-days arithmetic, delete-day decrements end_date, start_date change re-syncs end_date, trip-without-start-date doesn't crash on add-day.

### `api/test_idea_bin_api.py` — `/api/trips/{id}/ideas` + `/ingest`

**Ingest:** success, added_by first-name split, comma/newline splitters, empty, whitespace-only filtered, GMaps failure fallback, source_url persisted, non-member 403.

**Idea CRUD:** get (member / non-member 403), patch title + time_hint (member / non-member 403 / wrong trip 404), delete (happy / nonexistent 404).

**Cross-service:** `test_ingest_then_idea_appears_in_attached_group_library` — ingested idea surfaces in the library of an attached group.

**Batch vote data:** `GET /trips/{id}/ideas` returns `up`, `down`, `my_vote` per idea; `my_vote` is caller-specific (multi-user); empty bin returns `[]`.

### `api/test_brainstorm_api.py` — `/api/trips/{id}/brainstorm/*` ← NEW

**Chat:**
- `test_chat_returns_assistant_message` — POST chat appends user+assistant messages, returns `assistant_message` + `history`.
- `test_chat_persists_messages` — after chat, GET messages returns persisted user + assistant rows.
- `test_chat_multi_turn_history_grows` — second chat call returns all 4 messages (2 user + 2 assistant).
- `test_chat_non_member_403` — non-member cannot chat.
- `test_chat_requires_auth_401` — no token → 401.

**Extract:**
- `test_extract_creates_brainstorm_items` — POST extract populates items with all Google-Maps fields from fallback.
- `test_extract_items_have_added_by_ai` — extracted items' `added_by` = "AI".
- `test_extract_non_member_403` — non-member cannot extract.

**Bulk insert:**
- `test_bulk_insert_seeds_bin` — POST bulk with items list → items appear in GET items.
- `test_bulk_insert_non_member_403` — non-member cannot bulk-insert.

**List items:**
- `test_list_items_returns_own_only` — Alice sees her items; Bob (same trip) sees empty bin.
- `test_list_items_non_member_403` — non-member cannot list.

**List messages:**
- `test_list_messages_returns_own_only` — Alice sees her chat; Bob sees empty history.
- `test_list_messages_non_member_403` — non-member cannot list messages.

**Delete item:**
- `test_delete_item_happy` — owner can delete own item → 204.
- `test_delete_item_nonexistent_404` — deleting non-existent → 404.
- `test_delete_other_users_item_404` — Bob cannot delete Alice's item (scoped as 404, not 403).

**Clear all items:**
- `test_clear_items_deletes_all_for_user` — DELETE /items clears caller's bin, leaves other user's items.

**Promote:**
- `test_promote_all_moves_to_idea_bin` — promote with `item_ids=null` moves all items to idea bin + brainstorm empties.
- `test_promote_subset` — promote with specific `item_ids` moves only those; rest remain.
- `test_promote_full_field_copy` — every field on the promoted IdeaBinItem matches the source BrainstormBinItem (description, category, place_id, lat, lng, address, photo_url, rating, price_level, types, opening_hours, phone, website, time_hint, time_category, url_source).
- `test_promote_added_by_is_promoter_not_ai` — `added_by` on the IdeaBinItem = promoter's first name ("Alice"), not "AI".
- `test_promote_empty_ids_returns_empty` — `item_ids=[]` returns `[]` without error.
- `test_promote_nonexistent_ids_404` — requesting IDs that don't exist in caller's scope → 404.
- `test_promote_other_users_item_404` — Bob cannot promote Alice's brainstorm item.
- `test_promote_non_member_403` — non-member cannot promote.
- `test_promote_time_category_populates_time_hint` — item with `time_category="morning"` and no `time_hint` gets `time_hint="10:00 AM"` on promotion.

**Role gating:**
- `test_view_only_can_promote` — view_only member can promote from their own brainstorm.
- `test_view_with_vote_can_promote` — view_with_vote member can promote.

**Voting after promotion:**
- `test_vote_works_on_promoted_idea` — a freshly promoted IdeaBinItem is immediately votable.

### `api/test_llm_plan_trip.py` — `/api/llm/plan-trip` ← NEW

- `test_plan_trip_returns_preview` — POST with any prompt returns `{trip_name, start_date, duration_days, items}` from fallback.
- `test_plan_trip_items_have_full_fields` — each item has title, description, category, place_id, lat, lng, address, photo_url, rating, price_level, types, opening_hours.
- `test_plan_trip_item_count` — fallback returns exactly 10 items.
- `test_plan_trip_requires_auth_401` — no token → 401.
- `test_plan_trip_missing_prompt_422` — empty body → 422.

### `api/test_events.py` — `/api/events/*`

**CRUD:** create (happy / non-member 403 / missing fields 422 / tz-strip), list (by trip / non-member 403 / missing trip_id 422), patch (happy / non-member 403 / nonexistent 404), delete (happy / non-member 403 / nonexistent 404).

**Move-to-bin:** preserves place_id/lat/lng/added_by/time_hint, no-start-time → `time_hint=None`, non-member 403, nonexistent 404.

**Batch vote data:** `GET /events/` returns `up`, `down`, `my_vote` per event; `my_vote` is caller-specific (multi-user); no-votes returns zeros; `PATCH /events/{id}` response includes vote tallies.

### `api/test_ripple_api.py` — `/api/events/ripple/{trip_id}`

Shifts future events, non-member 403, missing delta 422, tz-strip on `start_from_time`, trip isolation, **parametrized non-admin 403** (view_only / view_with_vote).

### `api/test_quick_add_api.py` — `/api/events/quick-add/{trip_id}`

Success (NLP + GMaps mocked), non-member 403, NLP failure → 500.

### `api/test_dashboard.py` — `/api/dashboard/today`

**Auth / shape:** requires auth (401), top-level `{pages, default_index}` always present.

**State classification:** empty state, pre_trip / in_trip / post_trip single-trip, `end_date=None` falls back to `end=start`, trip with no start_date skipped, ending-today and starting-today both active, ended-yesterday is past.

**`in_trip` event enrichment:** today-only filter, order by start_time nulls-last, `is_ongoing` when now between start/end, `is_next` on first future event only, `day_number` from TripDays (or date-delta fallback), `total_days` from end-start, `client_now` override (ISO / Z-suffix / invalid falls back).

**`total_days` / `day_number` sync:** total_days updates after adding a day, total_days updates after deleting a day, editing start_date earlier keeps trip active with correct day_number.

**Ongoing + Up Next coexistence:** ongoing and next flags coexist correctly, past event gets neither flag, gap between events shows only up-next (no ongoing), all-past events get no flags, event without end_time is never ongoing, 6AM `client_now` skips 2AM event and picks 2PM as up-next (timezone regression).

**Multi-trip / isolation:** invited-but-not-accepted excluded, removed member loses trip, overlapping actives → soonest-start kept, default_index points at active when present, closer-upcoming default, zero-when-only-upcoming, past cap=2, upcoming cap=3, page ordering past→active→upcoming, closer-past default, per-user isolation.

### `api/test_groups.py` — `/api/groups/*`

**Create:** requires auth (401), empty/whitespace name rejected (422), strip whitespace, owner gets admin membership, `group_created` self-notification.

**Read:** detail by member (my_role), not-found (404), invited-but-not-accepted 403, list counts `member_count` + `trip_count`, isolation.

**Update:** patch name (admin / non-admin 403 / non-member 403 / empty noop / 404).

**Delete:** admin ok, non-admin 403, removes all members (including invited), nullifies `notifications.group_id`, nonexistent 404.

**Invitations:** admin ok, non-admin 403, unknown email 404, already-member 409, invalid role 422, default role `member`, pending-list shape (group + inviter), pending-empty, accept (happy / nonexistent / foreign / already-accepted 404), decline (happy / nonexistent 404), accept fan-out (self vs peers).

**Members list:** by member, non-member 403, includes invited + accepted.

**Role changes:** member→admin, non-admin 403, invalid 422, nonexistent member 404, cross-group 404.

**Remove member:** admin ok, non-admin 403, admin-self 400, nonexistent 404, fan-out to target + remaining.

**Trip attach/detach:** idempotent when already attached, non-group-admin 403, nonexistent trip 404, attach fan-out, detach by non-admin 403, detach when not attached 404, detach preserves trip data.

**Auth sweep:** parametrized 401 across all routes.

### `api/test_group_library.py` — `/api/groups/{id}/ideas`, `/tags`

**Aggregation:** across multiple trips, excludes unattached trips, non-member 403, empty group returns empty, unknown group 403.

**Query params:** case-insensitive search, no-match empty, filter by `trip_id`, filter by trip_id not in group (empty), combined q+tag, sort recent (id desc), sort title (lowercase key), sort top (score tie → higher `up`), unknown sort → recent.

**Row fields:** `tags`, `up`, `down`, `my_vote` all present; `my_vote` is per-caller.

**Tag summary:** empty when no ideas, sorted by count desc, non-member 403, excludes tags from detached trips.

### `api/test_ideas_tags_copy.py` — `/api/ideas/{id}/tags`, `/copy`

**Tags CRUD:** get empty, get non-member 403, get nonexistent 404, set strips/lowercases, drops empty strings, dedupes case-insensitive, view_only 403, view_with_vote 200, non-member 403, nonexistent idea 404, empty list clears.

**Copy across trips:** preserves `place_id`/lat/lng/url_source/time_hint/added_by/`origin_idea_id`/tags, copy-of-copy keeps original origin (sticky through chains — verified via group library `LibraryIdeaOut`), requires membership on source (403), same-trip duplicates, nonexistent idea 404, nonexistent target trip 403, no-tags-on-source copies zero tags.

### `api/test_votes.py` — `/api/ideas/{id}/vote`, `/events/{id}/vote`, voters

**Tally:** non-member 403, nonexistent idea/event 404, multi-user state (up/down/none).

**Vote edits:** admin can vote, view_only blocked (403), view_with_vote allowed, view_only reads tally, zero removes vote, idempotent same-value, up→down flip, `my_vote` reflects caller not latest voter, zero when no vote exists (no-op, no 404).

**Auth:** requires auth (401), vote on idea not in my trip (403).

**Voter lists:** idea voters split up/down, unknown-name → "Unknown", view_only can read, non-member 403, nonexistent 404; same for event voters.

**Voter list edge cases:** empty voters when no votes (idea + event), voter list updates after vote removal (value=0), event voters present after transfer from idea via `source_idea_id`.

**Invalid input:** missing field 422, non-int 422, parametrized out-of-range (2, -2, 10, 1.5, `"up"`) → 422.

### `api/test_notifications.py` — `/api/notifications/*`

**List:** requires auth 401, ordered by `created_at` desc, `limit` caps results, `limit=0`/`limit=101` → 422, `before_id` pagination, actor summary when `actor_id` set, actor null when system-emitted, `payload` defaults to `{}` when null, empty list for new user.

**Unread count:** requires auth 401, ignores read rows, only counts own user, decrements on mark-read, zeroes on mark-all-read.

**Mark-read:** nonexistent 404, another user's row 404, idempotent (preserves `read_at`), sets `read_at`.

**Mark-all-read:** empty is ok, leaves other users' rows alone.

**Fan-out:** trip-create self-notification, invite emits to invitee, per-user isolation.

---

## `services/` — service-layer unit tests

### `services/test_llm_client.py` — `llm_client.chat / extract_items / plan_trip` ← NEW

All tests run with `LLM_ENABLED=False` (the default).

- `test_chat_returns_fallback_string` — `chat()` returns the deterministic Bangkok fallback reply.
- `test_extract_items_returns_bangkok_list` — `extract_items()` returns a list of 10 dicts, each with `title` key.
- `test_extract_items_full_fields` — every item in the fallback has all Google-Maps fields populated (description, category, place_id, lat, lng, address, photo_url, rating, price_level, types, opening_hours).
- `test_plan_trip_returns_fallback` — `plan_trip()` returns `trip_name="Thailand Getaway"`, `duration_days=3`, `items` list of 10.
- `test_plan_trip_items_are_fresh_copies` — mutating the returned items does not alter the module-level `_BANGKOK_FALLBACK_ITEMS`.

### `services/test_idea_bin_service.py`

**Regex helpers (pure):** `extract_time_hint` (parametrized: `2pm`, `14:00`, `8:30 pm`, no-time), `strip_time_hint` (removes / no-change / 24h).

**Ingestion (real SQLite):** creates items with place, falls back when no place, handles Google exception, splits commas/newlines, empty returns empty.

### `services/test_ripple_engine.py`

Shifts future events, skips past events, skips locked, skips `start=None` (regression), preserves `end_time=None`, negative delta, zero-delta noop, ordered by `start_time`.

### `services/test_quick_add_service.py`

NLP time honored, default duration 60min, no start_iso uses today 10am, GMaps exception fallback (regression), default event_type `"activity"`.

### `services/test_nlp_service.py`

No API key → stub, with key calls mocked `AsyncOpenAI`, client is lazy.

### `services/test_google_maps_service.py`

No key → Rome mock, with-key ok returns first candidate, non-ok returns `None`, no candidates returns `None`.

### `services/test_notification_service.py`

`emit()` dedupes recipients, drops `None`, empty-list noop, persists `payload`/`actor`/`trip_id`/`group_id`, disabled type is silent noop (via `monkeypatch.setitem(NotificationType.ENABLED, ..., False)`), unknown type defaults true. `trip_member_ids` accepted-only default, includes-invited flag, `exclude_user` filter. `all_trip_member_ids` includes caller.

### `services/test_roles.py`

`get_trip_member` returns `None` for non-member / invited status. `require_trip_member` 403 for non-member. `require_trip_admin` accepts admin / 403 for view_only / 403 for view_with_vote. `require_vote_role` parametrized: admin + view_with_vote accepted / view_only 403.

---

## `core/` — core library unit tests

### `core/test_security.py`

Hash/verify roundtrip, wrong password, different salts, token contains sub+exp, custom expiry, wrong-secret fails.

### `core/test_deps.py` — `get_current_user` via `/api/users/me`

Wrong signature 401, missing sub 401, wrong algorithm (HS512 vs HS256) 401.

---

## `cross/` — multi-service integration

### `cross/test_trip_lifecycle.py`

Full trip lifecycle (register → create → invite → accept → add-day → ingest → event → ripple → remove → delete), view_only cannot mutate, IDOR across trips, ripple-then-day-delete bin reflects shifted time.

### `cross/test_vote_transfer.py`

**Idea→event:** transfer via `source_idea_id` preserves per-user up/down values, does NOT delete source IdeaVote rows (current behavior), event created without `source_idea_id` has no event votes.

**Event→idea (move-to-bin):** preserves both up/down voters, no votes → clean transfer, bin→timeline→bin roundtrip keeps tally, transferred idea shows up in group library with tally.

**Response inline votes:** `create_event` response includes transferred vote tallies; zero votes when no `source_idea_id`; `move-to-bin` response includes `up`, `down`, `my_vote`; `my_vote` reflects the calling user.

**Day-delete vote transfer:** `items_action=bin` preserves single-user vote, preserves multi-user up+down votes; `items_action=delete` does not create idea votes; zero-vote event produces clean idea; day-delete→bin roundtrip preserves votes on resulting idea.

**Extended roundtrips:** timeline→bin roundtrip preserves votes on the resulting idea (event→idea leg verified; the final re-creation step hits a known SQLite limitation with orphaned EventVote rows — see infrastructure gaps).

### `cross/test_brainstorm_lifecycle.py` — brainstorm E2E flows ← NEW

- `test_chat_extract_promote_e2e` — full flow: create trip → chat → extract → items appear → promote all → idea bin has items, brainstorm empties.
- `test_dashboard_plan_create_seed_e2e` — plan-trip → create trip → bulk-insert → items in brainstorm → promote → items in idea bin.
- `test_promote_then_vote` — promote items → vote on the promoted idea → tally correct.
- `test_non_admin_promote_visible_in_shared_idea_bin` — non-admin promotes from their brainstorm; promoted idea is visible in the shared Idea Bin to all trip members.
- `test_two_users_independent_brainstorm` — Alice and Bob on same trip: each chats, extracts, and promotes independently. Alice's promotions are visible in shared idea bin to Bob; Bob's brainstorm is never leaked to Alice.
- `test_promoted_idea_appears_in_group_library` — promote items on a trip attached to a group → items surface in group library.
- `test_trip_delete_cascades_brainstorm` — deleting a trip removes all brainstorm items and messages.
- `test_promote_time_category_default_carries_to_idea` — item with `time_category` but no `time_hint` gains the default time hint on promotion.

### `cross/test_group_trip_lifecycle.py`

Full E2E (create → invite → accept → attach → library → role change → detach → remove → delete), detach removes ideas from library, trip-delete propagates, IDOR across groups, removed member loses read access.

### `cross/test_notification_fanout.py`

**Trip:** `trip_created` self-only, `trip_renamed` / `date_changed` / `deleted` fan-out, invite/accept/decline chains with self vs peer payload shapes, `member_role_changed` to target, `member_removed` two-shape.

**Event:** `event_added` excludes creator, `event_moved` fires only on time change (not title-only), `event_removed` on delete, `event_removed` with `moved_to_bin=True` flag on move-to-bin, `ripple_fired` to affected members.

**Brainstorm (NEW):**
- `test_brainstorm_promote_notifies_peers_not_promoter` — on promote, Bob (peer) gets `brainstorm_promoted` notification; Alice (promoter) does not.
- `test_brainstorm_promote_notification_payload` — payload contains `trip_name`, `count`, `titles`, `actor_name`.
- `test_brainstorm_promote_no_notification_when_solo` — promote on a solo trip (no other members) emits zero notifications.

**Group:** `group_created` self-only, `group_invite_received` to invitee, group-attach to peers not actor.

**Negative:** disabled type suppresses emission (monkeypatch `ENABLED`).

### `cross/test_ripple_gating.py`

Admin allowed, parametrized non-admin 403 (view_only / view_with_vote), non-member 403.

> Note: `api/test_ripple_api.py` also asserts the non-admin 403 inline as a cross-service addition; the `cross/` file is the consolidated reference.

---

## `schemas/` — pydantic validation

### `schemas/test_brainstorm_schema.py` — brainstorm Pydantic schemas ← NEW

- `test_brainstorm_item_base_minimal` — only `title` required; all other fields default to `None`.
- `test_brainstorm_item_out_from_attributes` — `BrainstormItemOut` validates from ORM-like dict with `from_attributes=True`.
- `test_brainstorm_promote_request_none_means_all` — `BrainstormPromoteRequest()` defaults `item_ids` to `None`.
- `test_plan_trip_response_shape` — `PlanTripResponse` accepts the full fallback structure.
- `test_brainstorm_chat_request_requires_message` — empty body → validation error.

### `schemas/test_event_schema.py`

`_strip_tz` helper (none / UTC / non-UTC with offset), EventCreate / EventUpdate / RippleRequest strip tz. Trip validators: end-before-start rejected (create + update), equal dates ok, name-only ok. Request shape: invite default role `view_only`, ingest requires `text`. `Event` schema defaults `up=0, down=0, my_vote=0`. `IdeaBinItem` schema defaults `up=0, down=0, my_vote=0`.

### `schemas/test_votes_schema.py`

`VoteRequest` parametrized -1/0/1 accepted, out-of-range (2, -2, `None`) rejected, str→int coercion (pydantic default). `VoteTally` defaults zero. `VoterInfo` requires `name`, accepts name. `VoterList` defaults to empty lists. `TodayEvent` defaults `is_ongoing=False` and `is_next=False`, accepts `is_ongoing=True`.

### `schemas/test_library_schema.py`

`TagList` lowercases + strips, dedupes case-insensitive, filters empty/whitespace, preserves first-occurrence order, empty list ok. `CopyIdeaRequest` requires `target_trip_id` (422), accepts int.

### `schemas/test_group_schema.py`

`GroupCreate` requires name, accepts name. `GroupUpdate.name` optional. `GroupInviteRequest` default role `member`, requires email, rejects invalid email. `GroupRoleUpdateRequest` accepts any string (role validation is endpoint-level against `GROUP_ROLES`, not schema — regression anchor).

---

# Design notes

## Why additive Stage-2 features didn't break Stage-1 tests

Stage-1 tests assert on endpoint *contracts* (HTTP response + primary entity state). Stage-2 features — notifications, vote transfer, group-library visibility, cascade cleanup — are all additive side effects on *other* tables. The tests never queried those tables, so nothing broke:

- **Notifications** — emitted to a separate `notifications` table; Stage-1 tests don't query it.
- **Vote transfer** — only triggers when `source_idea_id` is set or via `move_to_bin`; Stage-1 event tests don't set it.
- **Group-library visibility** — library filter requires `Trip.group_id`; Stage-1 tests never attach trips to groups.
- **Role gating** — existing tests cover non-member 403 but not view_only / view_with_vote boundary; the new parametrized gating test fills this.

The *contract* tests remain valid; the *cross-service* files (`cross/`, `test_notification_fanout.py`, `test_vote_transfer.py`) are where the additive behavior is pinned.

## Why brainstorm tests don't break existing tests

Brainstorm endpoints live under `/api/trips/{id}/brainstorm/*` and write to two new tables (`brainstorm_bin_item`, `brainstorm_message`). Existing tests never hit these routes or query these tables. The promotion endpoint creates `IdeaBinItem` rows — the same entity tested by `test_idea_bin_api.py` — but promotion is exercised only in the new brainstorm test files and `cross/test_brainstorm_lifecycle.py`. The `BRAINSTORM_PROMOTED` notification type is additive to the `NotificationType.ENABLED` dict; existing notification tests don't query it. `LLM_ENABLED=False` means the `llm_client` module never attempts real network calls.

## Known infrastructure gaps (not test gaps)

- **Cascade on idea/event delete** — `IdeaTag`, `IdeaVote`, and `EventVote` all declare `ondelete="CASCADE"` at the FK level. SQLite ignores this unless `PRAGMA foreign_keys=ON` is set per-connection, which conftest does not do. Enabling it risks breaking Stage-1 tests that tolerate orphans. Cascade behavior is therefore not asserted in the test suite; it is enforced in Postgres (production) at the DB level. Consequence: when an Event is deleted in tests, orphaned `EventVote` rows survive, and SQLite may reuse the deleted event's ROWID for a new insert, causing a UNIQUE constraint collision on `(event_id, user_id)`. Roundtrip tests that delete an event and re-create one from the same votes work around this by verifying the intermediate idea instead.
- **Pagination** on unbounded list endpoints (`GET /events/`, `/ideas`, `/members`) — currently not tested because the endpoints don't paginate.

## Explicit non-goals

- Unicode / very long group names, tag names, idea titles
- Concurrent same-user vote (last-write-wins is current behavior)
- Removing last group admin — prevented by 400; revisit if admin handoff is added
- Notification `payload` shape drift — we don't pin exact keys per type beyond `trip_name` / `self`; add a schema only when the frontend breaks on a missing key
- `before_id` pagination with tombstones
- Large library (>1000 ideas) performance
- `freezegun`-based assertion for `quick_add`'s 10 AM fallback
- CORS smoke test
- Large `delta_minutes` / datetime overflow on ripple

---

# Running

```bash
cd backend
pytest tests/

# one directory
pytest tests/api -v

# single file
pytest tests/api/test_trips.py -v

# single test
pytest tests/api/test_trips.py::test_create_trip_basic -v
```

Configuration lives in `tests/pytest.ini` (`asyncio_mode = auto`). No `@pytest.mark.asyncio` needed on individual tests.

## Environment

- `OPENAI_API_KEY` unset or stub → NLP service returns stub
- `GOOGLE_MAPS_API_KEY` unset → GMaps service falls back to Rome mock
- `SECRET_KEY` — uses default from `app.core.config` if not set
- `LLM_ENABLED` — defaults to `False`; all brainstorm/LLM tests exercise the deterministic Bangkok fallback path

## Conventions

- HTTP tests use the `client` + `auth_headers` / `second_auth_headers` / `third_auth_headers` fixtures from `conftest.py`.
- Service tests prefer real in-memory SQLite via `db_session` when ORM behavior matters; mock only outbound I/O (OpenAI, Google Maps).
- Every new endpoint gets: happy path, auth required, authz boundary (non-member/non-admin), not-found, validation error.
- New Stage-2 features additionally get a cross-service test in `cross/` whenever they emit notifications, transfer state across entities, or surface data through a different endpoint (e.g., group library).

---

# Not Yet Written (future scope)

Documented but not yet implemented — these are cases where the current behavior is surprising, out of scope for this pass, or needs a product decision:

- Pagination on list endpoints (`GET /events/`, `/ideas`, `/members`) — currently unbounded
- Concurrency: two admins editing the same trip simultaneously
- Large `delta_minutes` / datetime overflow on ripple
- Unicode + very long strings in titles, group names, tags
- CORS smoke test
- `freezegun`-based `datetime.now()` assertion for `quick_add`'s 10 AM fallback
- Removing last trip/group admin leaves orphaned entity — product decision
- `PATCH /events/{id}` cannot change `trip_id` — schema-level assertion
- Empty-string `current_user.name` falls back to `added_by=None` on ingest — edge case
- Cascade on idea delete (`IdeaTag`, `IdeaVote`) — requires `PRAGMA foreign_keys=ON` in conftest; production (Postgres) enforces it at the DB layer
- `before_id` notification pagination where rows have been deleted
- Large group library (>1000 ideas) performance
- Notification `payload` shape drift — pin exact keys per type once frontend contracts stabilize
- `test_date_shift_cascade.py`, `test_day_delete_cascade.py`, `test_bin_to_timeline_roundtrip.py` under `cross/` — currently covered inline in `api/test_trips.py`, `api/test_trip_days.py`, and `cross/test_trip_lifecycle.py`; split out if/when they grow
- Real LLM integration tests (`LLM_ENABLED=True`) — requires API key; covered by manual QA
- Brainstorm bin pagination — currently unbounded like other list endpoints
- Concurrent brainstorm promotion by two users — last-write-wins
- Chat message size limits / adversarial input to LLM facade
