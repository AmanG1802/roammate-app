# Comprehensive Test Suite Plan — `aman/map-integration` (last 7 commits)

## Scope

This plan covers a **section-by-section, feature-by-feature test suite** for the work
landed in commits `12376ab → 1085e0c` on `aman/map-integration`. It enumerates:

1. The features each commit shipped.
2. Tests that already exist (do **not** re-write).
3. **New tests to add** — happy paths, edge cases, cross-feature interaction, and
   cross-entity interaction (User × Trip × Brainstorm × IdeaBin × LLM × Map ×
   Admin × Notification).

Convention used in this doc:
- ✅ = test already implemented in the repo, listed for reference only.
- 🆕 = **new test to add** (the actionable backlog).

Target home directories (existing convention):
- `backend/tests/api/` — endpoint tests with `AsyncClient`.
- `backend/tests/services/` — pure service unit tests.
- `backend/tests/cross/` — multi-feature lifecycles and entity interactions.
- `backend/tests/schemas/` — Pydantic validation only.
- `frontend/__tests__/` (proposed) — Vitest + React Testing Library for the new
  React components (no FE test infra exists today; the FE section below
  doubles as a setup checklist).

---

## Commit-to-feature map

| Commit | Feature area |
|---|---|
| `12376ab` | LLM config + directory restructure (registry, models, services/v1) |
| `0515e14` | Removal of deprecated NLP / QuickAdd; Idea Bin upgrade plan |
| `e1ca37e` | `RoammateServiceV1` — token-efficient pipeline, dedup, fallbacks |
| `a712b9e` | User persona system, profile pages, LLM personalisation |
| `8b172fb` | Google Maps service v1/v2 versioning + route endpoint + brainstorm/llm enrichment refactor |
| `b79052a` | `GOOGLE_MAPS_FETCH_PHOTOS` / `GOOGLE_MAPS_FETCH_RATING` flags |
| `1085e0c` | `/admin` panel, login gate, token + maps usage persistence |

The plan below is grouped by **feature area** rather than commit, because most
test gaps are cross-cutting.

---

## Section 1 — LLM Pipeline (`RoammateServiceV1`, registry, clients, models)

### Files under test
- `backend/app/services/llm/registry.py`
- `backend/app/services/llm/services/v1/roammate_v1.py`
- `backend/app/services/llm/services/v1/prompts/*.txt`
- `backend/app/services/llm/clients/{base,brainstorm_client,concierge_client,dashboard_client}.py`
- `backend/app/services/llm/models/{base,openai_model,claude_model,gemini_model}.py`
- `backend/app/services/llm/{pre_processor,dedup,fallbacks,token_tracker}.py`
- `backend/app/services/llm_client.py` (legacy fallback shim — still imported)

### Existing tests
- ✅ `tests/services/test_llm_client.py` (5 tests) — fallback chat / extract / plan_trip when `LLM_ENABLED=False`.

### 1A — Registry & model selection (🆕 new file: `tests/services/test_llm_registry.py`)
1. 🆕 `test_registry_default_provider` — `LLM_ENABLED=False` returns the legacy
   fallback client without instantiating any provider SDK.
2. 🆕 `test_registry_picks_openai_when_configured` — env vars route to `openai_model`.
3. 🆕 `test_registry_picks_claude_when_configured`.
4. 🆕 `test_registry_picks_gemini_when_configured`.
5. 🆕 `test_registry_unknown_provider_raises` — bad `LLM_PROVIDER` value → 500/`ValueError`.
6. 🆕 `test_registry_missing_api_key_falls_back_to_mock` — mirror Maps pattern.
7. 🆕 `test_registry_caches_singleton` — second call returns same instance.

### 1B — `RoammateServiceV1` envelope parsing (🆕 `tests/services/test_roammate_v1.py`)
The v1 prompts now return `{user_output, map_output}`. Assert the parser tolerates
all observed shapes.
1. 🆕 `test_parse_envelope_happy` — both keys present, items round-tripped.
2. 🆕 `test_parse_envelope_missing_map_output_returns_user_text_only`.
3. 🆕 `test_parse_envelope_missing_user_output_returns_empty_string`.
4. 🆕 `test_parse_envelope_extra_top_level_keys_ignored`.
5. 🆕 `test_parse_envelope_unwrapped_legacy_response_falls_back_gracefully`
   (an old-style flat list is still accepted).
6. 🆕 `test_parse_envelope_invalid_json_triggers_fallback` — `LLM_ENABLED=True`
   path with malformed model output returns the deterministic Bangkok payload.
7. 🆕 `test_pack_trip_context_includes_events_and_role` — baseline.
8. 🆕 `test_pack_trip_context_truncates_long_event_list` — sanity cap.

