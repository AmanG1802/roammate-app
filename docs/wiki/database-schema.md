# Roammate Production Database Schema

PostgreSQL on Railway. 26 tables across three conceptual domains: **Identity & Auth**, **Trips & Itinerary**, and **AI, Billing & Observability**.

---

## Table of Contents

1. [Entity Relationship Summary](#entity-relationship-summary)
2. [Identity & Auth Tables](#identity--auth-tables)
   - [user](#user)
   - [user_identity](#user_identity)
   - [refresh_token](#refresh_token)
   - [email_verification](#email_verification)
   - [password_reset](#password_reset)
3. [Trips & Itinerary Tables](#trips--itinerary-tables)
   - [trip](#trip)
   - [trip_day](#trip_day)
   - [trip_member](#trip_member)
   - [timeline_item](#timeline_item)
   - [event_vote](#event_vote)
   - [day_route](#day_route)
4. [Social & Groups Tables](#social--groups-tables)
   - [group](#group)
   - [group_member](#group_member)
5. [Ideas & Brainstorm Tables](#ideas--brainstorm-tables)
   - [idea_bin_item](#idea_bin_item)
   - [idea_tag](#idea_tag)
   - [idea_vote](#idea_vote)
   - [brainstorm_bin_item](#brainstorm_bin_item)
   - [brainstorm_message](#brainstorm_message)
6. [Concierge Chat Tables](#concierge-chat-tables)
   - [concierge_message](#concierge_message)
7. [Billing & Subscriptions Tables](#billing--subscriptions-tables)
   - [coupon](#coupon)
   - [coupon_redemption](#coupon_redemption)
   - [subscription_event](#subscription_event)
   - [usage_counter](#usage_counter)
8. [Observability Tables](#observability-tables)
   - [notification](#notification)
   - [token_usage](#token_usage)
   - [google_maps_api_usage](#google_maps_api_usage)
9. [Deletion Order](#deletion-order)
10. [Shared Place Fields Pattern](#shared-place-fields-pattern)

---

## Entity Relationship Summary

```
user ──< user_identity          (OAuth providers per user)
user ──< refresh_token          (JWT rotation chain)
user ──< email_verification     (verify / change email)
user ──< password_reset         (password reset tokens)

user ──< trip_member >── trip   (many-to-many, with role)
user ──> trip.created_by_id     (trip creator)
group ──< trip                  (optional group ownership)
group ──< group_member >── user

trip ──< trip_day               (one row per calendar date)
trip ──< timeline_item          (itinerary events, placed on a day)
trip ──< day_route              (polyline per day)
trip ──< idea_bin_item          (shared idea pool for the trip)
trip ──< brainstorm_message     (per-user AI chat log)
trip ──< brainstorm_bin_item    (items extracted from brainstorm)
trip ──< concierge_message      (AI Concierge chat log)
trip ──< notification           (trip-scoped notifications)

timeline_item ──< event_vote    (thumbs up/down per user)
idea_bin_item ──< idea_vote     (thumbs up/down per user)
idea_bin_item ──< idea_tag      (free-form tags)
idea_bin_item ──> idea_bin_item.origin_idea_id  (promoted from brainstorm)

user ──< usage_counter          (monthly brainstorm message quota)
user ──< token_usage            (LLM token spend per op)
user ──< google_maps_api_usage  (Maps API cost per call)
user ──< subscription_event     (Razorpay / Apple IAP webhooks)
user ──< coupon_redemption      (which coupon was used)
coupon ──< coupon_redemption
```

---

## Identity & Auth Tables

### `user`

Core account record. All subscription state lives here (denormalised for fast reads).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | auto-increment | PK |
| `email` | varchar | NO | — | Unique |
| `name` | varchar | YES | — | Display name |
| `hashed_password` | varchar | YES | — | NULL for pure-OAuth accounts |
| `personas` | json | YES | — | Array of travel-style tags (e.g. `["adventure","budget"]`) |
| `avatar_url` | varchar | YES | — | |
| `home_city` | varchar | YES | — | |
| `timezone` | varchar | YES | — | IANA timezone string |
| `currency` | varchar(8) | YES | — | ISO 4217 (e.g. `INR`) |
| `travel_blurb` | varchar | YES | — | Short bio |
| `created_at` | timestamptz | YES | `now()` | |
| `email_verified` | boolean | NO | `false` | |
| `email_verified_at` | timestamptz | YES | — | |
| `auth_version` | integer | NO | `1` | Incremented to invalidate all refresh tokens |
| `subscription_tier` | varchar(16) | NO | `'free'` | `free` \| `pro` \| `lifetime` |
| `subscription_status` | varchar(24) | NO | `'none'` | `none` \| `active` \| `expired` \| `cancelled` |
| `subscription_provider` | varchar(16) | YES | — | `razorpay` \| `apple` |
| `subscription_current_period_end` | timestamptz | YES | — | |
| `subscription_external_id` | varchar | YES | — | Provider subscription/order ID |
| `last_one_time_purchase_at` | timestamptz | YES | — | For lifetime purchases |
| `last_one_time_external_id` | varchar | YES | — | |
| `subscription_environment` | varchar(16) | YES | — | `sandbox` \| `production` (Apple only) |
| `tutorial_status_web` | varchar(20) | NO | `'not_started'` | `not_started` \| `in_progress` \| `completed` |
| `tutorial_status_ios` | varchar(20) | NO | `'not_started'` | |
| `tutorial_step_web` | integer | NO | `0` | Step index within tutorial |
| `tutorial_step_ios` | integer | NO | `0` | |

---

### `user_identity`

One row per OAuth provider linked to an account. A user can have multiple rows (e.g. both Google and Apple).

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | bigint | NO | PK |
| `user_id` | integer | NO | FK → `user.id` |
| `provider` | varchar(16) | NO | `google` \| `apple` |
| `subject` | varchar(255) | NO | Provider's stable user ID (Google `sub`, Apple `sub`) |
| `email_at_link` | varchar(320) | YES | Email at time of OAuth link |
| `apple_refresh_token` | varchar(2048) | YES | Apple refresh token for SIWA revocation on delete |
| `created_at` | timestamptz | NO | `now()` |

---

### `refresh_token`

JWT refresh token rotation chain. On every token refresh a new row is created; the old row is linked via `parent_id` so reuse of a stolen token can be detected.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | bigint | NO | PK |
| `user_id` | integer | NO | FK → `user.id` |
| `token_hash` | varchar(64) | NO | SHA-256 of the raw token |
| `device_label` | varchar(128) | YES | User-agent / device hint |
| `parent_id` | bigint | YES | FK → `refresh_token.id` (previous token in chain) |
| `expires_at` | timestamptz | NO | |
| `revoked_at` | timestamptz | YES | Set when revoked (logout, password change, auth_version bump) |
| `last_used_at` | timestamptz | YES | |
| `created_at` | timestamptz | NO | `now()` |

---

### `email_verification`

Tokens for email verification and email-change flows.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `token_hash` | varchar(64) | NO | PK (SHA-256 of raw token) |
| `user_id` | integer | NO | FK → `user.id` |
| `email` | varchar(320) | NO | The email being verified (may be new email for change flow) |
| `purpose` | varchar(24) | NO | `verify` \| `change` |
| `expires_at` | timestamptz | NO | |
| `consumed_at` | timestamptz | YES | Set when token is used |
| `created_at` | timestamptz | NO | `now()` |

---

### `password_reset`

Single-use password reset tokens.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `token_hash` | varchar(64) | NO | PK |
| `user_id` | integer | NO | FK → `user.id` |
| `expires_at` | timestamptz | NO | |
| `consumed_at` | timestamptz | YES | |
| `created_at` | timestamptz | NO | `now()` |

---

## Trips & Itinerary Tables

### `trip`

Top-level trip record.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | auto-increment | PK |
| `name` | varchar | NO | — | Trip name |
| `start_date` | timestamptz | YES | — | |
| `end_date` | timestamptz | YES | — | |
| `timezone` | varchar | YES | `'UTC'` | IANA timezone |
| `created_by_id` | integer | YES | — | FK → `user.id` |
| `group_id` | integer | YES | — | FK → `group.id` (NULL = solo trip) |
| `destination_city` | varchar | YES | — | |
| `country_code` | varchar(2) | YES | — | ISO 3166-1 alpha-2 |
| `destination_lat` | double | YES | — | |
| `destination_lng` | double | YES | — | |
| `is_tutorial` | boolean | NO | `false` | Onboarding demo trip |
| `is_tutorial_completed` | boolean | NO | `false` | |
| `created_at` | timestamptz | YES | `now()` | |

---

### `trip_day`

One row per calendar date within a trip. Used to anchor `timeline_item` rows and `day_route` rows to a day number.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `trip_id` | integer | NO | FK → `trip.id` |
| `date` | date | NO | Calendar date |
| `day_number` | integer | NO | 1-indexed day within trip |

---

### `trip_member`

Join table for users ↔ trips. A user is added here when they create a trip or accept an invitation.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `trip_id` | integer | YES | FK → `trip.id` |
| `user_id` | integer | YES | FK → `user.id` |
| `role` | varchar | YES | `owner` \| `member` |
| `status` | varchar | YES | `active` \| `invited` \| `declined` |

---

### `timeline_item`

An itinerary event placed on a specific day. Contains rich place data (Google Maps enriched). This is the core "thing to do" record.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `trip_id` | integer | YES | FK → `trip.id` |
| `day_date` | date | YES | Which day this event belongs to |
| `sort_order` | integer | YES | Visual position within the day |
| `title` | varchar | NO | Event name |
| `description` | text | YES | |
| `event_type` | varchar | YES | `activity` \| `food` \| `transport` \| `accommodation` etc. |
| `category` | varchar | YES | Sub-category |
| `time_category` | varchar | YES | `morning` \| `afternoon` \| `evening` \| `night` |
| `start_time` | time | YES | Local time |
| `end_time` | time | YES | |
| `is_locked` | boolean | YES | Locked events are not shifted by Smart Ripple Engine |
| `is_skipped` | boolean | NO | `false` | Soft-delete within a day |
| `added_by` | varchar | YES | Display name of the user who added it |
| `place_id` | varchar | YES | Google Maps place ID |
| `lat` | double | YES | |
| `lng` | double | YES | |
| `address` | varchar | YES | |
| `photo_url` | varchar | YES | |
| `rating` | double | YES | Google rating (0–5) |
| `price_level` | integer | YES | Google price level (0–4) |
| `types` | json | YES | Array of Google place type strings |

---

### `event_vote`

Up/down vote on a `timeline_item`. One row per user per event.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `event_id` | integer | NO | FK → `timeline_item.id` |
| `user_id` | integer | NO | FK → `user.id` |
| `value` | integer | NO | `1` = up, `-1` = down |
| `created_at` | timestamptz | NO | `now()` |

---

### `day_route`

Cached Google Directions result for a single day's ordered events. Re-computed when events change.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `trip_id` | integer | NO | FK → `trip.id` |
| `day_date` | varchar | NO | Date string matching `timeline_item.day_date` |
| `encoded_polyline` | text | YES | Google encoded polyline for the full route |
| `legs` | json | NO | Array of leg objects (duration, distance, steps) |
| `total_duration_s` | integer | YES | Total drive time in seconds |
| `total_distance_m` | integer | YES | Total distance in metres |
| `ordered_event_ids` | json | NO | Event IDs in route order |
| `unroutable` | json | NO | Event IDs that couldn't be routed |
| `waypoint_fingerprint` | varchar | NO | Hash of ordered event IDs; used to detect stale routes |
| `computed_at` | timestamptz | NO | `now()` |

---

## Social & Groups Tables

### `group`

A persistent friend circle that can be attached to multiple trips.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `name` | varchar | NO | |
| `owner_id` | integer | NO | FK → `user.id` |
| `created_at` | timestamptz | YES | `now()` |

---

### `group_member`

Users in a group.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `group_id` | integer | NO | FK → `group.id` |
| `user_id` | integer | NO | FK → `user.id` |
| `role` | varchar | YES | `owner` \| `member` |
| `status` | varchar | YES | `active` \| `invited` |

---

## Ideas & Brainstorm Tables

### `idea_bin_item`

The shared **Idea Bin** — a collaborative pool of destination/activity ideas visible to all trip members. Can be promoted from a private `brainstorm_bin_item` via `origin_idea_id`.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `trip_id` | integer | YES | FK → `trip.id` |
| `origin_idea_id` | integer | YES | FK → `idea_bin_item.id` (self-ref: promoted from another idea) |
| `title` | varchar | NO | |
| `description` | text | YES | |
| `category` | varchar | YES | |
| `time_category` | varchar | YES | `morning` / `afternoon` / `evening` / `night` |
| `start_time` | time | YES | |
| `end_time` | time | YES | |
| `added_by` | varchar | YES | Display name |
| `place_id` | varchar | YES | Google Maps place ID |
| `lat` / `lng` | double | YES | |
| `address` | varchar | YES | |
| `photo_url` | varchar | YES | |
| `rating` | double | YES | |
| `price_level` | integer | YES | |
| `types` | json | YES | Google place types array |

---

### `idea_tag`

Free-form tags on an `idea_bin_item`.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `idea_id` | integer | NO | FK → `idea_bin_item.id` |
| `tag` | varchar | NO | |
| `created_at` | timestamptz | NO | `now()` |

---

### `idea_vote`

Up/down vote on a shared idea. One row per user per idea.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `idea_id` | integer | NO | FK → `idea_bin_item.id` |
| `user_id` | integer | NO | FK → `user.id` |
| `value` | integer | NO | `1` = up, `-1` = down |
| `created_at` | timestamptz | NO | `now()` |

---

### `brainstorm_bin_item`

**Private** AI-extracted ideas for a single user within a trip (before they're promoted to the shared Idea Bin). Shares the same place-fields pattern as `idea_bin_item`.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `trip_id` | integer | YES | FK → `trip.id` |
| `user_id` | integer | NO | FK → `user.id` |
| `created_at` | timestamptz | YES | `now()` |
| `title` | varchar | NO | |
| `description` | text | YES | |
| `category` | varchar | YES | |
| `time_category` | varchar | YES | |
| `added_by` | varchar | YES | |
| `place_id` | varchar | YES | |
| `lat` / `lng` | double | YES | |
| `address` | varchar | YES | |
| `photo_url` | varchar | YES | |
| `rating` | double | YES | |
| `price_level` | integer | YES | |
| `types` | json | YES | |

---

### `brainstorm_message`

Chat log for the per-user, per-trip AI brainstorm chat. Stored as a flat list of `user` / `assistant` turns.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `trip_id` | integer | YES | FK → `trip.id` |
| `user_id` | integer | NO | FK → `user.id` |
| `role` | varchar | NO | `user` \| `assistant` |
| `content` | text | NO | Raw message text |
| `created_at` | timestamptz | YES | `now()` |
| `extracted_at` | timestamptz | YES | Set when this message was processed to extract `brainstorm_bin_item` rows |

---

## Concierge Chat Tables

### `concierge_message`

Chat log for the **AI Concierge** — the holistic on-trip assistant chat. Same turn-based structure as `brainstorm_message` but with richer metadata.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `trip_id` | integer | YES | FK → `trip.id` |
| `user_id` | integer | NO | FK → `user.id` |
| `role` | varchar | NO | `user` \| `assistant` |
| `content` | text | NO | |
| `message_type` | varchar | YES | `text` \| `action` \| `suggestion` etc. |
| `metadata` | json | YES | Arbitrary structured data attached to a message (e.g. suggested events) |
| `created_at` | timestamptz | YES | `now()` |

---

## Billing & Subscriptions Tables

### `coupon`

Promotional discount codes, supporting both Razorpay and Apple IAP offer IDs.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | auto-increment | PK |
| `code` | varchar(64) | NO | — | Human-readable code (e.g. `LAUNCH50`) |
| `description` | varchar | YES | — | Admin label |
| `discount_type` | varchar(16) | NO | — | `percent` \| `flat` |
| `discount_value` | integer | NO | — | Percentage (0–100) or flat paise |
| `applies_to` | varchar(32) | NO | — | `pro_monthly` \| `pro_annual` \| `lifetime` |
| `valid_from` | timestamptz | NO | `now()` | |
| `valid_until` | timestamptz | NO | — | |
| `max_redemptions_per_user` | integer | NO | `1` | |
| `razorpay_offer_id` | varchar | YES | — | Razorpay offer ID to attach at checkout |
| `apple_offer_id` | varchar | YES | — | Apple promotional offer ID |
| `is_active` | boolean | NO | `true` | |
| `created_at` | timestamptz | NO | `now()` | |
| `updated_at` | timestamptz | NO | `now()` | |

---

### `coupon_redemption`

Records each time a user successfully uses a coupon.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `coupon_id` | integer | NO | FK → `coupon.id` |
| `user_id` | integer | NO | FK → `user.id` |
| `provider` | varchar(24) | NO | `razorpay` \| `apple` |
| `payment_external_id` | varchar | YES | Razorpay order/payment ID or Apple transaction ID |
| `amount_paid_paise` | integer | NO | `0` | Actual amount charged after discount |
| `applied_at_period_start` | timestamptz | NO | `now()` | Subscription period start when applied |
| `created_at` | timestamptz | NO | `now()` | |

---

### `subscription_event`

Raw webhook payloads from Razorpay and Apple IAP for audit and replay.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `user_id` | integer | YES | FK → `user.id` (may be NULL if user not yet resolved) |
| `provider` | varchar(16) | NO | `razorpay` \| `apple` |
| `event_id` | varchar | NO | Provider's event/notification ID (idempotency key) |
| `event_type` | varchar(64) | NO | e.g. `subscription.activated`, `SUBSCRIBED` |
| `raw_payload` | json | NO | `{}` | Full webhook body |
| `created_at` | timestamptz | NO | `now()` |

---

### `usage_counter`

Monthly brainstorm message quota per user. One row per user per `YYYY-MM` period.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `user_id` | integer | NO | FK → `user.id` |
| `period` | varchar(7) | NO | Format: `YYYY-MM` |
| `brainstorm_messages` | integer | NO | `0` | Count of AI messages sent this period |
| `updated_at` | timestamptz | NO | `now()` |

---

## Observability Tables

### `notification`

In-app notifications delivered to users. Trip-scoped or group-scoped.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `user_id` | integer | NO | FK → `user.id` (recipient) |
| `actor_id` | integer | YES | FK → `user.id` (who triggered it) |
| `trip_id` | integer | YES | FK → `trip.id` |
| `group_id` | integer | YES | (no FK constraint — stored as plain integer) |
| `type` | varchar | NO | e.g. `trip_invite`, `event_added`, `idea_voted` |
| `payload` | json | NO | Notification-type-specific data |
| `read_at` | timestamptz | YES | NULL = unread |
| `created_at` | timestamptz | NO | `now()` |

---

### `token_usage`

LLM token spend ledger. One row per API call.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `user_id` | integer | YES | FK → `user.id` |
| `trip_id` | integer | YES | FK → `trip.id` |
| `op` | varchar | NO | Operation name (e.g. `brainstorm`, `concierge`, `intent`) |
| `provider` | varchar | NO | `openai` \| `anthropic` \| `google` |
| `model` | varchar | NO | Model ID string |
| `tokens_in` | integer | NO | Prompt tokens |
| `tokens_out` | integer | NO | Completion tokens |
| `tokens_total` | integer | NO | Sum |
| `source` | varchar | YES | Sub-operation tag |
| `cost_usd` | numeric | YES | Computed cost in USD |
| `created_at` | timestamptz | YES | `now()` |

---

### `google_maps_api_usage`

Google Maps API call ledger for cost tracking and circuit-breaker monitoring.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | integer | NO | PK |
| `user_id` | integer | YES | FK → `user.id` |
| `trip_id` | integer | YES | FK → `trip.id` |
| `op` | varchar | NO | Operation: `find_place`, `place_details`, `directions`, `geocode`, etc. |
| `status` | varchar | NO | `ok` \| `error` \| `cache_hit` |
| `latency_ms` | integer | YES | |
| `attempts` | integer | YES | Retry count |
| `cache_state` | varchar | YES | `hit` \| `miss` \| `stale` |
| `breaker_state` | varchar | YES | `closed` \| `half_open` \| `open` |
| `http_status` | integer | YES | HTTP response code from Maps API |
| `error_class` | varchar | YES | Exception class name on failure |
| `batch_size` | integer | YES | Number of places in batch request |
| `enriched_count` | integer | YES | How many places were successfully enriched |
| `cost_usd` | numeric | YES | Estimated API cost |
| `created_at` | timestamptz | YES | `now()` |

---

## Deletion Order

When wiping all user data (e.g. for a full reset), truncate in this order to respect FK constraints:

```sql
TRUNCATE TABLE
  event_vote, idea_vote, idea_tag,
  brainstorm_bin_item, brainstorm_message,
  concierge_message, day_route,
  google_maps_api_usage, notification,
  timeline_item, token_usage,
  trip_day, trip_member, idea_bin_item,
  trip, group_member, "group",
  coupon_redemption, email_verification,
  password_reset, refresh_token,
  subscription_event, usage_counter,
  user_identity, "user"
CASCADE;
```

To delete a single user and all their data, the FK cascade is sufficient if defined — otherwise delete child rows first following the dependency graph above.

---

## Shared Place Fields Pattern

`timeline_item`, `idea_bin_item`, and `brainstorm_bin_item` all share the same set of Google Maps-enriched place columns:

| Field | Source |
|-------|--------|
| `place_id` | Google Maps place ID |
| `lat`, `lng` | Geocoordinates |
| `address` | Formatted address |
| `photo_url` | First photo reference resolved to URL |
| `rating` | Google rating 0–5 |
| `price_level` | 0 (free) – 4 (very expensive) |
| `types` | JSON array of Google place type strings |
| `time_category` | Inferred: `morning` / `afternoon` / `evening` / `night` |
| `category` | Roammate category: `food` / `activity` / `accommodation` / `transport` |
| `added_by` | Display name string (denormalised, not a FK) |

These fields are populated by the **Maps Enrichment Pipeline** (`find_place` → `place_details` → hydrate) after the LLM returns a structured suggestion.
