# Backend Test Suite Catalogue: Roammate

Canonical, exhaustive list of test cases for **Integration**, **Smoke**, and **Scale** tiers.
Each entry is a `test_` function with a 1-2 line description of what it asserts.

Companion blueprint: `docs/[40] backend-testing-blueprint.md`

> **Tier boundary note.** Pure-logic tests live in `tests/unit/` and are intentionally **not** catalogued
> here: schema validation (`event`, `votes`, `place_fields`, `brainstorm`, `group`, `library` schemas),
> the LLM pre-processor / dedup / clients / registry / fallbacks, the Maps circuit-breaker state machine,
> the Smart Ripple wall-clock math, the persona catalog, and cost-table computation. This catalogue owns
> the **integration tier**: DB-backed services, Redis/HTTP-mock-boundary code, and cross-cutting flows.
> The legacy `tests/cross/`, `tests/services/`, and `tests/schemas/` folders are folded into `tests/integration/`.

---

## Table of Contents

1. [Auth & Identity](#1-auth--identity)
2. [Billing & Entitlements](#2-billing--entitlements)
3. [Trips](#3-trips)
4. [Trip Members & Invitations](#4-trip-members--invitations)
5. [Trip Days](#5-trip-days)
6. [Events (Timeline Items)](#6-events-timeline-items)
7. [Idea Bin](#7-idea-bin)
8. [Brainstorm Chat & Bin](#8-brainstorm-chat--bin)
9. [Concierge](#9-concierge)
10. [Votes & Vote Transfer](#10-votes--vote-transfer)
11. [Notifications](#11-notifications)
12. [Groups](#12-groups)
13. [Maps & Enrichment](#13-maps--enrichment)
14. [Routes & DayRoute Persistence](#14-routes--dayroute-persistence)
15. [Ripple Engine](#15-ripple-engine)
16. [Dashboard](#16-dashboard)
17. [LLM ↔ DB Integration](#17-llm--db-integration)
18. [Ideas (Tags & Copy)](#18-ideas-tags--copy)
19. [Users & Personas](#19-users--personas)
20. [Tutorial & Onboarding](#20-tutorial--onboarding)
21. [Admin Panel](#21-admin-panel)
22. [Pagination & OpenAPI](#22-pagination--openapi)
23. [Google Maps Service (v1/v2/mock/factory)](#23-google-maps-service-v1v2mockfactory)
24. [Apple Maps Service](#24-apple-maps-service)
25. [Maps Location Bias & Geocoding](#25-maps-location-bias--geocoding)
26. [Redis Cache & Breaker](#26-redis-cache--breaker)
27. [Spec Validation Middleware](#27-spec-validation-middleware)
28. [Notification Service (DB emit)](#28-notification-service-db-emit)
29. [Roles & RBAC (DB)](#29-roles--rbac-db)
30. [Maps Feature-Flag Propagation](#30-maps-feature-flag-propagation)
31. [Brainstorm ↔ Maps Enrichment](#31-brainstorm--maps-enrichment)
32. [Brainstorm Concurrency](#32-brainstorm-concurrency)
33. [Persona ↔ LLM Interaction](#33-persona--llm-interaction)
34. [Admin Persistence & Token Attribution](#34-admin-persistence--token-attribution)
35. [Smoke Tests](#35-smoke-tests)
36. [Scale & Performance Tests (Locust)](#36-scale--performance-tests-locust)

---

## 1. Auth & Identity

### Integration Tests — `tests/integration/test_auth_lifecycle.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_signup_creates_unverified_user` | POST /auth/signup inserts a User row with `email_verified=False` and issues an EmailVerification token. |
| 2 | `test_signup_duplicate_email_does_not_leak` | Signing up with an existing email returns 200 with the same ambiguous message regardless of whether the email exists, preventing enumeration. |
| 3 | `test_signup_unverified_duplicate_reissues_token` | If a prior unverified user exists, /signup re-issues a fresh verification token and sends a new email. |
| 4 | `test_verify_token_activates_user` | Consuming a valid verification token sets `email_verified=True`, `email_verified_at`, and returns a JWT+refresh pair. |
| 5 | `test_verify_expired_token_rejected` | A token whose `expires_at` is in the past returns 400 "Invalid or expired". |
| 6 | `test_verify_consumed_token_rejected` | Re-using an already-consumed verification token returns 400. |
| 7 | `test_verify_resend_204_for_unknown_email` | /verify/resend always returns 204 even for non-existent emails (anti-enumeration). |
| 8 | `test_login_correct_credentials` | POST /auth/login with valid email+password returns TokenPair and sets `rm_access` / `rm_refresh` cookies. |
| 9 | `test_login_wrong_password_401` | Incorrect password returns 401 without revealing whether the email exists. |
| 10 | `test_login_unverified_email_409` | Login against an unverified account returns 409 and re-sends the verification email. |
| 11 | `test_login_skip_verification_flag` | `skip_verification=True` bypasses the 409 check and issues tokens for unverified users. |
| 12 | `test_refresh_token_rotation` | Presenting a valid refresh token returns a new pair and revokes the old one. The old token cannot be reused. |
| 13 | `test_refresh_token_reuse_revokes_chain` | Replaying a consumed refresh token revokes all tokens for that user (theft detection). |
| 14 | `test_refresh_expired_token_401` | A refresh token past its `expires_at` returns 401. |
| 15 | `test_logout_revokes_refresh_and_clears_cookies` | POST /auth/logout marks the refresh token row `revoked_at` and clears both cookies. |
| 16 | `test_password_forgot_sends_reset` | POST /auth/password/forgot for an existing user with a password inserts a PasswordReset row. Returns 204 regardless. |
| 17 | `test_password_forgot_no_password_user_noop` | OAuth-only users (no hashed_password) do not get a reset token issued. |
| 18 | `test_password_forgot_unknown_email_204` | Unknown email returns 204 without leaking existence. |
| 19 | `test_password_reset_success` | Consuming a valid reset token updates `hashed_password`, bumps `auth_version`, revokes all existing refresh tokens, and issues a fresh session. |
| 20 | `test_password_reset_expired_400` | Expired reset token returns 400. |
| 21 | `test_password_reset_consumed_400` | Already-consumed reset token returns 400. |
| 22 | `test_auth_version_bump_invalidates_access_tokens` | After a password reset bumps `auth_version`, old access tokens (with the prior `ver` claim) are rejected by `get_current_user`. |
| 23 | `test_google_oauth_creates_new_user` | Valid Google id_token for an unknown email creates User + UserIdentity rows and returns a session. |
| 24 | `test_google_oauth_links_existing_verified_user` | Google OAuth with an email matching an existing verified user links the identity and returns a session for that user. |
| 25 | `test_google_oauth_blocks_unverified_existing_email` | If the email exists but is unverified, OAuth raises 409 `verify_existing_email_first`. |
| 26 | `test_google_oauth_invalid_token_400` | Malformed or invalid id_token returns 400. |
| 27 | `test_apple_oauth_creates_new_user` | Valid Apple id_token creates User + UserIdentity(provider=apple) and returns a session. |
| 28 | `test_apple_oauth_links_existing_verified_user` | Apple OAuth links to an existing verified email and reuses the user row. |
| 29 | `test_change_email_issues_verification` | POST /auth/me/email/change with correct password issues a `change_email` verification token for the new address. |
| 30 | `test_change_email_wrong_password_400` | Incorrect password returns 400 "Password incorrect". |
| 31 | `test_change_email_same_email_400` | Attempting to change to the same email returns 400. |
| 32 | `test_change_email_taken_409` | If the new email is already owned by another user, returns 409. |
| 33 | `test_verify_change_email_updates_user_email` | Consuming a `change_email` verification token updates `user.email` to the new address. |
| 34 | `test_list_identities_shows_linked_providers` | GET /auth/me/identities returns provider list and `has_password` flag. |
| 35 | `test_unlink_identity_removes_provider` | DELETE /auth/me/identities/{provider} removes the UserIdentity row. |
| 36 | `test_unlink_last_method_blocked` | Cannot unlink the only sign-in method (no password + 1 identity) — returns 400. |
| 37 | `test_unlink_nonexistent_identity_404` | Unlinking a provider not linked to the user returns 404. |

---

## 2. Billing & Entitlements

### Integration Tests — `tests/integration/test_entitlements.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_free_user_entitlement_defaults` | A fresh user gets `tier=free`, `can_use_concierge=False`, `brainstorm_remaining=15`, `active_trip_cap=2`. |
| 2 | `test_plus_user_entitlement_unlimited` | A user with `subscription_tier=plus`, `subscription_status=active` gets unlimited brainstorm, concierge access, and no trip cap. |
| 3 | `test_expired_plus_reverts_to_free` | When `subscription_current_period_end` is in the past, `_is_active` returns False and entitlement downgrades to free. |
| 4 | `test_past_due_status_keeps_plus_active` | `subscription_status=past_due` still returns `_is_active=True` (grace period). |
| 5 | `test_active_trip_count_excludes_past_trips` | Trips whose `end_date < today` are not counted against the active trip cap. |
| 6 | `test_active_trip_count_includes_null_end_date` | Trips with `end_date=None` (planning-in-progress) count as active. |
| 7 | `test_enforce_active_trip_raises_402` | A free user at the 2-trip cap attempting to create a third gets HTTP 402 with `code=needs_plus`. |
| 8 | `test_enforce_active_trip_allows_tutorial` | Tutorial trips bypass the active trip cap enforcement. |
| 9 | `test_enforce_brainstorm_raises_402_at_cap` | A free user who has sent 15 brainstorm messages gets 402 on the next chat call. |
| 10 | `test_enforce_brainstorm_skips_plus_user` | Plus user never gets 402 on brainstorm regardless of message count. |
| 11 | `test_enforce_concierge_raises_402_for_free` | Free users get 402 on POST /concierge/{trip_id}/chat. |
| 12 | `test_enforce_concierge_allows_tutorial` | Tutorial trips bypass concierge gating for free users. |
| 13 | `test_bump_brainstorm_counter_increments` | `bump_brainstorm_counter` upserts the UsageCounter row and increments `brainstorm_messages`. |
| 14 | `test_bump_brainstorm_counter_noop_for_plus` | Plus users do not have their counter incremented. |
| 15 | `test_bump_brainstorm_counter_noop_for_tutorial` | Tutorial trips do not consume free-tier quota. |
| 16 | `test_usage_counter_resets_monthly` | A counter for period `2026-04` does not affect enforcement in period `2026-05`. |

### Integration Tests — `tests/integration/test_coupons.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_validate_coupon_returns_quote` | A valid active coupon for the correct target returns a CouponQuote with computed discount and final amounts. |
| 2 | `test_validate_coupon_not_found` | An unknown code raises 400 `coupon_not_found`. |
| 3 | `test_validate_coupon_inactive` | A coupon with `is_active=False` raises 400 `coupon_inactive`. |
| 4 | `test_validate_coupon_expired` | A coupon whose `valid_until` is in the past raises 400 `coupon_expired`. |
| 5 | `test_validate_coupon_not_yet_active` | A coupon whose `valid_from` is in the future raises 400 `coupon_not_yet_active`. |
| 6 | `test_validate_coupon_wrong_target` | A `one_time` coupon applied to `subscription` target raises 400 `coupon_wrong_target`. |
| 7 | `test_validate_coupon_already_redeemed` | A user who has a CouponRedemption row for this coupon gets 400 `coupon_already_redeemed`. |
| 8 | `test_flat_off_discount_computation` | `discount_type=flat_off` subtracts value from original, clamped to 0. |
| 9 | `test_percent_off_discount_computation` | `discount_type=percent_off` applies basis-point math correctly. |
| 10 | `test_fixed_price_discount_computation` | `discount_type=fixed_price` sets the final price to the coupon value. |
| 11 | `test_record_redemption_idempotent` | Calling `record_redemption` twice with the same coupon+user is a no-op on conflict. |

### Integration Tests — `tests/integration/test_billing_flows.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_billing_status_returns_entitlement_dto` | GET /billing/status returns the full entitlement DTO including tier, caps, and pricing. |
| 2 | `test_create_razorpay_subscription_returns_sub_id` | POST /billing/razorpay/subscription (mocked Razorpay client) returns `subscription_id` and sets user to `subscription_status=pending`. |
| 3 | `test_create_razorpay_subscription_with_coupon` | When `coupon_code` is provided, the offer_id from the coupon is forwarded to Razorpay and the response includes the coupon DTO. |
| 4 | `test_razorpay_webhook_subscription_activated` | A `subscription.activated` webhook payload flips user to `tier=plus`, `status=active` and records a SubscriptionEvent. |
| 5 | `test_razorpay_webhook_subscription_halted` | A `subscription.halted` webhook sets `status=past_due`. |
| 6 | `test_razorpay_webhook_subscription_cancelled` | A `subscription.cancelled` webhook sets `status=canceled` (user keeps Plus until period_end). |
| 7 | `test_razorpay_webhook_subscription_expired` | A `subscription.expired` webhook downgrades to `tier=free`, `status=expired`. |
| 8 | `test_razorpay_webhook_idempotent_replay` | Replaying the same `event_id` returns `{"ok": true, "replay": true}` without mutating user state. |
| 9 | `test_razorpay_webhook_invalid_signature_400` | An incorrect signature header returns 400. |
| 10 | `test_razorpay_webhook_missing_subscription_ignored` | A webhook payload without a subscription entity is silently ignored. |
| 11 | `test_razorpay_webhook_coupon_redemption_on_activation` | When notes contain `coupon_id`, the activation webhook records a CouponRedemption row. |
| 12 | `test_one_time_purchase_zero_price_grants_directly` | A coupon that zeroes the price bypasses Razorpay and grants Plus immediately with `provider=internal_grant`. |
| 13 | `test_one_time_purchase_creates_razorpay_order` | Without a zero-price coupon, an order is created and order_id + amount_paise are returned. |
| 14 | `test_verify_one_time_purchase_success` | Valid signature + captured payment flips user to `one_time` Plus and records a SubscriptionEvent. |
| 15 | `test_verify_one_time_purchase_invalid_signature_400` | Bad signature returns 400 "Invalid payment signature". |
| 16 | `test_verify_one_time_purchase_not_captured_400` | If the payment status is not `captured`/`authorized`, returns 400. |
| 17 | `test_verify_one_time_purchase_idempotent` | Replaying the same payment_id does not double-grant (SubscriptionEvent conflict = no-op). |
| 18 | `test_apple_verify_monthly_subscription` | A valid signed JWS for the monthly product flips user to Plus with `expires_date` from the transaction. |
| 19 | `test_apple_verify_one_time_nonrenewing` | A non-renewing Apple product sets `status=one_time` and computes `period_end = now + 30 days`. |
| 20 | `test_apple_verify_expired_transaction` | An expired Apple transaction sets `tier=free`, `status=expired`. |
| 21 | `test_apple_verify_invalid_jws_400` | Malformed JWS returns 400. |
| 22 | `test_apple_verify_wrong_product_400` | A valid JWS for an unrecognized product/bundle returns 400. |
| 23 | `test_apple_verify_coupon_redemption` | When `coupon_id` is passed, a CouponRedemption row is recorded alongside the verify. |
| 24 | `test_apple_webhook_renew_updates_period_end` | An Apple server notification with a renewed transaction updates `subscription_current_period_end`. |
| 25 | `test_apple_webhook_expired_downgrades` | An expired Apple notification sets `tier=free`. |
| 26 | `test_apple_webhook_idempotent_replay` | Replaying the same transaction_id returns `{"ok": true, "replay": true}`. |
| 27 | `test_apple_redeem_offer_returns_signed_payload` | POST /billing/apple/redeem-offer with a valid coupon returns the signed promotional offer fields. |
| 28 | `test_apple_redeem_offer_no_apple_offer_400` | A coupon without `apple_offer_id` returns 400 `no_apple_offer`. |
| 29 | `test_cancel_subscription_razorpay` | POST /billing/cancel for a Razorpay user calls `cancel_subscription(at_cycle_end=True)` and sets `status=canceled`. |
| 30 | `test_cancel_subscription_apple_blocked` | POST /billing/cancel for an Apple user returns 400 `cancel_not_allowed`. |
| 31 | `test_validate_coupon_endpoint` | POST /billing/coupons/validate returns a CouponQuote DTO without redeeming. |

---

## 3. Trips

### Integration Tests — `tests/integration/test_trips.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_create_trip_returns_trip_with_member` | POST /trips creates a Trip row and auto-adds the creator as an admin TripMember. |
| 2 | `test_create_trip_sets_destination_metadata` | `destination_city`, `country_code`, `destination_lat`, `destination_lng` are persisted from the request body. |
| 3 | `test_create_trip_enforces_free_tier_cap` | A free user at the active trip limit gets 402 when creating another trip. |
| 4 | `test_list_trips_returns_only_own` | GET /trips returns only trips the authenticated user is a member of. |
| 5 | `test_get_trip_detail` | GET /trips/{trip_id} returns full trip data including members count. |
| 6 | `test_get_trip_non_member_403` | A user not in the trip gets 403. |
| 7 | `test_patch_trip_admin_only` | Only admin-role members can PATCH trip fields (name, dates). Non-admins get 403. |
| 8 | `test_patch_trip_updates_fields` | PATCH /trips/{trip_id} updates name, start_date, end_date, timezone. |
| 9 | `test_delete_trip_admin_only` | Only the admin can DELETE a trip. Non-admins and non-members get 403. |
| 10 | `test_delete_trip_cascades_children` | Deleting a trip removes associated TripMembers, TripDays, TimelineItems, IdeaBinItems, BrainstormBinItems, BrainstormMessages, ConciergeMessages. |
| 11 | `test_trip_with_group_attachment` | A trip created with `group_id` sets `Trip.group_id` and appears in the group's trip list. |
| 12 | `test_full_trip_lifecycle` | End-to-end: create trip → invite member → add event → fire ripple → delete; asserts state and access at each step. |
| 13 | `test_view_only_cannot_mutate` | A `view_only` member is blocked (403) from creating/updating/deleting events and ideas. |
| 14 | `test_idor_across_trips` | A member of Trip A cannot read or mutate Trip B's events/ideas/days by ID (cross-trip IDOR). |
| 15 | `test_ripple_then_day_delete_bin_reflects_shifted_time` | After a ripple shifts events, deleting the day moves events to the bin with their **post-shift** times preserved. |
| 16 | `test_idea_timeline_bin_timeline_round_trip` | Idea → event → bin → event round-trip preserves all PlaceFields end-to-end (field survival). |
| 17 | `test_create_trip_with_start_date_auto_creates_day1` | POST /trips with a `start_date` auto-creates Day 1 (`day_number=1`, `date=start_date`). |
| 18 | `test_create_trip_without_start_date_creates_no_days` | POST /trips with no `start_date` creates the trip but zero TripDays. |
| 19 | `test_create_trip_syncs_end_date_from_days` | After Day 1 is created, `_sync_trip_end_date` sets `end_date` to the last day's date. |
| 20 | `test_patch_trip_start_date_shift_forward_moves_days_and_events` | Moving `start_date` later shifts every TripDay **and** its events' `day_date` by the delta (processed latest-first, no unique-constraint collision). |
| 21 | `test_patch_trip_start_date_shift_backward_moves_days_and_events` | Moving `start_date` earlier shifts days/events by the negative delta (processed earliest-first). |
| 22 | `test_patch_trip_null_start_rebases_days_by_day_number` | When the trip had no prior `start_date`, PATCH rebases each TripDay to `new_start + (day_number-1)` and rewrites event `day_date`s. |
| 23 | `test_patch_trip_syncs_end_date_after_start_change` | A `start_date` change re-runs `_sync_trip_end_date` so `end_date` tracks the shifted last day. |
| 24 | `test_patch_trip_end_date_or_timezone_only_no_day_shift` | PATCHing only `end_date`/`timezone` updates the trip without shifting any days. |
| 25 | `test_patch_trip_not_found_404` | PATCH on a trip_id the admin caller is a member of but which does not exist returns 404. |

---

## 4. Trip Members & Invitations

### Integration Tests — `tests/integration/test_trip_members.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_invite_user_creates_pending_member` | POST /trips/{id}/invite creates a TripMember with `status=invited`. |
| 2 | `test_invite_creates_notification_for_invitee` | The invitee receives a TRIP_INVITED notification. |
| 3 | `test_invite_duplicate_idempotent` | Inviting the same user twice does not create duplicate rows. |
| 4 | `test_accept_invitation_sets_accepted` | POST /invitations/{member_id}/accept flips status to `accepted`. |
| 5 | `test_accept_invitation_creates_notification` | Accepting an invitation notifies existing trip members. |
| 6 | `test_accept_already_accepted_404` | Accepting an already-accepted invitation returns 404. |
| 7 | `test_accept_foreign_invitation_404` | A user cannot accept another user's invitation. |
| 8 | `test_decline_invitation_removes_member` | DELETE /invitations/{member_id}/decline removes the TripMember row. |
| 9 | `test_list_pending_invitations` | GET /trips/invitations/pending returns only `status=invited` rows for the current user. |
| 10 | `test_change_member_role_admin_only` | PATCH /trips/{id}/members/{mid}/role requires admin role. Non-admins get 403. |
| 11 | `test_change_member_role_updates_role` | Admin can change a member's role from `view_only` to `view_with_vote`. |
| 12 | `test_remove_member_admin_only` | DELETE /trips/{id}/members/{mid} requires admin role. |
| 13 | `test_remove_member_deletes_row` | Removing a member deletes their TripMember row. |
| 14 | `test_list_trip_members` | GET /trips/{id}/members returns all members with roles and statuses. |
| 15 | `test_non_member_cannot_list_members` | A user not in the trip gets 403 on /trips/{id}/members. |

---

## 5. Trip Days

### Integration Tests — `tests/integration/test_trip_days.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_create_trip_day` | POST /trips/{id}/days creates a TripDay row with the correct date and day_number. |
| 2 | `test_create_duplicate_day_fails` | Creating a day with a date that already exists for this trip violates the unique constraint. |
| 3 | `test_list_trip_days_ordered` | GET /trips/{id}/days returns days ordered by date ascending. |
| 4 | `test_delete_trip_day_moves_events_to_bin` | DELETE /trips/{id}/days/{day_id} moves all events on that day to the idea bin and deletes the day. |
| 5 | `test_delete_trip_day_preserves_place_fields` | Events moved to bin during day deletion retain all PlaceFields (lat, lng, place_id, photo_url, etc.). |
| 6 | `test_delete_trip_day_transfers_votes` | EventVotes on events being moved to bin are converted to IdeaVotes on the resulting IdeaBinItems. |
| 7 | `test_delete_trip_day_non_member_403` | A non-member cannot delete a trip day. |
| 8 | `test_delete_day_action_bin_restores_to_idea_bin` | `items_action="bin"` (default) moves the day's events to the idea bin (`trips.py:954`). |
| 9 | `test_delete_day_action_delete_permanent_no_idea_items` | `items_action="delete"` permanently removes the day's events — no IdeaBinItems are created. |
| 10 | `test_day_delete_action_delete_creates_no_idea_votes` | With `items_action="delete"`, no EventVotes are converted to IdeaVotes (events are gone, not binned). |

---

## 6. Events (Timeline Items)

### Integration Tests — `tests/integration/test_events.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_create_event_basic` | POST /events with valid fields creates a TimelineItem and returns it with vote tallies. |
| 2 | `test_create_event_non_member_403` | A user not in the trip gets 403 on event creation. |
| 3 | `test_create_event_from_source_idea` | When `source_idea_id` is set, the event inherits all PlaceFields from the source IdeaBinItem. |
| 4 | `test_create_event_from_idea_transfers_votes` | IdeaVotes on the source idea are transferred to EventVotes on the new event. |
| 5 | `test_create_event_from_idea_removes_source` | After promotion, the source IdeaBinItem is deleted. |
| 6 | `test_create_event_emits_notification` | Creating an event emits EVENT_ADDED to all trip members except the creator. |
| 7 | `test_update_event_fields` | PATCH /events/{id} updates title, day_date, start_time, end_time, sort_order, time_category, is_skipped. |
| 8 | `test_update_event_non_member_403` | A non-member cannot update an event. |
| 9 | `test_update_event_nonexistent_404` | PATCH on a non-existent event_id returns 404. |
| 10 | `test_update_event_time_change_emits_notification` | Changing day_date or start_time emits EVENT_MOVED notification. |
| 11 | `test_update_event_overnight_rejected_422` | Setting end_time < start_time on an event returns 422 "Overnight events not supported". |
| 12 | `test_delete_event` | DELETE /events/{id} removes the TimelineItem and emits EVENT_REMOVED notification. |
| 13 | `test_delete_event_non_member_403` | A non-member cannot delete an event. |
| 14 | `test_delete_event_nonexistent_404` | DELETE on a non-existent event returns 404. |
| 15 | `test_move_event_to_bin` | POST /events/{id}/move-to-bin creates an IdeaBinItem with all PlaceFields, transfers votes, and deletes the event. |
| 16 | `test_move_event_to_bin_preserves_enrichment_fields` | All Google Maps enrichment fields (place_id, lat, lng, address, photo_url, rating, price_level, types) survive the event-to-idea transfer. |
| 17 | `test_move_event_to_bin_emits_notification` | Moving to bin emits EVENT_REMOVED with `moved_to_bin=True`. |
| 18 | `test_get_events_for_trip` | GET /events?trip_id=X returns all events with vote tallies attached. |
| 19 | `test_get_events_non_member_403` | A non-member cannot list events for a trip. |
| 20 | `test_get_events_empty_trip` | An empty trip returns an empty list (not an error). |

---

## 7. Idea Bin

### Integration Tests — `tests/integration/test_idea_bin.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_list_ideas_for_trip` | GET /trips/{id}/ideas returns all IdeaBinItems for the trip with vote tallies. |
| 2 | `test_list_ideas_non_member_403` | A non-member cannot list ideas. |
| 3 | `test_ingest_ideas_bulk` | POST /trips/{id}/ingest with a list of items creates multiple IdeaBinItems in one call. |
| 4 | `test_ingest_ideas_enrichment_fields_persisted` | Bulk-ingested ideas retain all PlaceFields including `added_by`. |
| 5 | `test_ingest_ideas_non_member_403` | A non-member cannot ingest ideas. |
| 6 | `test_delete_idea` | DELETE /trips/{id}/ideas/{idea_id} removes the IdeaBinItem row. |
| 7 | `test_delete_idea_non_member_403` | A non-member cannot delete an idea. |
| 8 | `test_delete_nonexistent_idea_404` | Deleting a non-existent idea returns 404. |
| 9 | `test_update_idea_fields` | PATCH /trips/{id}/ideas/{idea_id} updates mutable fields on the idea. |
| 10 | `test_idea_bin_service_ingest_from_text` | `IdeaBinService.ingest_from_text` splits comma/newline-separated text into individual items and attempts Maps enrichment on each. |
| 11 | `test_idea_bin_service_maps_failure_fallback` | When `find_place` raises, the item is still created with the raw title. |

---

## 8. Brainstorm Chat & Bin

### Integration Tests — `tests/integration/test_brainstorm.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_chat_returns_ai_response` | POST /brainstorm/chat with a mocked LLM returns an assistant message and persists both user and assistant BrainstormMessage rows. |
| 2 | `test_chat_multi_turn_history_grows` | Each successive chat call appends messages; GET /brainstorm/messages returns the full ordered history. |
| 3 | `test_chat_non_member_403` | A user not in the trip cannot send chat messages. |
| 4 | `test_chat_empty_message_accepted` | The API currently accepts empty messages (no min_length validation). |
| 5 | `test_chat_enforces_brainstorm_quota` | A free user at the monthly brainstorm cap gets 402 on the next chat call. |
| 6 | `test_extract_returns_structured_items` | POST /brainstorm/extract with a mocked LLM returns brainstorm bin items extracted from chat history. |
| 7 | `test_extract_idempotent_no_duplicates` | Calling extract twice on the same chat history does not create duplicate items (messages are stamped with `extracted_at`). |
| 8 | `test_extract_fallback_when_llm_disabled` | When `LLM_ENABLED=False`, extract returns deterministic fallback items. |
| 9 | `test_bulk_insert_seeds_bin` | POST /brainstorm/bulk with pre-formatted items inserts them into BrainstormBinItem with `added_by=AI`. |
| 10 | `test_bulk_insert_non_member_403` | A non-member cannot bulk-insert brainstorm items. |
| 11 | `test_bulk_insert_preserves_all_enriched_fields` | All PlaceFields on bulk-inserted items are persisted correctly. |
| 12 | `test_promote_items_to_idea_bin` | POST /brainstorm/promote moves selected BrainstormBinItems to the shared IdeaBinItem table. |
| 13 | `test_promote_non_admin_succeeds` | A non-admin trip member can promote from their own brainstorm bin. |
| 14 | `test_promote_same_item_twice_404` | Promoting an already-promoted (deleted) item returns 404. |
| 15 | `test_promote_does_not_affect_chat_history` | Promoting items does not alter BrainstormMessage rows. |
| 16 | `test_promote_emits_notification` | Promoting notifies other trip members with BRAINSTORM_PROMOTED; promoter is excluded. |
| 17 | `test_promote_solo_no_notification` | If the user is the only trip member, no notification is emitted. |
| 18 | `test_get_brainstorm_items` | GET /brainstorm/items returns only the current user's BrainstormBinItems for this trip. |
| 19 | `test_get_brainstorm_messages` | GET /brainstorm/messages returns ordered chat history for the current user in this trip. |
| 20 | `test_seed_initial_message` | POST /brainstorm/messages/seed creates the first assistant greeting message. |
| 21 | `test_delete_all_brainstorm_items` | DELETE /brainstorm/items clears all BrainstormBinItems for the user in this trip. |
| 22 | `test_delete_single_brainstorm_item` | DELETE /brainstorm/items/{item_id} removes only the specified item. |
| 23 | `test_brainstorm_items_visible_only_to_owner` | User A's brainstorm items are not visible to User B via GET /brainstorm/items. |

### Integration Tests — `tests/integration/test_brainstorm_lifecycle.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_chat_to_extract_to_promote_full_flow` | End-to-end: chat → extract items from chat → promote to idea bin → verify ideas visible to all members. |
| 2 | `test_promoted_ideas_surface_in_group_library` | Ideas promoted into a trip that is attached to a group appear in that group's idea library. |
| 3 | `test_empty_name_user_added_by_fallback` | If the promoter has no `name`, `added_by` falls back to `user:{id}`. |
| 4 | `test_dashboard_plan_create_seed_e2e` | Dashboard plan-trip → create trip → seed brainstorm flow produces a usable trip with seeded items. |
| 5 | `test_promote_then_vote` | After promoting a brainstorm item to the idea bin, the resulting idea can be voted on and tallies update. |
| 6 | `test_promote_time_category_carries_to_idea` | The `time_category` on a promoted brainstorm item carries through to the created IdeaBinItem. |

---

## 9. Concierge

### Integration Tests — `tests/integration/test_concierge_executor.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_executor_skip_event` | `execute(intent="skip_event")` sets `is_skipped=True` on the target event and returns the updated event dict. |
| 2 | `test_executor_skip_event_missing_id` | Missing `event_id` in params returns `{"success": false, "message": "Missing event_id"}`. |
| 3 | `test_executor_skip_event_not_found` | An event_id not belonging to the trip returns `{"success": false}`. |
| 4 | `test_executor_shift_timeline` | `execute(intent="shift_timeline")` invokes SmartRippleEngine and returns the list of shifted events. |
| 5 | `test_executor_shift_timeline_no_events` | Shifting when no events match returns `{"success": true, "updated_events": []}`. |
| 6 | `test_executor_move_event_new_time` | `execute(intent="move_event")` updates start_time and preserves duration (end_time = start_time + original duration). |
| 7 | `test_executor_move_event_new_day` | Moving an event to a new `day_date` updates the field correctly. |
| 8 | `test_executor_move_event_not_found` | Moving a non-existent event returns `{"success": false}`. |
| 9 | `test_executor_add_event` | `execute(intent="add_event")` creates a new TimelineItem with the provided title, time, and place data. |
| 10 | `test_executor_add_event_missing_title` | Missing title returns `{"success": false, "message": "Missing title"}`. |
| 11 | `test_executor_add_event_defaults_to_today` | If `day_date` is not provided, it defaults to today in the trip's timezone. |
| 12 | `test_executor_add_event_auto_end_time` | If only `start_time` is provided, `end_time` defaults to start_time + 1 hour. |
| 13 | `test_executor_find_nearby_adds_event_and_ripples` | `execute(intent="find_nearby")` creates an event from place data and triggers SmartRippleEngine for subsequent events. |
| 14 | `test_executor_find_nearby_missing_title` | Missing title returns `{"success": false}`. |
| 15 | `test_executor_find_nearby_default_start_time` | If no `start_time` is given, defaults to now + 15 minutes in trip-local time. |
| 16 | `test_executor_find_nearby_category_from_types` | `_category_from_types` maps Google Places types to human-friendly categories (e.g., "restaurant" → "Food & Dining"). |
| 17 | `test_executor_unknown_intent` | An unrecognized intent returns `{"success": false, "message": "Unknown intent: ..."}`. |
| 18 | `test_executor_parse_time_param_iso` | `_parse_time_param` correctly parses full ISO datetime strings and converts them to trip-local wall-clock time. |
| 19 | `test_executor_parse_time_param_bare` | `_parse_time_param` parses bare `HH:MM` and `HH:MM:SS` strings. |

### Integration Tests — `tests/integration/test_concierge_api.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_concierge_chat_returns_intent` | POST /concierge/{trip_id}/chat (mocked LLM) returns a ConciergeChatResponse with intent, user_message, and params. |
| 2 | `test_concierge_chat_persists_messages` | Both user and assistant messages are stored in ConciergeMessage table. |
| 3 | `test_concierge_chat_non_member_403` | Non-member of the trip gets 403. |
| 4 | `test_concierge_chat_free_user_402` | Free-tier user gets 402 `needs_plus` on concierge chat. |
| 5 | `test_concierge_chat_tutorial_canned_replies` | For a tutorial trip, responses come from `CANNED_CONCIERGE_REPLIES` without hitting the LLM. |
| 6 | `test_concierge_chat_completed_tutorial_423` | A completed tutorial trip returns 423 `tutorial_locked`. |
| 7 | `test_concierge_execute_confirm_action` | POST /concierge/{trip_id}/execute dispatches to the executor and returns success + updated events. |
| 8 | `test_concierge_execute_non_member_403` | Non-member cannot execute concierge actions. |
| 9 | `test_concierge_execute_free_user_402` | Free-tier user gets 402 on execute. |
| 10 | `test_concierge_find_nearby_returns_place_cards` | POST /concierge/{trip_id}/find-nearby (mocked Maps) returns PlaceCards with travel_time and distance. |
| 11 | `test_concierge_find_nearby_non_member_403` | Non-member gets 403. |
| 12 | `test_concierge_skip_event_sets_flag` | POST /concierge/{trip_id}/skip-event marks the event skipped and persists a system message. |
| 13 | `test_concierge_whats_next_current_and_upcoming` | GET /concierge/{trip_id}/whats-next returns current_event, next_event, time_until_next, and travel_time_to_next. |
| 14 | `test_concierge_whats_next_no_events` | When no events exist for today, returns nulls for all fields. |
| 15 | `test_concierge_whats_next_skipped_events_excluded` | Skipped events do not appear as current or next. |
| 16 | `test_concierge_today_summary` | GET /concierge/{trip_id}/today-summary returns date, totals, and per-event status (completed/ongoing/upcoming/skipped). |
| 17 | `test_concierge_today_summary_empty_day` | An empty day returns `total_events=0`. |
| 18 | `test_concierge_chat_history_limited` | Chat history loaded for LLM context is limited to the last 10 messages. |

---

## 10. Votes & Vote Transfer

### Integration Tests — `tests/integration/test_votes.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_vote_on_idea_upvote` | POST /ideas/{id}/vote with value=+1 creates an IdeaVote row. |
| 2 | `test_vote_on_idea_downvote` | POST /ideas/{id}/vote with value=-1 creates an IdeaVote row. |
| 3 | `test_vote_on_idea_toggle_off` | POST /ideas/{id}/vote with value=0 removes the vote row. |
| 4 | `test_vote_on_idea_change_vote` | Switching from +1 to -1 updates the existing row in-place. |
| 5 | `test_vote_on_idea_view_only_403` | A `view_only` member cannot vote — gets 403. |
| 6 | `test_vote_on_idea_view_with_vote_allowed` | A `view_with_vote` member can vote. |
| 7 | `test_vote_on_idea_non_member_403` | A non-member cannot vote. |
| 8 | `test_get_idea_vote_tally` | GET /ideas/{id}/votes returns `{up, down, my_vote}`. |
| 9 | `test_get_idea_voters` | GET /ideas/{id}/voters returns the list of voters with their values. |
| 10 | `test_vote_on_event` | POST /events/{id}/vote creates an EventVote row. |
| 11 | `test_get_event_vote_tally` | GET /events/{id}/votes returns `{up, down, my_vote}`. |
| 12 | `test_get_event_voters` | GET /events/{id}/voters returns the voter list. |
| 13 | `test_tally_votes_batch_query` | `tally_votes()` computes up/down/my_vote for a batch of target IDs in a single query. |
| 14 | `test_tally_votes_empty_ids` | Passing an empty target_ids list returns an empty dict (no DB query). |

### Integration Tests — `tests/integration/test_vote_transfer.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_idea_to_event_vote_transfer` | Creating an event from a source idea transfers IdeaVotes to EventVotes. |
| 2 | `test_event_to_bin_vote_transfer` | Moving an event to bin transfers EventVotes to IdeaVotes on the new idea. |
| 3 | `test_day_delete_vote_transfer` | Deleting a day moves events to bin and preserves votes as IdeaVotes. |
| 4 | `test_vote_transfer_does_not_delete_source_rows` | Source vote rows (IdeaVote) are not deleted by the transfer — they become orphaned only when the source entity is deleted by cascade. |
| 5 | `test_round_trip_idea_event_bin_event` | Idea → event → bin → event round-trip preserves vote counts at each step. |
| 6 | `test_enrichment_fields_survive_vote_transfer` | All Google Maps enrichment fields survive the event → idea bin transfer. |
| 7 | `test_idea_to_event_preserves_per_user_values` | Each voter's individual +1/-1 value is preserved (not collapsed) when idea votes become event votes. |
| 8 | `test_event_created_without_source` | An event created without a `source_idea_id` starts with zero votes. |
| 9 | `test_move_to_bin_preserves_up_and_down` | Moving an event to the bin preserves both up and down counts on the resulting idea. |
| 10 | `test_move_to_bin_no_votes_clean` | Moving an event with no votes to the bin creates an idea with a clean zero tally. |
| 11 | `test_move_to_bin_shows_in_group_library_with_tally` | An event moved to the bin surfaces in the group library carrying its transferred vote tally. |
| 12 | `test_create_event_response_includes_transferred_votes` | The create-event response body includes the vote tally transferred from the source idea. |
| 13 | `test_create_event_response_zero_votes_without_source` | The create-event response shows a zero tally when there is no source idea. |
| 14 | `test_move_to_bin_response_includes_votes` | The move-to-bin response body includes the transferred vote tally. |
| 15 | `test_move_to_bin_my_vote_reflects_caller` | `my_vote` in the move-to-bin response reflects the calling user's own vote. |
| 16 | `test_day_delete_bin_preserves_multi_user_votes` | Deleting a day preserves votes from multiple distinct users on the binned ideas. |
| 17 | `test_day_delete_bin_zero_votes_clean` | Deleting a day with unvoted events yields ideas with clean zero tallies. |
| 18 | `test_day_delete_bin_roundtrip_votes_on_idea` | Votes survive a day-delete → bin → re-add round-trip and remain queryable on the idea. |

---

## 11. Notifications

### Integration Tests — `tests/integration/test_notifications.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_list_notifications_paginated` | GET /notifications?before_id=X returns pages of notifications in reverse-chronological order. |
| 2 | `test_list_notifications_isolated_between_users` | User A's notifications do not appear in User B's list. |
| 3 | `test_unread_count` | GET /notifications/unread-count returns the number of notifications with `read_at=NULL`. |
| 4 | `test_mark_one_as_read` | POST /notifications/{id}/read sets `read_at` and decrements unread count. |
| 5 | `test_mark_all_as_read` | POST /notifications/mark-all-read sets `read_at` on all unread notifications for the user. |
| 6 | `test_trip_created_notification` | Creating a trip emits TRIP_CREATED to the creator. |
| 7 | `test_invite_notification_payload` | Trip invitation emits TRIP_INVITED with trip_id and trip_name in the payload. |
| 8 | `test_accept_fanout_notifications` | Accepting an invitation fans out notifications to all existing members. |
| 9 | `test_event_added_notification_excludes_actor` | EVENT_ADDED notifies all members except the one who created the event. |
| 10 | `test_event_moved_notification` | EVENT_MOVED is emitted when start_time or day_date changes. |
| 11 | `test_event_removed_notification` | EVENT_REMOVED is emitted on event deletion or move-to-bin. |
| 12 | `test_ripple_fired_notification` | RIPPLE_FIRED notification includes `delta_minutes` and `shifted_count`. |
| 13 | `test_brainstorm_promote_notification_excludes_promoter` | The promoter does not receive BRAINSTORM_PROMOTED; other members do. |
| 14 | `test_disabled_notification_type_silently_skipped` | If a NotificationType is not in ENABLED, `emit()` is a silent no-op. |
| 15 | `test_notification_actor_summary` | Notification payload includes actor user info (name, avatar_url). |

### Integration Tests — `tests/integration/test_notification_fanout.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_full_trip_lifecycle_notification_count` | End-to-end: create trip → invite 2 users → accept → add event → fire ripple → verify total notification count per user. |
| 2 | `test_group_invite_notification` | Inviting a user to a group emits GROUP_INVITED. |
| 3 | `test_group_accept_notification` | Accepting a group invitation notifies the group owner. |
| 4 | `test_trip_renamed_fanout` | Renaming a trip fans out a TRIP_UPDATED notification to all members except the actor. |
| 5 | `test_trip_date_changed_fanout` | Changing a trip's start/end dates fans out to all members except the actor. |
| 6 | `test_trip_deleted_fanout` | Deleting a trip notifies all members that the trip was removed. |
| 7 | `test_invite_declined_to_admins` | Declining a trip invitation notifies the trip's admins. |
| 8 | `test_role_changed_notifies_target` | Changing a member's role notifies the targeted member. |
| 9 | `test_member_removed_two_shapes` | Removing a member emits one notification shape to the removed user and another to remaining members. |
| 10 | `test_group_created_self_only` | Creating a group notifies only the creator (GROUP_CREATED, self-only). |
| 11 | `test_brainstorm_promote_notification_payload` | The BRAINSTORM_PROMOTED payload carries item count, trip_id, and actor summary. |

---

## 12. Groups

### Integration Tests — `tests/integration/test_groups.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_create_group` | POST /groups creates a Group and auto-adds the creator as admin GroupMember. |
| 2 | `test_list_groups` | GET /groups returns only groups the user is a member of. |
| 3 | `test_get_group_detail` | GET /groups/{id} returns group name, owner, and member count. |
| 4 | `test_update_group` | PATCH /groups/{id} updates group name. |
| 5 | `test_delete_group_admin_only` | Only admin can delete the group. Non-admins get 403. |
| 6 | `test_invite_to_group` | POST /groups/{id}/invite creates a pending GroupMember. |
| 7 | `test_accept_group_invite` | POST /groups/invitations/{member_id}/accept flips status to `accepted`. |
| 8 | `test_decline_group_invite` | DELETE /groups/invitations/{member_id}/decline removes the GroupMember row. |
| 9 | `test_list_pending_group_invitations` | GET /groups/invitations/pending returns only the user's pending group invites. |
| 10 | `test_change_group_member_role` | PATCH /groups/{id}/members/{mid}/role updates the role. |
| 11 | `test_remove_group_member` | DELETE /groups/{id}/members/{mid} removes the member. |
| 12 | `test_list_group_members` | GET /groups/{id}/members returns all members with roles. |
| 13 | `test_attach_trip_to_group` | POST /groups/{id}/trips/{trip_id} sets `Trip.group_id`. |
| 14 | `test_detach_trip_from_group` | DELETE /groups/{id}/trips/{trip_id} clears `Trip.group_id`. |
| 15 | `test_list_group_trips` | GET /groups/{id}/trips returns all trips attached to the group. |
| 16 | `test_group_idor_blocked` | A user in Group A cannot read Group B's data. |

### Integration Tests — `tests/integration/test_group_library.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_group_idea_library_aggregates_across_trips` | GET /groups/{id}/ideas returns IdeaBinItems from all trips attached to the group. |
| 2 | `test_group_idea_library_empty_when_no_ideas` | A group with no trip ideas returns an empty list. |
| 3 | `test_group_tags_summary` | GET /groups/{id}/tags returns tag counts aggregated across the group's ideas. |
| 4 | `test_group_tags_empty_when_no_tags` | A group with no tagged ideas returns an empty tag list. |
| 5 | `test_detach_trip_removes_ideas_from_library` | After detaching a trip, its ideas no longer appear in the group library. |
| 6 | `test_ingested_ideas_surface_in_group_library` | Ideas added to a trip via brainstorm promote or bulk ingest appear in the group's library. |

### Integration Tests — `tests/integration/test_group_lifecycle.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_full_group_lifecycle` | Create group → invite member → accept → attach trip → verify library → detach → delete group. |
| 2 | `test_group_trip_members_overlap` | Verify that group membership and trip membership are independent — a group member does not auto-become a trip member. |
| 3 | `test_trip_delete_while_attached` | Deleting a trip that is attached to a group cleanly removes it from the group's trip list and library. |
| 4 | `test_removed_member_loses_read_access` | A member removed from a group can no longer read that group's data (403). |

---

## 13. Maps & Enrichment

### Integration Tests — `tests/integration/test_maps_enrichment.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_enrich_item_finds_and_hydrates` | `enrich_item` calls `find_place` + `place_details` and populates place_id, lat, lng, address, rating, photo_url, types. |
| 2 | `test_enrich_item_skips_already_enriched` | Items with an existing `place_id` are returned as-is (idempotent). |
| 3 | `test_enrich_item_empty_title_skipped` | Items with no title are returned unmodified. |
| 4 | `test_enrich_item_find_place_returns_none` | When `find_place` returns None, the item is returned with original data intact. |
| 5 | `test_enrich_item_details_fallback` | When `place_details` fails but `find_place` succeeds, `_apply_find_place_fallback` populates partial fields. |
| 6 | `test_enrich_item_quota_exceeded_sets_reason` | A 429 response sets `_last_failure_reason = "quota_exceeded"`. |
| 7 | `test_enrich_item_network_error_sets_reason` | A network error sets `_last_failure_reason = "network_error"`. |
| 8 | `test_enrich_items_batch_concurrency` | `enrich_items` processes items with bounded concurrency (semaphore = 5). |
| 9 | `test_enrich_items_no_api_key_skips` | When `api_key` is None and `_mock=False`, all items are returned unenriched and a `no_api_key` tracker call is recorded. |
| 10 | `test_enrich_items_with_summary_full` | When all items are enriched, summary returns `status=full`. |
| 11 | `test_enrich_items_with_summary_partial` | When some items fail, summary returns `status=partial`. |
| 12 | `test_enrich_items_with_summary_none` | When no items are enriched, summary returns `status=none`. |
| 13 | `test_enrich_items_with_summary_breaker_open` | When the circuit breaker is open, enrichment is skipped and reason is `breaker_open`. |
| 14 | `test_location_context_fingerprint` | `LocationContext.fingerprint()` returns a stable cache-key when lat/lng/country_code are set. |
| 15 | `test_location_context_no_bias` | A LocationContext with no lat/lng and no country_code returns `fingerprint()=None`. |
| 16 | `test_nearby_search_returns_place_cards` | `nearby_search` (mocked) returns normalized place card dicts with required keys. |
| 17 | `test_timezone_for_cached` | A cached timezone lookup returns immediately without an API call. |
| 18 | `test_timezone_for_miss_calls_api` | A cache miss calls the Time Zone API and caches the result. |

### Integration Tests — `tests/integration/test_maps_http.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_request_with_retry_success` | A successful first attempt returns the JSON body with `attempts=1`. |
| 2 | `test_request_with_retry_retries_on_500` | A 500 response is retried up to MAX_RETRIES times with exponential backoff. |
| 3 | `test_request_with_retry_retries_on_429` | A 429 (rate limit) response triggers retries. |
| 4 | `test_request_with_retry_gives_up_after_max` | After MAX_RETRIES failures, the last error is raised. |
| 5 | `test_request_with_retry_transport_error` | A transport error (network disconnect) triggers retries. |

> _The Maps circuit-breaker **state machine** (`test_maps_breaker.py`) is pure logic and lives in `tests/unit/test_maps_breaker.py`. Redis-backed breaker behaviour is in §26._

### Integration Tests — `tests/integration/test_maps_cache.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_directions_cache_hit` | A previously cached directions result returns `(cached_data, "hit")`. |
| 2 | `test_directions_cache_miss` | An uncached lookup returns `(MISS, "miss")`. |
| 3 | `test_directions_cache_negative` | A cached None (negative result) returns `(None, "negative")`. |
| 4 | `test_timezone_cache_hit` | A previously cached timezone returns the IANA string. |
| 5 | `test_timezone_cache_miss` | An uncached timezone lookup returns `(MISS, ...)`. |
| 6 | `test_cache_find_place_miss_then_hit` | A find_place lookup misses, populates the cache, then returns a hit on the second call. |
| 7 | `test_cache_find_place_normalises_query` | Whitespace/case-different queries normalise to the same cache key. |
| 8 | `test_cache_place_details_keyed_by_place_id_and_field_signature` | place_details cache keys include both place_id and the requested field signature. |
| 9 | `test_cache_v1_and_v2_entries_isolated` | v1 and v2 service cache entries do not collide for the same query. |
| 10 | `test_cache_directions_different_mode_isolated` | Directions cached for `driving` mode do not satisfy a `walking` mode lookup. |
| 11 | `test_clear_all_resets_everything` | `clear_all()` empties find_place, place_details, directions, and timezone caches. |

---

## 14. Routes & DayRoute Persistence

### Integration Tests — `tests/integration/test_routes.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_compute_route_returns_polyline` | POST /trips/{id}/route (mocked Directions API) returns an encoded polyline, legs, and totals. |
| 2 | `test_compute_route_requires_two_waypoints` | A route request with fewer than 2 valid waypoints returns None / empty result. |
| 3 | `test_compute_route_invalid_waypoint_skipped` | Waypoints without place_id or lat/lng are flagged and the request aborts gracefully. |
| 4 | `test_get_cached_route` | GET /trips/{id}/route returns the previously computed route from cache or DB. |
| 5 | `test_save_route_persists_day_route` | POST /trips/{id}/route/save creates/upserts a DayRoute row with encoded_polyline, legs, fingerprint. |
| 6 | `test_route_staleness_on_time_change` | Changing an event's `start_time` alters the waypoint fingerprint, making the saved route stale. |
| 7 | `test_route_not_stale_on_title_change` | Non-waypoint changes (title, description) do not affect the fingerprint. |
| 8 | `test_route_fingerprint_deterministic` | Same inputs (event lat/lng/place_id/start_time) produce the same fingerprint. |
| 9 | `test_route_excludes_events_without_location` | Events without lat/lng/place_id are excluded from the route waypoints. |
| 10 | `test_route_upsert_overwrites_existing` | Saving a route for the same (trip_id, day_date) overwrites the previous DayRoute row. |
| 11 | `test_polyline_encoding` | `encode_polyline` correctly encodes a list of lat/lng tuples into Google's polyline format. |
| 12 | `test_route_from_dict` | `route_from_dict` deserializes a raw dict into a RouteResult with typed legs. |
| 13 | `test_deleting_event_reduces_route_points` | Deleting an event removes its waypoint, reducing the recomputed route's leg count. |
| 14 | `test_route_recomputes_with_different_events` | Adding/removing events changes the waypoint set and yields a different recomputed route. |

---

## 15. Ripple Engine

### Integration Tests — `tests/integration/test_ripple_engine.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_legacy_ripple_shifts_events_by_delta` | `RippleEngine.shift_itinerary` shifts all qualifying events after `start_from_time` by `delta_minutes`. |
| 2 | `test_legacy_ripple_skips_locked_events` | Events with `is_locked=True` are not shifted. |
| 3 | `test_legacy_ripple_skips_cross_midnight` | Events that would shift past midnight in trip-local time are silently skipped. |
| 4 | `test_legacy_ripple_respects_timezone` | Shifts use the trip's IANA timezone for wall-clock arithmetic. |
| 5 | `test_smart_ripple_anchor_shift` | SmartRippleEngine shifts the anchor event by delta_minutes. |
| 6 | `test_smart_ripple_propagation_with_travel_time` | Subsequent events are shifted based on actual travel time (mocked Directions API) when the gap is insufficient. |
| 7 | `test_smart_ripple_stops_when_gap_sufficient` | Propagation stops when the gap between prev_end and curr_start exceeds travel time. |
| 8 | `test_smart_ripple_cross_midnight_raises` | A shift that would push an event to a different day raises `CrossMidnightShiftError`. |
| 9 | `test_smart_ripple_skips_locked_and_skipped` | Locked and skipped events are excluded from the ripple query. |
| 10 | `test_smart_ripple_by_event_id` | `start_from_event_id` targets a specific anchor event. |
| 11 | `test_smart_ripple_no_events_returns_empty` | An empty trip returns an empty list. |
| 12 | `test_smart_ripple_event_without_location_zero_travel` | Events without lat/lng/place_id default to 0 travel time. |
| 13 | `test_legacy_ripple_skips_past_events` | Events starting before `start_from_time` are not shifted. |
| 14 | `test_legacy_ripple_skips_events_with_none_start` | Events with `start_time=None` are skipped by the shift query. |
| 15 | `test_legacy_ripple_handles_none_end_time` | Events with `end_time=None` shift their start without raising. |
| 16 | `test_legacy_ripple_negative_delta_shifts_backward` | A negative `delta_minutes` moves qualifying events earlier. |
| 17 | `test_legacy_ripple_zero_delta_is_noop` | A `delta_minutes=0` returns the events unchanged. |
| 18 | `test_legacy_ripple_returns_ordered_by_start_time` | Shifted events are returned ordered by start_time ascending. |

> _Pure wall-clock/delta arithmetic for the Smart Ripple algorithm lives in `tests/unit/test_smart_ripple.py`; the rows above exercise the DB-backed engine (real session, mocked Directions API)._

### Integration Tests — `tests/integration/test_ripple_api.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_ripple_endpoint_admin_only` | POST /events/ripple/{trip_id} requires admin role. Non-admins get 403. |
| 2 | `test_ripple_endpoint_non_member_403` | A non-member gets 403. |
| 3 | `test_ripple_endpoint_fires_and_returns_events` | A valid ripple request returns the list of shifted events with vote tallies. |
| 4 | `test_ripple_endpoint_cross_midnight_422` | A cross-midnight shift returns 422 with structured error detail. |
| 5 | `test_ripple_endpoint_emits_notification` | Firing a ripple emits RIPPLE_FIRED notification to other trip members. |

---

## 16. Dashboard

### Integration Tests — `tests/integration/test_dashboard.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_today_widget_active_trip` | GET /dashboard/today returns a trip classified as `active` when `start_date <= today <= end_date`. |
| 2 | `test_today_widget_upcoming_trip` | A trip with `start_date > today` is classified as `upcoming`. |
| 3 | `test_today_widget_past_trip` | A trip with `end_date < today` is classified as `past`. |
| 4 | `test_today_widget_null_end_date_fallback` | `end_date=None` falls back to `start_date` — a same-day trip is active when today matches start_date. |
| 5 | `test_today_widget_null_start_date_excluded` | A trip with `start_date=None` is never classified as any state. |
| 6 | `test_today_widget_timezone_aware` | Dashboard uses trip timezone for classification, not UTC. |
| 7 | `test_today_widget_client_now_override` | The `client_now` query parameter overrides the server's "now" for classification. |
| 8 | `test_today_widget_caps_active_to_one` | When two trips are both active, only the soonest-start is surfaced. |
| 9 | `test_today_widget_caps_past_and_upcoming` | Past and upcoming trips are capped to MAX_PAST and MAX_UPCOMING respectively. |
| 10 | `test_today_widget_default_page_priority` | Default page index prioritizes: active > first upcoming > most recent past. |
| 11 | `test_today_widget_regression_2am_event` | Regression: a 2AM event must not show as up-next when client_now is 6AM. |

---

## 17. LLM ↔ DB Integration

The LLM **clients** (`BrainstormClient`, `ConciergeChatClient`, `DashboardClient`), the `BaseLLMService`,
the **dedup** filter, **fallbacks**, the **registry**, and the zero-LLM **pre-processor** are all pure /
mock-only logic and are tested in `tests/unit/` (`test_llm_clients*.py`, `test_llm_v1_service.py`,
`test_llm_dedup.py`, `test_llm_fallbacks.py`, `test_llm_registry.py`, `test_llm_pre_processor.py`).

What remains at the **integration tier** is how the LLM layer touches the database and endpoints — those
cases are catalogued where they belong rather than duplicated here:

| Behaviour | Catalogued in |
|-----------|---------------|
| Brainstorm chat/extract persist messages & bin items (mocked LLM) | §8 Brainstorm Chat & Bin |
| Concierge dispatch/chat persist messages and return intents (mocked LLM) | §9 Concierge |
| Dashboard `plan_trip` → create → seed end-to-end | §8 (`test_dashboard_plan_create_seed_e2e`) |
| User personas are packed into the LLM prompt on chat | §33 Persona ↔ LLM Interaction |
| Brainstorm extract triggers Maps enrichment on extracted items | §31 Brainstorm ↔ Maps Enrichment |
| Token usage from LLM calls is persisted and attributed | §34 Admin Persistence & Token Attribution |

---

## 18. Ideas (Tags & Copy)

### Integration Tests — `tests/integration/test_ideas_tags_copy.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_get_idea_tags` | GET /ideas/{id}/tags returns all IdeaTag rows for the idea. |
| 2 | `test_set_idea_tags` | PUT /ideas/{id}/tags replaces all tags with the new set. |
| 3 | `test_set_idea_tags_empty_clears` | Setting tags to an empty list removes all IdeaTag rows. |
| 4 | `test_copy_idea_to_another_trip` | POST /ideas/{id}/copy creates a new IdeaBinItem in the target trip with all PlaceFields preserved. |
| 5 | `test_copy_preserves_place_lat_lng_url_hint_added_by` | All enrichment fields (lat, lng, photo_url, place_id, added_by) survive the copy. |
| 6 | `test_copy_no_tags_on_source` | Tags from the source idea are not copied to the destination. |
| 7 | `test_copy_nonexistent_idea_404` | Copying a non-existent idea returns 404. |
| 8 | `test_copy_nonexistent_target_trip_forbidden` | Copying to a trip the user isn't a member of returns 403. |
| 9 | `test_copy_of_copy_keeps_original_origin` | Copying a copy preserves `origin_idea_id` pointing to the original idea. |
| 10 | `test_cross_trip_copy_preserves_all_place_fields` | Copying across trips retains all 13 PlaceFields. |

---

## 19. Users & Personas

### Integration Tests — `tests/integration/test_users.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_get_profile` | GET /users/me returns user profile with name, email, avatar_url, timezone, personas. |
| 2 | `test_update_profile` | PUT /users/me updates name, avatar_url, timezone, home_city, currency, travel_blurb. |
| 3 | `test_update_profile_partial` | Sending only `name` updates name without clearing other fields. |
| 4 | `test_delete_account` | DELETE /users/me removes the User row and cascades to owned data. |
| 5 | `test_persona_catalog_endpoint` | GET /users/personas/catalog returns all available persona entries with label, icon, description. _(The catalog data guards — 14 entries, unique slugs, <140-char descriptions — are unit-tier: `unit/test_persona_catalog.py`.)_ |
| 6 | `test_get_user_personas` | GET /users/me/personas returns the user's selected persona IDs. |
| 7 | `test_set_user_personas` | PUT /users/me/personas updates the user's `personas` JSON column. |
| 8 | `test_set_user_personas_validates_ids` | Setting personas with IDs not in the catalog is rejected or silently filtered. |

---

## 20. Tutorial & Onboarding

### Integration Tests — `tests/integration/test_tutorial.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_tutorial_status_default_not_started` | GET /tutorial/status for a new user returns `status=not_started`, `step=0`, `trip_id=None`. |
| 2 | `test_tutorial_start_seeds_trip` | POST /tutorial/start creates a tutorial trip with 3 days, 5 events, 4 ideas, 6 brainstorm items, 8 chat messages, 3 day routes, and 2 concierge messages. |
| 3 | `test_tutorial_start_idempotent` | Calling /start twice does not create duplicate tutorial trips. |
| 4 | `test_tutorial_step_advances` | PATCH /tutorial/step updates the step number. |
| 5 | `test_tutorial_step_sets_in_progress` | Patching step on a `not_started` user auto-sets status to `in_progress`. |
| 6 | `test_tutorial_skip` | POST /tutorial/skip sets `status=skipped`. |
| 7 | `test_tutorial_complete_locks_trip` | POST /tutorial/complete sets `status=completed` and `trip.is_tutorial_completed=True`. |
| 8 | `test_tutorial_completed_trip_blocks_concierge` | A completed tutorial trip returns 423 on concierge chat. |
| 9 | `test_tutorial_replay_reseeds` | POST /tutorial/replay deletes the old tutorial trip, seeds a fresh one, and resets step to 1. |
| 10 | `test_tutorial_reset_clears_state` | POST /tutorial/reset deletes the trip and sets status to `not_started`, step to 0. |
| 11 | `test_tutorial_delete_trip` | DELETE /tutorial/trip removes the tutorial trip but preserves status/step. |
| 12 | `test_tutorial_platform_independence` | Web and iOS tutorial progress are independent — advancing web step does not affect iOS step. |
| 13 | `test_tutorial_platform_header_parsing` | `X-Client-Platform: iOS` selects iOS columns; default/web selects web columns. |
| 14 | `test_tutorial_trip_bypasses_entitlement_gates` | Tutorial trips bypass active trip cap, brainstorm quota, and concierge gating. |
| 15 | `test_tutorial_canned_brainstorm_replies` | Brainstorm chat on a tutorial trip returns canned replies without LLM calls. |
| 16 | `test_tutorial_canned_concierge_replies` | Concierge chat on a tutorial trip returns canned replies without LLM calls. |

---

## 21. Admin Panel

### Integration Tests — `tests/integration/test_admin.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_admin_login_success` | POST /admin/login with valid admin credentials returns an admin JWT. |
| 2 | `test_admin_login_wrong_credentials` | Invalid credentials return 401. |
| 3 | `test_admin_jwt_rejects_regular_user` | A regular user JWT on admin endpoints returns 403. |
| 4 | `test_admin_list_users` | GET /admin/users returns paginated user list. |
| 5 | `test_admin_token_usage_summary` | GET /admin/token-usage/summary returns aggregated token usage stats. |
| 6 | `test_admin_token_usage_per_user` | GET /admin/token-usage/users returns per-user breakdowns. |
| 7 | `test_admin_token_usage_filter_options` | GET /admin/token-usage/options returns available filter dimensions. |
| 8 | `test_admin_maps_usage_summary` | GET /admin/maps-usage/summary returns aggregated Maps API usage. |
| 9 | `test_admin_maps_usage_per_user` | GET /admin/maps-usage/users returns per-user Maps usage. |

> _Pure cost math (`compute_token_cost`, `compute_maps_cost`, pricing tables) is unit-tier: `unit/test_admin_costs.py`. Cross-cutting token/maps attribution that depends on DB persistence is in §34._

---

## 22. Pagination & OpenAPI

### Integration Tests — `tests/integration/test_pagination.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_cursor_pagination_first_page` | First page returns items and a `next_cursor` if more exist. |
| 2 | `test_cursor_pagination_second_page` | Passing `before_id` returns the next page of results. |
| 3 | `test_cursor_pagination_empty` | An empty dataset returns an empty list with no cursor. |
| 4 | `test_cursor_pagination_respects_limit` | The number of items per page respects the `limit` parameter. |

### Integration Tests — `tests/integration/test_openapi_spec.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_openapi_spec_loads` | The OpenAPI JSON schema at /openapi.json is valid and parseable. |
| 2 | `test_openapi_all_routes_documented` | Every registered route has a corresponding entry in the OpenAPI spec. |

---

## 23. Google Maps Service (v1/v2/mock/factory)

### Integration Tests — `tests/integration/test_google_maps_service.py`

Mocks HTTP at the service boundary (per blueprint §4). Covers the legacy v1, new-Places v2, and mock providers plus the factory selector. _This was previously untested in the catalogue and is the single largest coverage gap._

| # | Test | Description |
|---|------|-------------|
| 1 | `test_v1_find_place_ok` | v1 `find_place` parses a candidate and returns place_id + geometry. |
| 2 | `test_v1_find_place_zero_results` | v1 `find_place` returns None when the API yields zero candidates. |
| 3 | `test_v1_place_details_ok` | v1 `place_details` returns the detail payload for a place_id. |
| 4 | `test_v1_apply_details_maps_fields` | v1 `_apply_details` maps API fields onto the item (address, rating, photo, types). |
| 5 | `test_v1_extract_place_id` | v1 `_extract_place_id` pulls the id from a candidate shape. |
| 6 | `test_v1_cache_after_first_call` | A second identical v1 lookup is served from cache (no second HTTP call). |
| 7 | `test_v2_find_place_ok` | v2 (new Places) `find_place` returns a normalized result. |
| 8 | `test_v2_find_place_zero_results` | v2 `find_place` returns None on empty results. |
| 9 | `test_v2_place_details_drops_unwanted_fields` | v2 `place_details` strips fields outside the requested field mask. |
| 10 | `test_v2_apply_details_maps_price_level_enum` | v2 maps the `priceLevel` enum string to the internal price_level integer. |
| 11 | `test_v2_extract_place_id` | v2 `_extract_place_id` reads the new-Places id form. |
| 12 | `test_v2_cache_after_first_call` | v2 second identical lookup is cached. |
| 13 | `test_mock_find_place_returns_full_shape` | The mock provider returns a fully-shaped candidate for deterministic tests. |
| 14 | `test_mock_place_details_drops_legacy_fields` | The mock `place_details` mirrors the v2 field-drop behaviour. |
| 15 | `test_mock_directions_builds_polyline` | The mock `directions` returns a synthetic encoded polyline + legs. |
| 16 | `test_mock_enrich_items_populates_place_id` | The mock `enrich_items` stamps place_id onto each item. |
| 17 | `test_backwards_compat_alias` | The legacy import alias still resolves to the current service class. |
| 18 | `test_factory_returns_mock_when_GOOGLE_MAPS_MOCK_true` | The factory returns the mock service when `GOOGLE_MAPS_MOCK=true`. |
| 19 | `test_factory_returns_v1_by_default` | With a key present and no v2 flag, the factory returns the v1 service. |
| 20 | `test_factory_returns_v2_when_configured` | The factory returns v2 when the new-Places flag is set. |
| 21 | `test_factory_falls_back_to_mock_when_key_missing` | With no API key, the factory falls back to the mock service. |
| 22 | `test_v1_apply_details_skips_rating_when_flag_off` | `FETCH_RATING=off` → v1 omits rating/price_level. |
| 23 | `test_v1_apply_details_skips_photos_when_flag_off` | `FETCH_PHOTOS=off` → v1 omits photo_url. |
| 24 | `test_v1_detail_fields_exclude_rating_when_flag_off` | v1 request field list excludes rating fields when the flag is off. |
| 25 | `test_v1_detail_fields_exclude_photos_when_flag_off` | v1 request field list excludes photo fields when the flag is off. |
| 26 | `test_v2_apply_details_skips_rating_when_flag_off` | `FETCH_RATING=off` → v2 omits rating/price_level. |
| 27 | `test_v2_apply_details_skips_photos_when_flag_off` | `FETCH_PHOTOS=off` → v2 omits photo_url. |
| 28 | `test_v2_field_mask_excludes_rating_when_flag_off` | v2 field mask excludes rating when the flag is off. |
| 29 | `test_v2_field_mask_excludes_photos_when_flag_off` | v2 field mask excludes photos when the flag is off. |
| 30 | `test_v2_field_mask_both_off` | Both flags off → v2 field mask excludes rating and photos. |
| 31 | `test_mock_apply_details_skips_rating_when_flag_off` | Mock honours `FETCH_RATING=off`. |
| 32 | `test_mock_apply_details_skips_photos_when_flag_off` | Mock honours `FETCH_PHOTOS=off`. |

---

## 24. Apple Maps Service

### Integration Tests — `tests/integration/test_apple_maps_service.py`

`app/services/apple_maps/` is an alternate Maps provider used by `maps.py`, `brainstorm.py`, and `llm.py`. Mock HTTP + token provider; **no prior coverage**.

| # | Test | Description |
|---|------|-------------|
| 1 | `test_apple_find_place_ok` | `find_place` parses an Apple results payload into a normalized candidate. |
| 2 | `test_apple_find_place_zero_results` | `find_place` returns None when Apple returns no results. |
| 3 | `test_apple_place_details_maps_fields` | `place_details` + `_apply_details` map Apple fields onto the item. |
| 4 | `test_apple_extract_place_id` | `_extract_place_id` reads Apple's identifier form. |
| 5 | `test_apple_apply_find_place_fallback` | `_apply_find_place_fallback` populates partial fields when details are missing. |
| 6 | `test_apple_nearby_search_returns_cards` | `nearby_search` returns normalized place-card dicts. |
| 7 | `test_apple_directions_api_call` | `_directions_api_call` returns route legs/polyline from a mocked response. |
| 8 | `test_apple_photo_url_builds` | `photo_url` builds a valid URL from a photo reference. |
| 9 | `test_apple_auth_header_uses_token_provider` | `_auth_headers` attaches the bearer token from `AppleMapsTokenProvider`. |
| 10 | `test_apple_token_provider_caches_and_refreshes` | The token provider caches the JWT and refreshes it after expiry. |

---

## 25. Maps Location Bias & Geocoding

### Integration Tests — `tests/integration/test_maps_location_bias.py`

Async cache-isolation and provider-backed geocoding. _Pure `LocationContext.fingerprint()` math is unit-tier (`unit/test_maps_geocoding.py`); the rows below exercise the cache + geocode provider._

| # | Test | Description |
|---|------|-------------|
| 1 | `test_cache_isolates_entries_by_fingerprint` | Cache entries are partitioned by location fingerprint — a biased read never returns an unbiased entry. |
| 2 | `test_cache_legacy_no_bias_path_unchanged` | A lookup with no location bias uses the legacy (unbiased) cache key path. |
| 3 | `test_biased_read_misses_unbiased_entry` | A biased read for a city does not hit an entry written without bias. |
| 4 | `test_mock_find_place_anchors_on_bias_lat_lng` | When a bias lat/lng is supplied, the mock `find_place` anchors its result on it. |
| 5 | `test_geocode_city_returns_centroid_via_provider` | `geocode_city` resolves a city to a centroid via the Maps provider. |
| 6 | `test_geocode_city_caches_centroid` | A second `geocode_city` for the same city is served from cache. |
| 7 | `test_geocode_city_returns_country_only_when_city_missing` | With only a country code, `geocode_city` returns the country-level bias. |
| 8 | `test_geocode_city_returns_none_when_no_signal` | With no city and no country, `geocode_city` returns None. |
| 9 | `test_enrich_item_without_location_unchanged` | Enriching an item with no location signal leaves it unchanged. |
| 10 | `test_enrich_items_accepts_location_without_error` | `enrich_items` accepts an optional LocationContext without raising. |

---

## 26. Redis Cache & Breaker

### Integration Tests — `tests/integration/test_redis_cache.py`

Redis-backed cache layer with a circuit breaker and graceful fallback to the in-memory cache. Uses a fake Redis.

| # | Test | Description |
|---|------|-------------|
| 1 | `test_redis_find_place_roundtrip` | A find_place value written to Redis is read back on the next lookup. |
| 2 | `test_redis_negative_cache` | A negative (None) result is cached and short-circuits subsequent lookups. |
| 3 | `test_redis_miss_returns_sentinel` | A cache miss returns the MISS sentinel, not None. |
| 4 | `test_redis_place_details_field_signature_isolated` | place_details entries are isolated by requested field signature. |
| 5 | `test_falls_back_to_local_when_redis_down` | When Redis is unreachable, reads/writes fall back to the local in-memory cache. |
| 6 | `test_redis_breaker_opens_after_threshold` | Consecutive Redis errors open the breaker, stopping further Redis calls. |
| 7 | `test_redis_breaker_success_closes` | A successful Redis call after cooldown closes the breaker. |
| 8 | `test_breaker_falls_back_to_local_when_redis_down` | While the breaker is open, the layer serves from the local cache. |

---

## 27. Spec Validation Middleware

### Integration Tests — `tests/integration/test_spec_validation.py`

`SpecValidationMiddleware` (RM-047) validates each request against `docs/api/openapi.yaml`. Wired in `main.py`; **no prior coverage**.

| # | Test | Description |
|---|------|-------------|
| 1 | `test_valid_request_passes_through` | A request matching the spec passes to the route handler unchanged. |
| 2 | `test_malformed_body_returns_spec_validation_error` | A body that violates the schema is rejected before reaching the handler. |
| 3 | `test_error_response_detail_prefixed_spec_validation` | The rejection response `detail` is prefixed `[SpecValidation]`. |
| 4 | `test_excluded_paths_skip_validation` | Excluded paths (docs, openapi.json, health) bypass validation. |
| 5 | `test_unknown_route_not_blocked` | A path absent from the spec is not blocked by the middleware. |

---

## 28. Notification Service (DB emit)

### Integration Tests — `tests/integration/test_notification_service.py`

Service-level `emit()` and recipient-resolution helpers against the DB. _(API-level notification behaviour is in §11.)_

| # | Test | Description |
|---|------|-------------|
| 1 | `test_emit_creates_one_row_per_unique_recipient` | `emit()` inserts exactly one Notification row per unique recipient. |
| 2 | `test_emit_drops_none_recipients` | None entries in the recipient list are dropped. |
| 3 | `test_emit_empty_recipients_is_noop` | An empty recipient list inserts nothing. |
| 4 | `test_emit_persists_all_fields` | The emitted row persists type, payload, actor, and target fields. |
| 5 | `test_emit_disabled_type_is_noop` | A NotificationType not in ENABLED produces no rows. |
| 6 | `test_is_enabled_unknown_type_defaults_true` | `is_enabled()` defaults unknown types to True. |
| 7 | `test_trip_member_ids_accepted_only_by_default` | `trip_member_ids()` returns only accepted members by default. |
| 8 | `test_trip_member_ids_accepted_only_false_includes_invited` | With `accepted_only=False`, invited members are included. |
| 9 | `test_trip_member_ids_exclude_user` | The `exclude_user` argument omits the actor from the recipient set. |
| 10 | `test_all_trip_member_ids_includes_caller` | `all_trip_member_ids()` includes the calling user. |

---

## 29. Roles & RBAC (DB)

### Integration Tests — `tests/integration/test_roles.py`

DB-backed role-resolution helpers. _(Pure `VOTE_ROLES`/`ADMIN_ONLY` constants are unit-tier: `unit/test_roles.py`.)_

| # | Test | Description |
|---|------|-------------|
| 1 | `test_get_trip_member_returns_none_for_non_member` | `get_trip_member` returns None for a user not on the trip. |
| 2 | `test_get_trip_member_returns_none_for_invited_status` | An `invited` (not yet accepted) member resolves as None for gating. |
| 3 | `test_require_trip_member_raises_for_non_member` | `require_trip_member` raises 403 for a non-member. |
| 4 | `test_require_trip_admin_accepts_admin` | `require_trip_admin` passes for an admin member. |
| 5 | `test_require_trip_admin_403_for_non_admin` | `require_trip_admin` raises 403 for non-admin roles (parametrised). |
| 6 | `test_require_vote_role_accepts` | `require_vote_role` passes for `admin` and `view_with_vote` (parametrised). |
| 7 | `test_require_vote_role_403_for_view_only` | `require_vote_role` raises 403 for `view_only`. |

---

## 30. Maps Feature-Flag Propagation

### Integration Tests — `tests/integration/test_maps_flags_propagation.py`

End-to-end propagation of `FETCH_PHOTOS` / `FETCH_RATING` from enrichment through brainstorm extract, the cache key, and admin usage visibility.

| # | Test | Description |
|---|------|-------------|
| 1 | `test_mock_enrich_FETCH_PHOTOS_off_items_lack_photo_url` | `FETCH_PHOTOS=off` → enriched items have no photo_url. |
| 2 | `test_mock_enrich_FETCH_RATING_off_items_lack_rating_and_price_level` | `FETCH_RATING=off` → enriched items have no rating/price_level. |
| 3 | `test_brainstorm_extract_FETCH_PHOTOS_off_skips_photo` | Brainstorm extract enrichment skips photos when the flag is off. |
| 4 | `test_brainstorm_extract_FETCH_RATING_off_skips_rating` | Brainstorm extract enrichment skips rating when the flag is off. |
| 5 | `test_flag_toggle_cache_entries_differ_by_field_signature` | Toggling a flag changes the field signature, producing distinct cache entries. |
| 6 | `test_admin_maps_usage_shows_photo_url_calls` | Admin maps-usage reflects photo_url detail calls when photos are fetched. |
| 7 | `test_FETCH_PHOTOS_off_no_new_photo_url_calls` | With `FETCH_PHOTOS=off`, no new photo_url detail calls appear in admin usage. |

---

## 31. Brainstorm ↔ Maps Enrichment

### Integration Tests — `tests/integration/test_brainstorm_map_enrichment.py`

Verifies that brainstorm extract drives the Maps enrichment pipeline.

| # | Test | Description |
|---|------|-------------|
| 1 | `test_brainstorm_extract_calls_enrich_items` | Extract passes the extracted items through `enrich_items`. |
| 2 | `test_brainstorm_extract_enriched_items_have_place_id` | Successfully enriched items carry a place_id into the brainstorm bin. |
| 3 | `test_brainstorm_extract_partial_enrichment_failures_skip_only_failing` | When some items fail enrichment, only the failing ones are left unenriched; the rest succeed. |

---

## 32. Brainstorm Concurrency

### Integration Tests — `tests/integration/test_brainstorm_concurrency.py`

Concurrency safety on brainstorm promote/extract (forced via gathered async calls / DB transactions).

| # | Test | Description |
|---|------|-------------|
| 1 | `test_two_concurrent_promotes_same_item_only_one_succeeds` | Two concurrent promotes of the same item create exactly one idea (the loser gets 404/no-op). |
| 2 | `test_concurrent_extract_does_not_double_insert` | Concurrent extracts on the same chat history do not double-insert bin items. |
| 3 | `test_promote_during_chat_does_not_corrupt_history` | A promote interleaved with an active chat leaves the message history intact. |

---

## 33. Persona ↔ LLM Interaction

### Integration Tests — `tests/integration/test_persona_llm_interaction.py`

User personas (DB) flow into the LLM prompt on brainstorm chat (mocked LLM captures the packed prompt).

| # | Test | Description |
|---|------|-------------|
| 1 | `test_user_with_personas_brainstorm_chat_passes_personas` | A user's selected personas are packed into the prompt sent to the LLM. |
| 2 | `test_persona_change_takes_effect_on_next_chat` | Updating personas changes what the next chat passes to the LLM. |
| 3 | `test_two_users_on_same_trip_personas_isolated_per_user` | Two members of the same trip get prompts packed with their own personas, not each other's. |
| 4 | `test_user_with_null_personas_chat_still_works` | A user with no personas chats successfully (empty persona block). |

---

## 34. Admin Persistence & Token Attribution

### Integration Tests — `tests/integration/test_admin_persistence.py`

Cross-cutting: LLM calls persist TokenUsage rows that the admin panel attributes per user, surviving user deletion.

| # | Test | Description |
|---|------|-------------|
| 1 | `test_brainstorm_chat_then_admin_token_usage_summary_reflects_call` | A brainstorm chat records token usage that the admin summary then reflects. |
| 2 | `test_two_users_usage_correctly_attributed` | Token usage from two users is attributed to the correct user in the per-user breakdown. |
| 3 | `test_user_deleted_orphans_token_usage_visible_as_unattributed` | Deleting a user leaves their token rows, shown as unattributed in admin. |
| 4 | `test_admin_login_does_not_create_token_usage_row` | Admin login performs no LLM call and creates no TokenUsage row. |
| 5 | `test_user_register_login_chat_admin_summary_full_loop` | Full loop: register → login → chat → admin summary reflects the user's usage. |
| 6 | `test_user_delete_then_admin_summary_marks_rows_unattributed` | After deleting a user, the admin summary marks their historical rows unattributed. |

---

## 35. Smoke Tests

All smoke tests live in `tests/smoke/` and make **real network calls** to live systems. They are excluded from the standard CI pipeline and run post-deployment or on manual trigger.

### `tests/smoke/test_health.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_health_endpoint_200` | GET /health (or /status) on the live deployment returns 200 with `{"status": "ok"}`. |
| 2 | `test_openapi_spec_accessible` | GET /openapi.json on the live deployment returns 200 and valid JSON. |

### `tests/smoke/test_database_connectivity.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_postgres_connection_alive` | A raw SQL `SELECT 1` against the production PostgreSQL DSN succeeds within 5 seconds. |
| 2 | `test_postgres_migrations_applied` | The `user` and `trip` tables exist in the `public` schema (confirms migrations ran). |
| 3 | `test_postgres_test_entity_readable` | A designated read-only test row (e.g., a seed user or canary trip) is queryable, confirming schema integrity. |

### `tests/smoke/test_redis_connectivity.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_redis_ping` | `redis.ping()` against the production Redis URL returns `True`. |
| 2 | `test_redis_set_get_roundtrip` | SET a smoke-test key, GET it, DELETE it — confirms read/write works. |

### `tests/smoke/test_external_apis.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_google_maps_api_key_valid` | A minimal `findPlace` call with the production API key returns a 200 (not 403 key_invalid). |
| 2 | `test_google_maps_directions_reachable` | A simple directions call between two known place_ids returns a route. |
| 3 | `test_openai_api_key_valid` | A minimal completions call (1 token) to OpenAI verifies the key is active. |
| 4 | `test_anthropic_api_key_valid` | A minimal call to the Anthropic API verifies the key is active. |
| 5 | `test_google_genai_api_key_valid` | A minimal call to Google GenAI verifies the key is active. |
| 6 | `test_razorpay_credentials_valid` | `razorpay_client.plan.all()` with production keys returns without auth error. |

### `tests/smoke/test_auth_flow.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_signup_login_refresh_cycle` | Full auth cycle against the live deployment: signup → verify (mocked or test token) → login → refresh → verify token works → logout. |
| 2 | `test_jwt_decode_with_production_secret` | A locally-minted JWT with the production SECRET_KEY is accepted by the live `/auth/me` endpoint. |

### `tests/smoke/test_critical_paths.py`

| # | Test | Description |
|---|------|-------------|
| 1 | `test_create_and_delete_trip` | Create a trip on the live API, verify it appears in /trips, delete it. |
| 2 | `test_brainstorm_chat_responds` | Send a brainstorm chat message to a live trip and verify the AI responds with valid JSON. |
| 3 | `test_plan_trip_endpoint` | POST /llm/plan-trip returns a structured trip preview on the live deployment. |
| 4 | `test_billing_status_accessible` | GET /billing/status returns a valid entitlement DTO (not 500). |
| 5 | `test_admin_login_accessible` | POST /admin/login with test admin credentials returns a token. |

---

## 36. Scale & Performance Tests (Locust)

All scale tests live in `tests/scale/` and use **Locust** for load generation. They are never run in CI — only in dedicated performance environments.

### `tests/scale/locustfile_trips.py`

| # | Test / TaskSet | Description |
|---|----------------|-------------|
| 1 | `TripCRUDUser` | Simulates a user creating, listing, updating, and deleting trips in rapid succession. Measures p50/p95/p99 latency under 100-500 concurrent users. |
| 2 | `test_concurrent_trip_creation_saturation` | 200 concurrent users each create a trip simultaneously. Verifies no 500s and connection pool doesn't exhaust. |
| 3 | `test_concurrent_event_mutations_on_same_trip` | 100 concurrent users PATCH events on the same trip. Validates PostgreSQL row-level locks handle concurrent edits. |

### `tests/scale/locustfile_brainstorm.py`

| # | Test / TaskSet | Description |
|---|----------------|-------------|
| 1 | `BrainstormChatUser` | Simulates 50-200 users sending brainstorm chat messages concurrently. Measures LLM response latency and error rate under load. |
| 2 | `test_extract_under_load` | 100 users trigger /brainstorm/extract concurrently. Verifies dedup logic handles concurrent writes without duplicate items. |
| 3 | `test_bulk_insert_throughput` | Measures throughput of /brainstorm/bulk with varying batch sizes (10, 50, 100 items). |

### `tests/scale/locustfile_events.py`

| # | Test / TaskSet | Description |
|---|----------------|-------------|
| 1 | `EventTimelineUser` | Simulates a realistic user flow: list events → create event → update time → move to bin → list again. Measures full-cycle latency. |
| 2 | `test_event_list_with_votes_at_scale` | GET /events?trip_id=X for a trip with 200 events and 500 votes. Measures query latency of the batch vote tally. |
| 3 | `test_vote_burst` | 100 concurrent users cast votes on the same idea. Validates unique constraint doesn't deadlock. |

### `tests/scale/locustfile_ripple.py`

| # | Test / TaskSet | Description |
|---|----------------|-------------|
| 1 | `RippleStressUser` | Fires the Smart Ripple Engine on a trip with 100 events across 10 days. Measures CPU time and DB query count. |
| 2 | `test_ripple_cascading_200_events` | Shifts the first event on a 200-event trip. Profiles how many downstream events are touched and total wall-clock time. |
| 3 | `test_ripple_concurrent_fires` | 10 concurrent users fire ripple on the same trip. Validates no double-shifts or race conditions. |

### `tests/scale/locustfile_maps.py`

| # | Test / TaskSet | Description |
|---|----------------|-------------|
| 1 | `MapsEnrichmentUser` | Simulates bulk enrichment of 50-item batches under concurrent load. Measures Maps API latency, cache hit rate, and breaker behavior. |
| 2 | `test_directions_cache_hit_rate` | Repeatedly compute routes for the same waypoints. Measures cache hit ratio and verifies zero API calls on hits. |
| 3 | `test_enrichment_breaker_under_load` | Simulates Maps API returning 429s. Verifies the circuit breaker opens after threshold failures and recovery time. |

### `tests/scale/locustfile_concierge.py`

| # | Test / TaskSet | Description |
|---|----------------|-------------|
| 1 | `ConciergeChatUser` | Simulates 50 concurrent users chatting with the concierge. Measures LLM dispatch latency and intent classification accuracy. |
| 2 | `test_whats_next_at_scale` | 100 users hit GET /concierge/{trip_id}/whats-next simultaneously. Measures query latency for the time-based event lookup. |
| 3 | `test_find_nearby_throughput` | 50 concurrent find-nearby requests. Measures Maps nearby_search + directions latency. |

### `tests/scale/locustfile_notifications.py`

| # | Test / TaskSet | Description |
|---|----------------|-------------|
| 1 | `NotificationFeedUser` | Simulates 200 users polling GET /notifications every 5 seconds. Measures index scan performance on the notification table. |
| 2 | `test_notification_fanout_at_scale` | A trip with 50 members fires an event-added. Measures the time to insert 49 notification rows. |
| 3 | `test_mark_all_read_at_scale` | A user with 1000 unread notifications calls /mark-all-read. Measures UPDATE latency. |

### `tests/scale/locustfile_auth.py`

| # | Test / TaskSet | Description |
|---|----------------|-------------|
| 1 | `AuthFlowUser` | Simulates signup → login → refresh → logout cycles at 100 users/sec. Measures JWT issuance throughput. |
| 2 | `test_refresh_token_rotation_under_load` | 200 concurrent refresh token rotations. Validates no token-theft false positives under legitimate load. |

### `tests/scale/locustfile_rate_limit.py`

| # | Test / TaskSet | Description |
|---|----------------|-------------|
| 1 | `test_rate_limit_triggers_429` | Burst 1000 requests from a single IP within 10 seconds. Verifies that HTTP 429 is returned after the threshold. |
| 2 | `test_rate_limit_does_not_affect_normal_traffic` | Normal request patterns (1 req/sec) never see 429. |
| 3 | `test_rate_limit_recovery` | After a burst triggers 429, verify requests succeed again after the window resets. |

### `tests/scale/locustfile_connection_pool.py`

| # | Test / TaskSet | Description |
|---|----------------|-------------|
| 1 | `test_connection_pool_no_exhaustion` | 500 concurrent users making DB queries simultaneously. Verify no `ConnectionPoolExhausted` or `TimeoutError`. |
| 2 | `test_connection_pool_graceful_degradation` | Gradually ramp from 100 to 1000 users. Measure at what point p99 latency exceeds 5 seconds. |

---

*Total test count: ~430 tests across Integration (~380), Smoke (~17), and Scale (~30 Locust task sets). Pure-logic schema-validation and service tests live in `tests/unit/` and are not counted here.*