### 1C — Pre-processor / dedup / fallbacks (🆕 `tests/services/test_llm_dedup.py`, `test_llm_fallbacks.py`, `test_llm_pre_processor.py`)
1. 🆕 `test_dedup_removes_exact_title_duplicates`.
2. 🆕 `test_dedup_removes_case_insensitive_duplicates`.
3. 🆕 `test_dedup_keeps_distinct_place_ids_with_same_title` (e.g. two
   "Starbucks" with different place_ids both kept).
4. 🆕 `test_dedup_against_existing_idea_bin_items_excludes_already_added`.
5. 🆕 `test_dedup_against_brainstorm_bin_excludes_already_brainstormed`.
6. 🆕 `test_pre_processor_strips_whitespace_and_lowercases_categories`.
7. 🆕 `test_pre_processor_drops_items_without_title`.
8. 🆕 `test_fallback_payload_is_a_fresh_copy` — mutating the returned items
   must not mutate the constant (regression for shared-list bugs).

### 1D — Token tracker (🆕 `tests/services/test_token_tracker.py`)
Token tracker now persists to DB via `asyncio.create_task`.
1. 🆕 `test_track_writes_log_line` — captures `roammate.tokens` log record.
2. 🆕 `test_track_persists_token_usage_row` — after `await asyncio.sleep(0)` the
   `token_usage` table has one row with `tokens_in`, `tokens_out`, `tokens_total`,
   `provider`, `model`, `op`, `source`, `cost_usd`.
3. 🆕 `test_track_cost_uses_pricing_table` — gpt-4o-mini in/out → expected USD,
   exact decimal (use `Decimal` comparison, not float).
4. 🆕 `test_track_unknown_model_zero_cost_no_crash`.
5. 🆕 `test_track_user_id_optional` — anonymous tracking writes `user_id=NULL`.
6. 🆕 `test_track_db_error_does_not_break_caller` — patch session factory to
   raise; the caller (e.g. `chat()`) must still return a response.

### 1E — Provider model wrappers (🆕 `tests/services/test_llm_models.py`)
With network mocked via `respx` / `httpx.MockTransport`:
1. 🆕 `test_openai_model_request_shape` — payload matches OpenAI Chat schema.
2. 🆕 `test_claude_model_request_shape` — uses Messages API + `system` separation.
3. 🆕 `test_gemini_model_request_shape`.
4. 🆕 `test_each_model_returns_normalised_completion_dict`
   (`{text, tokens_in, tokens_out, model, provider}`).
5. 🆕 `test_each_model_retries_on_5xx_and_eventually_raises`.
6. 🆕 `test_each_model_no_retry_on_4xx`.

### 1F — Endpoint integration (extend `tests/api/test_brainstorm_api.py`, `test_llm_plan_trip.py`)
1. 🆕 `test_brainstorm_extract_uses_envelope_and_enriches_via_maps`
   — assert that after `POST /brainstorm/extract`, returned items have `place_id`
   and `lat/lng` populated by the mock map service.
2. 🆕 `test_brainstorm_chat_records_token_usage_row` — asserts persistence side-effect.
3. 🆕 `test_plan_trip_records_token_usage_row_with_source_plan_trip`.
4. 🆕 `test_concierge_endpoint_records_token_usage_with_source_concierge`
   (concierge endpoint exists via brainstorm/llm path — confirm `source` value).

---

## Section 2 — User Persona System

### Files under test
- `backend/app/config/persona_catalog.py`
- `backend/app/api/endpoints/users.py` (extended)
- `backend/app/services/llm/services/v1/roammate_v1.py::_pack_user_persona` (if added)
- Frontend: `PersonaPicker`, `OnboardingPersonaModal`, `PersonaSoftPrompt`,
  `EditProfile`, `PersonaCatalogContext`, `useProfile`, `UserMenu`, profile routes.

### Existing tests
- (none specific to personas)

### 2A — Persona catalog (🆕 `tests/services/test_persona_catalog.py`)
1. 🆕 `test_catalog_has_14_entries`.
2. 🆕 `test_catalog_slugs_are_unique`.
3. 🆕 `test_catalog_slugs_match_persona_enum`.
4. 🆕 `test_catalog_each_entry_has_label_icon_description`.
5. 🆕 `test_catalog_descriptions_under_140_chars` (prompt budget guard).

### 2B — Catalog endpoint (🆕 `tests/api/test_personas_catalog.py`)
1. 🆕 `test_GET_personas_catalog_public_no_auth_required` *(decision: spec says public — assert 200 without token; if implementation requires auth, flip this to assert 401 and update the doc).*
2. 🆕 `test_GET_personas_catalog_returns_14_items_in_stable_order`.
3. 🆕 `test_GET_personas_catalog_response_shape` (each item has `slug,label,icon,description`).

### 2C — `GET/PUT /users/me/personas` (🆕 `tests/api/test_users_personas.py`)
1. 🆕 `test_GET_my_personas_default_null` for a fresh user.
2. 🆕 `test_PUT_my_personas_happy_roundtrip`.
3. 🆕 `test_PUT_my_personas_empty_list_explicit_skip` (NULL → `[]`).
4. 🆕 `test_PUT_my_personas_unknown_slug_422` with the bad slug echoed in detail.
5. 🆕 `test_PUT_my_personas_partial_invalid_rejects_whole_request_atomically`
   — DB unchanged after 422.
6. 🆕 `test_PUT_my_personas_idempotent_same_value_no_throw`.
7. 🆕 `test_PUT_my_personas_requires_auth_401`.
8. 🆕 `test_PUT_my_personas_other_users_unaffected`.
9. 🆕 `test_GET_my_personas_after_update_reflects_change`.
10. 🆕 `test_PUT_my_personas_max_length_14_accepted_15_ignored_or_422` (decide; spec is silent — pin behaviour explicitly).

### 2D — Profile fields (🆕 `tests/api/test_users_profile.py`)
1. 🆕 `test_PUT_me_updates_name_only_other_fields_unchanged`.
2. 🆕 `test_PUT_me_updates_home_city_timezone_currency_blurb`.
3. 🆕 `test_PUT_me_password_requires_current_password_400`.
4. 🆕 `test_PUT_me_password_wrong_current_400`.
5. 🆕 `test_PUT_me_password_success_can_login_with_new_password`.
6. 🆕 `test_PUT_me_password_old_password_no_longer_valid`.
7. 🆕 `test_PUT_me_avatar_url_accepts_relative_and_absolute`.
8. 🆕 `test_PUT_me_travel_blurb_max_length_enforced`.
9. 🆕 `test_DELETE_me_removes_user_and_invalidates_token`.
10. 🆕 `test_DELETE_me_cascades_or_nulls_token_usage_user_id` (the FK is `SET NULL`).
11. 🆕 `test_DELETE_me_cascades_brainstorm_messages_and_items` (`ondelete=CASCADE`).
12. 🆕 `test_PUT_me_unauthenticated_401`.

### 2E — Persona LLM injection (🆕 `tests/services/test_roammate_v1_persona.py`)
1. 🆕 `test_pack_user_persona_empty_when_personas_null` — returns "".
2. 🆕 `test_pack_user_persona_empty_when_personas_empty_list` (explicit skip).
3. 🆕 `test_pack_user_persona_includes_descriptors_in_order`.
4. 🆕 `test_pack_user_persona_skips_unknown_slugs_silently`.
5. 🆕 `test_pack_user_persona_token_budget_under_120_for_all_14_selected`
   — count tokens with `tiktoken` cl100k (or fallback word*1.3).
6. 🆕 `test_pack_trip_context_appends_persona_block` — prompt contains both
   trip events and persona descriptors.
7. 🆕 `test_brainstorm_chat_with_two_personas_outputs_diverge`
   — snapshot test: same prompt, different personas → different system message.
8. 🆕 `test_existing_users_with_null_personas_unchanged_prompt` (regression).

### 2F — Onboarding gate (🆕 frontend, OR backend if a server-side flag is added)
If gating remains FE-only, document FE tests in §6. Backend invariants worth pinning:
1. 🆕 `test_register_returns_personas_null` — fresh signup payload.
2. 🆕 `test_register_then_PUT_personas_then_GET_me_reflects_value`.

---

## Section 3 — Brainstorm + LLM Interaction

### Files under test
- `backend/app/api/endpoints/brainstorm.py`, `llm.py`
- `backend/app/schemas/brainstorm.py`
- `backend/app/services/llm_client.py`
- Models: `BrainstormBinItem`, `BrainstormMessage`

### Existing tests
- ✅ `tests/api/test_brainstorm_api.py` (30 tests covering chat, extract, bulk, list, delete, promote, role gating, full-field copy, vote-after-promote).
- ✅ `tests/api/test_llm_plan_trip.py` (5 tests).
- ✅ `tests/cross/test_brainstorm_lifecycle.py` (8 tests).
- ✅ `tests/services/test_llm_client.py`.
- ✅ `tests/schemas/test_brainstorm_schema.py`.

### 3A — Gaps to add (🆕 extend `test_brainstorm_api.py`)
1. 🆕 `test_chat_empty_message_422`.
2. 🆕 `test_chat_message_too_long_422` (define cap; pin behaviour).
3. 🆕 `test_chat_history_only_last_N_passed_to_llm` (token budget — assert
   `llm_client.chat` called with at most N messages).
4. 🆕 `test_extract_with_no_assistant_messages_returns_empty_or_400`.
5. 🆕 `test_extract_dedups_against_existing_brainstorm_items`
   — calling extract twice does not duplicate items.
6. 🆕 `test_extract_dedups_against_existing_idea_bin_items`
   — items already in shared idea bin should not reappear in brainstorm.
7. 🆕 `test_bulk_insert_partial_invalid_rejected_atomically`.
8. 🆕 `test_bulk_insert_max_size_cap` (e.g. 50 items).
9. 🆕 `test_promote_emits_BRAINSTORM_PROMOTED_notification_to_other_members_only`
   — promoter does not self-notify (covered partially by `test_notification_fanout`,
   but pin the new enum value).
10. 🆕 `test_promote_added_by_user_with_no_first_name_falls_back_to_name_or_email`.
11. 🆕 `test_delete_chat_history_endpoint_or_DELETE_messages` (if implemented).
12. 🆕 `test_brainstorm_endpoints_404_on_nonexistent_trip`.
13. 🆕 `test_brainstorm_endpoints_404_on_archived_or_deleted_trip` if such state exists.
14. 🆕 `test_brainstorm_extract_envelope_handles_map_output_with_zero_items`.
15. 🆕 `test_brainstorm_extract_persists_full_google_fields_from_envelope`
    (place_id, address, photo_url, rating, types, opening_hours).

### 3B — Concurrency / race conditions (🆕 `tests/cross/test_brainstorm_concurrency.py`)
1. 🆕 `test_two_concurrent_promotes_same_item_only_one_succeeds`
   (the second sees 404 because the row was deleted by the first).
2. 🆕 `test_concurrent_extract_does_not_double_insert`
   (same chat history, two parallel extracts → unique titles only).
3. 🆕 `test_promote_during_chat_does_not_corrupt_history`.

---

## Section 4 — Google Maps Service (V1 / V2 / Mock + flags + route endpoint)

### Files under test
- `backend/app/services/google_maps/{__init__,base,v1,v2,mock,cache,breaker,tracker}.py`
- `backend/app/api/endpoints/maps.py`
- `backend/app/schemas/route.py`
- `backend/app/services/idea_bin.py` (find_place response tolerance)

### Existing tests
- ✅ `tests/services/test_google_maps_service.py` (32 tests) — V1/V2/Mock find_place,
  details, apply_details, factory, flag-off scenarios for both photos and rating,
  cache hit on second call.
- ✅ `tests/api/test_route_endpoint.py` (5 tests) — polyline, ordering, validation gates.

### 4A — Find place edge cases (🆕 extend `test_google_maps_service.py`)
1. 🆕 `test_v1_find_place_400_status_returns_zero_results_dict`.
2. 🆕 `test_v1_find_place_429_triggers_retry_then_success`.
3. 🆕 `test_v1_find_place_5xx_retries_then_raises`.
4. 🆕 `test_v2_find_place_field_mask_header_present_on_request`.
5. 🆕 `test_v2_find_place_handles_displayName_text_vs_string` (older v1-shaped
   responses leaking through `idea_bin.py` tolerance).
6. 🆕 `test_idea_bin_find_place_accepts_v1_and_v2_shapes` — explicit unit test on
   the tolerance code in `idea_bin.py` (currently exercised only indirectly).

### 4B — Place details edge cases
1. 🆕 `test_v1_place_details_missing_geometry_keeps_existing_lat_lng_or_null`.
2. 🆕 `test_v1_place_details_missing_photos_array_no_photo_url`.
3. 🆕 `test_v2_place_details_missing_priceLevel_no_field_set`.
4. 🆕 `test_v2_priceLevel_string_to_int_mapping_all_5_values`
   (`PRICE_LEVEL_FREE..VERY_EXPENSIVE` → 0..4).
5. 🆕 `test_apply_details_does_not_overwrite_existing_lat_lng_when_falsy_in_response`.

### 4C — Cache behaviour (🆕 `tests/services/test_maps_cache.py`)
1. 🆕 `test_cache_keyed_by_place_id_and_field_signature`.
2. 🆕 `test_cache_v1_and_v2_entries_isolated` (same place_id, different versions
   never collide).
3. 🆕 `test_cache_evicts_oldest_at_lru_capacity`.
4. 🆕 `test_cache_ttl_expiry`.
5. 🆕 `test_negative_cache_records_zero_results_and_short_circuits`.
6. 🆕 `test_cache_field_signature_changes_when_flag_toggled`
   — tracking test: with `FETCH_RATING=False` then `True`, two distinct cache
   entries exist for the same place_id.

### 4D — Circuit breaker (🆕 `tests/services/test_maps_breaker.py`)
1. 🆕 `test_breaker_opens_after_N_consecutive_failures`.
2. 🆕 `test_breaker_open_short_circuits_calls_with_circuit_open_status`.
3. 🆕 `test_breaker_half_open_after_cooldown_recovers_on_success`.
4. 🆕 `test_breaker_per_process_state_does_not_leak_between_test_modules`
   (reset fixture sanity test).

### 4E — Tracker (🆕 `tests/services/test_maps_tracker.py`)
1. 🆕 `test_track_call_logs_structured_record_with_op_status_latency`.
2. 🆕 `test_track_call_persists_google_maps_api_usage_row`.
3. 🆕 `test_track_call_cost_zero_for_cache_hits`.
4. 🆕 `test_track_call_cost_uses_MAPS_PRICING_for_op`.
5. 🆕 `test_track_call_user_id_threaded_from_caller`
   (assert `user_id` column populated when caller passes it).
6. 🆕 `test_enrich_batch_op_does_not_double_count_cost`
   (find_place + place_details billed separately; enrich_batch row has
   `cost_usd=0`).
7. 🆕 `test_track_call_db_failure_swallowed_logs_warning`.

### 4F — Route endpoint (🆕 extend `test_route_endpoint.py`)
1. 🆕 `test_route_non_member_403`.
2. 🆕 `test_route_unauthenticated_401`.
3. 🆕 `test_route_with_one_event_returns_need_two_points`.
4. 🆕 `test_route_filters_by_day_query_param`
   (events on day-1 and day-2; `?day=1` returns only day-1 polyline).
5. 🆕 `test_route_returns_per_leg_distance_and_duration`.
6. 🆕 `test_route_two_back_to_back_events_zero_gap_allowed`
   (boundary case for "conflict" check — same end/start time should pass).
7. 🆕 `test_route_overlap_validation_error_payload_shape`
   (the error matches `RouteValidationError` schema).
8. 🆕 `test_route_when_events_lack_lat_lng_uses_place_id_lookup_path`.
9. 🆕 `test_route_with_breaker_open_returns_503_or_graceful_message`.

### 4G — Factory & config (🆕 extend `test_google_maps_service.py`)
1. 🆕 `test_factory_invalid_GOOGLE_MAPS_API_VERSION_falls_back_to_v1`
   (e.g. `"v3"` → V1).
2. 🆕 `test_factory_lru_cached_singleton_invalidated_when_settings_change`
   (or document that a process restart is required).

### 4H — Schema tests (🆕 `tests/schemas/test_route_schema.py`)
1. 🆕 `test_RouteResponse_serialises_polyline_and_legs`.
2. 🆕 `test_RouteValidationError_required_fields`.

---

## Section 5 — Maps Feature Flags (`FETCH_PHOTOS`, `FETCH_RATING`)

### Existing tests
- ✅ Eight V1/V2/Mock `_apply_details` flag-off tests in `test_google_maps_service.py`.

### 5A — End-to-end propagation (🆕 cross test: `tests/cross/test_maps_flags_propagation.py`)
1. 🆕 `test_brainstorm_extract_with_FETCH_PHOTOS_off_items_lack_photo_url`
   (flip env var via `monkeypatch.setenv`, restart factory cache, call extract).
2. 🆕 `test_brainstorm_extract_with_FETCH_RATING_off_items_lack_rating_and_price_level`.
3. 🆕 `test_route_endpoint_unaffected_by_FETCH_PHOTOS_flag` (orthogonality).
4. 🆕 `test_idea_bin_promotion_carries_flag_state` —
   if photo was never fetched it stays absent in the promoted idea row.
5. 🆕 `test_flag_toggle_mid_session_old_cache_entries_not_reused`
   (cache key includes field-signature — verified in §4C, but assert via
   end-to-end call counts here too).
6. 🆕 `test_billing_cost_drops_when_rating_flag_off`
   (token tracker / maps tracker shows cheaper SKU billing per
   `MAPS_PRICING` table).

---

## Section 6 — Frontend (Persona, Profile, Admin, Map UI)

There is no frontend test infra today (no `vitest`, no `jest.config.*`).
This section lists the **suite to add once a runner is wired**, plus the
**manual QA matrix** to use in the meantime.

### 6A — Setup (🆕 one-time)
- Add `vitest`, `@testing-library/react`, `@testing-library/user-event`,
  `jsdom`, `msw` (mock fetch).
- `frontend/vitest.config.ts` with React + path aliases matching `tsconfig.json`.
- `frontend/__tests__/` mirror layout of `frontend/components/`.

### 6B — `PersonaPicker.tsx`
1. 🆕 `renders_14_chips_from_catalog_context`.
2. 🆕 `selecting_a_chip_toggles_its_state_and_aria_checked`.
3. 🆕 `save_button_disabled_until_selection_changes`.
4. 🆕 `save_calls_onSave_with_selected_slugs`.
5. 🆕 `reset_returns_to_initial_selection`.
6. 🆕 `keyboard_space_toggles_focused_chip` (a11y).
7. 🆕 `reduced_motion_disables_stagger`.

### 6C — `OnboardingPersonaModal.tsx`
1. 🆕 `mounts_only_when_personas_is_null`.
2. 🆕 `backdrop_click_does_not_dismiss`.
3. 🆕 `Esc_does_not_dismiss`.
4. 🆕 `Continue_disabled_when_zero_selected_unless_skip_used`.
5. 🆕 `Continue_PUTs_personas_and_navigates_to_dashboard`.
6. 🆕 `Skip_PUTs_empty_list_and_sets_localStorage_flag`.

### 6D — `PersonaSoftPrompt.tsx`
1. 🆕 `renders_when_personas_is_empty_list`.
2. 🆕 `does_not_render_when_personas_has_items`.
3. 🆕 `does_not_render_when_localStorage_dismissed`.
4. 🆕 `dismiss_writes_localStorage_and_unmounts`.

### 6E — `EditProfile.tsx`
1. 🆕 `inline_edit_name_saves_on_Enter_reverts_on_Esc`.
2. 🆕 `password_change_requires_current_password`.
3. 🆕 `unsaved_changes_pill_appears_when_field_dirty`.
4. 🆕 `tab_switch_with_dirty_state_shows_confirm_modal`.
5. 🆕 `delete_account_modal_requires_typing_email_to_confirm`.
6. 🆕 `avatar_upload_emits_blob_to_POST_users_me_avatar`.

### 6F — `useProfile.ts`
1. 🆕 `loads_user_on_mount`.
2. 🆕 `optimistically_updates_then_reverts_on_error`.
3. 🆕 `dirty_flag_per_field`.

### 6G — `UserMenu.tsx`
1. 🆕 `three_dot_opens_popover`.
2. 🆕 `click_outside_closes_popover`.
3. 🆕 `Profile_navigates_to_profile_route`.
4. 🆕 `Logout_calls_handleLogout`.

### 6H — Admin login + dashboard (`useAdminAuth`, `/admin`, `/admin/dashboard`)
1. 🆕 `login_with_correct_creds_stores_token_in_sessionStorage`.
2. 🆕 `login_with_wrong_creds_shows_error`.
3. 🆕 `dashboard_redirects_to_login_when_no_token`.
4. 🆕 `dashboard_redirects_to_login_when_GET_users_returns_401`.
5. 🆕 `sidebar_section_change_refetches_filtered_data`.
6. 🆕 `users_section_filters_by_search_locally`.
7. 🆕 `token_usage_filters_provider_model_month_day` — assert query string.
8. 🆕 `maps_usage_op_multiselect_includes_each_in_query_string`.
9. 🆕 `logout_clears_sessionStorage_and_redirects`.
10. 🆕 `closing_browser_tab_clears_session` (covered by sessionStorage choice;
    pin via `window.dispatchEvent('beforeunload')` test).

### 6I — Map UI (`GoogleMap.tsx` — large refactor in commit `8b172fb`)
1. 🆕 `renders_AdvancedMarkerElement_for_each_event_with_lat_lng`.
2. 🆕 `route_refresh_button_calls_POST_trips_id_route`.
3. 🆕 `polyline_filtered_by_active_day`.
4. 🆕 `missing_time_validation_toast_blocks_route_call`.
5. 🆕 `time_overlap_validation_toast_blocks_route_call`.
6. 🆕 `marker_click_focuses_event_in_timeline_pane`.

### 6J — Flag-driven UI gating (`BrainstormBin`, `IdeaBin`, `Timeline`)
1. 🆕 `BrainstormBin_hides_rating_when_NEXT_PUBLIC_FETCH_RATING_false`.
2. 🆕 `BrainstormBin_hides_photo_when_NEXT_PUBLIC_FETCH_PHOTOS_false`.
3. 🆕 `IdeaBin_no_details_fallback_when_both_flags_off_and_no_address`.
4. 🆕 `Timeline_tooltip_arrow_hidden_when_no_details_per_flags`.
5. 🆕 `Timeline_tooltip_renders_photo_only_when_flag_on_and_url_present`.

### 6K — Manual QA matrix (until FE runner exists)
Mirror the verification sections in `[3] brainstorm-bin-and-llm-interaction-plan.md`,
`[4] user-persona-implementation-plan.md`, and `admin-dashboard-plan.md` 1:1
into a checklist file under `docs/qa/` and run on every PR touching these
surfaces.

---

## Section 7 — Admin Panel (Backend)

### Files under test
- `backend/app/api/endpoints/admin.py`
- `backend/app/api/deps.py::get_admin`
- `backend/app/services/admin_costs.py`
- Models `TokenUsage`, `GoogleMapsApiUsage`

### Existing tests
- (none specific to admin — listed under "files mention admin" but no actual coverage)

### 7A — Admin auth (🆕 `tests/api/test_admin_auth.py`)
1. 🆕 `test_login_correct_creds_returns_token_with_admin_claim`.
2. 🆕 `test_login_wrong_username_401`.
3. 🆕 `test_login_wrong_password_401`.
4. 🆕 `test_login_returns_token_expiring_in_4_hours`.
5. 🆕 `test_admin_endpoint_without_token_401`.
6. 🆕 `test_admin_endpoint_with_user_jwt_403` (user JWT has no `admin` claim).
7. 🆕 `test_admin_endpoint_with_expired_admin_token_401`.
8. 🆕 `test_admin_endpoint_with_token_signed_by_other_secret_401`.
9. 🆕 `test_admin_endpoint_with_garbage_token_401`.

### 7B — Users endpoint (🆕 `tests/api/test_admin_users.py`)
1. 🆕 `test_GET_admin_users_returns_total_and_list_sorted_by_created_desc`.
2. 🆕 `test_GET_admin_users_includes_users_with_null_personas`.
3. 🆕 `test_GET_admin_users_does_not_leak_hashed_password`.

### 7C — Token usage endpoints (🆕 `tests/api/test_admin_token_usage.py`)
Seed 6–10 `TokenUsage` rows across providers/models/sources/dates in fixtures.
1. 🆕 `test_summary_no_filters_returns_total_and_breakdowns`.
2. 🆕 `test_summary_filter_by_provider`.
3. 🆕 `test_summary_filter_by_model`.
4. 🆕 `test_summary_filter_by_month`.
5. 🆕 `test_summary_filter_by_day_overrides_month`.
6. 🆕 `test_summary_invalid_month_format_silently_ignored` (matches code) — pin behaviour.
7. 🆕 `test_summary_invalid_day_format_silently_ignored`.
8. 🆕 `test_summary_top_model_when_tie_picks_one_deterministically_or_documented`.
9. 🆕 `test_summary_avg_tokens_zero_when_no_rows`.
10. 🆕 `test_users_groups_by_user_and_sums_correctly`.
11. 🆕 `test_users_search_filters_by_name_or_email_substring_case_insensitive`.
12. 🆕 `test_users_unattributed_row_when_user_id_is_null` (orphan after cascade).
13. 🆕 `test_options_returns_distinct_provider_to_model_mapping`.
14. 🆕 `test_options_empty_when_no_token_usage_rows`.

### 7D — Maps usage endpoints (🆕 `tests/api/test_admin_maps_usage.py`)
1. 🆕 `test_summary_no_filters`.
2. 🆕 `test_summary_filter_by_ops_multi`.
3. 🆕 `test_summary_filter_by_month`.
4. 🆕 `test_summary_filter_by_day`.
5. 🆕 `test_summary_cache_hit_rate_calculation`.
6. 🆕 `test_summary_error_rate_calculation`.
7. 🆕 `test_summary_zero_rows_returns_zero_rates_not_NaN`.
8. 🆕 `test_users_pivots_calls_by_op_per_user`.
9. 🆕 `test_users_search_filter`.
10. 🆕 `test_users_unattributed_grouped_under_single_row`.
11. 🆕 `test_users_total_cost_summed_per_user`.

### 7E — Cost computation (🆕 `tests/services/test_admin_costs.py`)
1. 🆕 `test_TOKEN_PRICING_includes_each_supported_provider_model_pair`.
2. 🆕 `test_token_cost_calculation_known_values` (parametrised across pricing table).
3. 🆕 `test_unknown_model_returns_zero_cost`.
4. 🆕 `test_MAPS_PRICING_each_op_has_entry_or_zero`.
5. 🆕 `test_enrich_batch_pricing_is_zero_to_avoid_double_count`.
6. 🆕 `test_decimal_precision_to_six_places`.

### 7F — End-to-end persistence (🆕 `tests/cross/test_admin_persistence.py`)
1. 🆕 `test_brainstorm_chat_then_admin_token_usage_summary_reflects_call`
   (call brainstorm chat as user, then admin login, then summary contains
   the row).
2. 🆕 `test_route_endpoint_then_admin_maps_usage_summary_reflects_directions`.
3. 🆕 `test_two_users_token_usage_correctly_attributed_per_user`.
4. 🆕 `test_user_deleted_orphans_token_usage_with_user_id_null_visible_as_unattributed`.

---

## Section 8 — Cross-feature & cross-entity scenarios

These are the biggest source of regressions and the most under-tested area today.

### 8A — Persona × LLM (🆕 `tests/cross/test_persona_llm_interaction.py`)
1. 🆕 `test_user_with_personas_brainstorm_extract_yields_persona_themed_items`
   (snapshot: prompt sent to LLM contains persona descriptors).
2. 🆕 `test_user_with_personas_concierge_chat_passes_personas_in_system_prompt`.
3. 🆕 `test_persona_change_takes_effect_on_next_chat_no_caching`.
4. 🆕 `test_two_users_on_same_trip_personas_isolated_per_user`.

### 8B — Brainstorm × Map (🆕 `tests/cross/test_brainstorm_map_enrichment.py`)
1. 🆕 `test_brainstorm_extract_calls_enrich_items_once_per_batch`.
2. 🆕 `test_brainstorm_extract_with_breaker_open_persists_unenriched_items_gracefully`.
3. 🆕 `test_brainstorm_extract_partial_enrichment_failures_skip_only_failing_items`.

### 8C — Brainstorm × Idea Bin × Vote × Notification × Group Library
This already has solid coverage in `test_brainstorm_lifecycle.py`. Add:
1. 🆕 `test_promote_emits_notification_with_correct_BRAINSTORM_PROMOTED_type`.
2. 🆕 `test_promote_then_archive_idea_does_not_resurrect_in_brainstorm`.
3. 🆕 `test_promote_idempotency_promoting_same_subset_twice_second_call_404`.

### 8D — Map × Route × Trip days × Events (🆕 `tests/cross/test_route_trip_interaction.py`)
1. 🆕 `test_route_recomputes_after_event_reorder`.
2. 🆕 `test_route_recomputes_after_event_lat_lng_changes`.
3. 🆕 `test_deleting_event_invalidates_route_cache_or_recomputes`.
4. 🆕 `test_route_for_day_with_only_one_event_returns_need_two_points`.

### 8E — Admin × Persistence × User lifecycle (🆕 `tests/cross/test_admin_user_lifecycle.py`)
1. 🆕 `test_user_register_login_chat_admin_summary_full_loop`.
2. 🆕 `test_user_delete_then_admin_summary_marks_their_rows_unattributed`.
3. 🆕 `test_admin_login_does_not_create_token_usage_row` (admin actions don't
   pollute the metrics).

### 8F — Flags × Admin (🆕 `tests/cross/test_flags_admin_visibility.py`)
1. 🆕 `test_with_FETCH_PHOTOS_off_admin_maps_usage_shows_zero_photo_url_calls`.
2. 🆕 `test_with_FETCH_RATING_off_admin_maps_usage_shows_essentials_tier_pricing`
   (cost per call drops for `place_details`).

### 8G — Migration / startup safety (🆕 `tests/cross/test_startup_migration.py`)
1. 🆕 `test_auto_migrate_creates_personas_avatar_url_etc_columns_idempotently`
   (run twice, no error).
2. 🆕 `test_auto_migrate_creates_token_usage_and_google_maps_api_usage_tables`.
3. 🆕 `test_auto_migrate_extends_idea_bin_item_with_google_maps_columns`.
4. 🆕 `test_auto_migrate_no_op_when_schema_already_current`.

---

## Section 9 — Schemas & validators (🆕 `tests/schemas/`)

1. 🆕 `test_PersonaUpdate_rejects_non_list`.
2. 🆕 `test_ProfileUpdate_password_without_current_rejected_at_endpoint_layer`
   (already covered API-side; pin schema-level shape).
3. 🆕 `test_RouteResponse_polyline_is_encoded_string`.
4. 🆕 `test_BrainstormItemBase_extra_fields_forbidden_or_ignored` (pin).

---

## Section 10 — Performance / smoke (optional but recommended)

1. 🆕 `test_brainstorm_extract_50_items_under_X_seconds` (with mock map).
2. 🆕 `test_admin_token_usage_summary_with_10K_rows_under_500ms`.
3. 🆕 `test_route_with_10_waypoints_returns_under_2s` (mock).

---

## Test infrastructure improvements

1. 🆕 `conftest.py` fixtures:
   - `admin_token` (calls `/api/admin/login`).
   - `admin_headers` analogous to `auth_headers`.
   - `seed_token_usage` factory fixture that inserts N rows with controllable
     `provider/model/created_at`.
   - `seed_maps_usage` analogue.
   - `monkeypatch_maps_flags` context manager that flips
     `GOOGLE_MAPS_FETCH_PHOTOS` / `GOOGLE_MAPS_FETCH_RATING` and resets the
     `lru_cache` on the factory.
2. 🆕 Hermetic Postgres alternative: keep SQLite for fast unit, add a
   `@pytest.mark.pg` marker that runs against a Dockerised Postgres for
   `JSON` / `Numeric` precision checks (current setup uses SQLite — `Numeric(10,6)`
   precision in cost-rounding tests should be verified on Postgres at least once).
3. 🆕 Snapshot library (`syrupy`) for prompt-diff tests in §1 and §2E.
4. 🆕 Coverage gate: target ≥85% on
   `app/services/llm/**`, `app/services/google_maps/**`,
   `app/api/endpoints/{admin,brainstorm,llm,maps,users}.py`,
   `app/config/persona_catalog.py`.

---

## Suggested execution order

1. **Phase A — close backend gaps** (sections 1, 2, 4, 5, 7).
   Highest leverage, smallest infra investment.
2. **Phase B — cross tests** (sections 3B, 8). Most regression value.
3. **Phase C — frontend infra + tests** (section 6). Largest setup cost.
4. **Phase D — perf & migration** (sections 9, 10). Final hardening.

Estimated new tests: **~190**.
Existing tests retained: **~85** (across the seven existing files listed above).
