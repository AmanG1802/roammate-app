# Integrate Apple App Store Server API (server-side IAP hardening)

## Context

The backend currently grants Plus entitlement from a StoreKit JWS blob sent by the iOS device, **without verifying its signature** — both at `/billing/apple/verify` (`backend/app/api/endpoints/billing.py:429-516`) and at the SSN V2 webhook `/billing/apple/webhook` (`billing.py:586-674`). A forged JWS would currently grant Plus. The webhook also lacks notification-type branching, so refunds and cancellations silently fall through as renewals.

Apple's **App Store Server API** + **App Store Server Library (Python)** solves all of this: full JWS/JWE signature verification against Apple's root CA chain, typed notification payloads, sandbox/production environment detection, and ground-truth subscription state lookups. The required settings (`APPLE_ISSUER_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY_PATH`) are already declared in `backend/app/core/config.py:105-108` but unused — this is a greenfield wiring.

Intended outcome: every Apple JWS the backend touches is cryptographically verified before granting entitlement; the webhook acts on the right state changes (refunds downgrade, renewals extend, expirations clear); the architecture is ready for v1.1 add-ons (reconciliation jobs, refund analytics) without rework.

## Scope decisions (already confirmed with user)

- **SDK**: Apple's official `app-store-server-library` Python package.
- **Signature verification**: applied to BOTH `/apple/verify` and `/apple/webhook` paths.
- **Notification branching**: full — REFUND/REVOKE downgrade immediately; DID_CHANGE_RENEWAL_STATUS marks canceled (Plus retained until `period_end`); EXPIRED + GRACE_PERIOD_EXPIRED downgrade.
- **Reconciliation job**: deferred to v1.1.

## Manual setup (one-time, by user)

1. **App Store Connect → Users and Access → Integrations → App Store Connect API → +**
   - Role: **App Manager**
   - Name: `Roammate Server`
   - Download the `.p8` file (one-time).
   - Note: **Issuer ID** (UUID, top of page), **Key ID** (10 chars).
2. Save the `.p8` at `backend/secrets/app_store_server.p8` (verify `backend/secrets/` is gitignored; add to `.gitignore` if not).
3. Populate `.env`:
   ```
   APPLE_ISSUER_ID=<uuid from App Store Connect>
   APPLE_KEY_ID=<10-char key id>
   APPLE_PRIVATE_KEY_PATH=backend/secrets/app_store_server.p8
   APPLE_USE_SANDBOX=true   # flip to false in prod
   ```

## Implementation

### 1. Dependency

`backend/requirements.txt`: add `app-store-server-library` (latest stable from PyPI — Apple-maintained SDK that wraps the Server API + provides `SignedDataVerifier` for JWS/JWE chain validation).

### 2. New service module: `backend/app/services/payments/app_store_server.py`

Single module that owns the SDK client lifecycle. Exposes:

- `get_verifier() -> SignedDataVerifier` — lazy singleton; loads bundled Apple root CAs (the SDK ships them) + reads `APPLE_BUNDLE_ID`, `APPLE_USE_SANDBOX`. Returns a verifier capable of decoding *and verifying* both transaction JWS and SSN V2 envelope payloads.
- `get_api_client() -> AppStoreServerAPIClient` — lazy singleton built from `APPLE_ISSUER_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY_PATH`, `APPLE_BUNDLE_ID`, env (sandbox/prod).
- `verify_transaction_jws(jws: str) -> JWSTransactionDecodedPayload` — wraps `verifier.verify_and_decode_signed_transaction`. Raises `VerificationException` on tampered/expired/wrong-bundle JWS.
- `verify_notification(signed_payload: str) -> ResponseBodyV2DecodedPayload` — wraps `verifier.verify_and_decode_notification`. Returns typed notification with `notificationType`, `subtype`, `data.signedTransactionInfo`, `data.signedRenewalInfo`.
- `lookup_subscription_statuses(original_transaction_id: str) -> StatusResponse` — optional helper for future use (refund flow may want to confirm latest status before downgrade).

Settings access uses `app.core.config.settings.APPLE_*` only — no module-level reads at import time (keeps tests cheap when Apple isn't configured).

### 3. Rewrite `backend/app/services/payments/apple_service.py`

- Keep the public `AppleTransaction` dataclass and the `is_valid_product` / `is_active` / `is_one_time` helpers — callers in `billing.py` depend on them.
- Replace `decode_signed_transaction` body: delegate to `app_store_server.verify_transaction_jws`, then map the SDK's `JWSTransactionDecodedPayload` into the existing `AppleTransaction` shape. Now the function performs full signature verification by default.
- Drop the base64/JSON manual decode path. Drop the docstring's "trust-the-device" caveat.
- Keep `sign_promotional_offer` untouched (different key, different scheme).

### 4. Update `/apple/verify` endpoint (`backend/app/api/endpoints/billing.py:429-516`)

Minimal change — `apple_service.decode_signed_transaction` now verifies. Add a focused `except VerificationException` clause that maps to HTTP 400 with `code: "invalid_signature"`. Existing flow (idempotency via `SubscriptionEvent`, user state flip, entitlement DTO return) is unchanged.

### 5. Rewrite `/apple/webhook` handler (`backend/app/api/endpoints/billing.py:586-674`)

Replace the manual JWS walk with:

```
payload = app_store_server.verify_notification(body["signedPayload"])
```

Then branch on `payload.notificationType` (use the SDK's `NotificationTypeV2` enum):

| Notification | Action |
|---|---|
| `SUBSCRIBED`, `DID_RENEW`, `OFFER_REDEEMED` | Extend: update `subscription_status='active'`, `subscription_current_period_end = expiresDate`. |
| `DID_CHANGE_RENEWAL_STATUS` (subtype `AUTO_RENEW_DISABLED`) | Mark `subscription_status='canceled'`; keep `subscription_tier='plus'` until period_end. |
| `DID_CHANGE_RENEWAL_STATUS` (subtype `AUTO_RENEW_ENABLED`) | Restore `subscription_status='active'`. |
| `EXPIRED`, `GRACE_PERIOD_EXPIRED` | Downgrade: `subscription_tier='free'`, `subscription_status='expired'`. |
| `REFUND`, `REVOKE` | Downgrade immediately: `subscription_tier='free'`, `subscription_status='canceled'`. Log refund context. |
| `DID_FAIL_TO_RENEW` | `subscription_status='past_due'`. |
| Everything else | Log + record `SubscriptionEvent` only. No state change. |

Idempotency: use `payload.notificationUUID` as the dedupe key for `SubscriptionEvent.event_id` (per Apple's recommendation). Existing helper already supports this.

### 6. Schema addition (small)

Add one nullable column to `User` in `backend/app/models/all_models.py`:

- `subscription_environment: Mapped[Optional[str]]` — `"Sandbox" | "Production"`, populated from the decoded transaction. Lets prod and sandbox transaction IDs coexist without collision and lets admin tooling separate the two.

One Alembic migration under `backend/alembic/versions/` adding this column nullable. Backfill not needed — only newly verified transactions populate it.

### 7. Tests

Follow the existing pattern in `backend/tests/api/test_api_billing.py:112-154` (mock `apple_service`):

- `test_apple_verify_signature_invalid` — mock `verify_transaction_jws` to raise `VerificationException`; assert 400 + `code: invalid_signature`.
- `test_apple_verify_signature_valid` — mock to return a fixture `JWSTransactionDecodedPayload`; assert user is flipped to Plus.
- `test_apple_webhook_refund_downgrades` — mock `verify_notification` to return a `REFUND` payload; assert user downgraded.
- `test_apple_webhook_did_change_renewal_canceled` — assert canceled status but Plus retained until period_end.
- `test_apple_webhook_expired_downgrades` — assert tier='free'.
- `test_apple_webhook_idempotent_on_uuid` — same `notificationUUID` twice → second call is a no-op.
- `test_apple_webhook_invalid_signature_400` — `verify_notification` raises → 400, no state change.

No real `.p8` keys in CI — every test mocks the SDK boundary.

### 8. iOS / config touches

None on the iOS side — `StoreKitClient.swift` already sends `jwsRepresentation` and the request shape is unchanged.

Update `.env.example` to add `APPLE_ISSUER_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY_PATH` with placeholder values + a comment pointing to App Store Connect → Users and Access → Integrations.

## Files to be modified

- `backend/requirements.txt` — add `app-store-server-library`
- `backend/app/services/payments/app_store_server.py` — new module
- `backend/app/services/payments/apple_service.py` — replace decoder, keep public shape
- `backend/app/api/endpoints/billing.py` — verify endpoint catches new exception; webhook handler rewritten with notification-type branching
- `backend/app/models/all_models.py` — add `subscription_environment` column to User
- `backend/alembic/versions/<new>_add_subscription_environment.py` — new migration
- `backend/tests/api/test_api_billing.py` — replace existing Apple tests + add 5 new ones
- `.env.example` — document new env vars
- `backend/secrets/.gitignore` — ensure `.p8` files are ignored

## Verification

1. **Local sandbox flow**:
   - Set `APPLE_USE_SANDBOX=true` and populated `.env`.
   - Run a real StoreKit 2 purchase in the iOS simulator (sandbox tester account).
   - Confirm `/billing/apple/verify` returns 200, user flipped to Plus, `subscription_environment='Sandbox'`.
2. **Forgery test**: hand-edit one byte of the JWS payload, replay → expect 400 `invalid_signature`.
3. **Webhook**: trigger SSN V2 from App Store Connect → Test Notifications (sandbox-issuable). Step through each `notificationType` (SUBSCRIBED, DID_RENEW, REFUND, DID_CHANGE_RENEWAL_STATUS, EXPIRED) — confirm DB state matches the table in step 5.
4. **Idempotency**: replay the same notification twice; assert no duplicate `SubscriptionEvent` rows and no state thrash.
5. **Test suite**: `cd backend && pytest tests/api/test_api_billing.py -v` — all green.
6. **Type check** / linter on changed Python files.

## Out of scope (explicit deferrals)

- Reconciliation polling job (deferred to v1.1).
- Family Sharing recognition.
- Refund analytics / admin dashboards.
- Migrating existing pre-verification transactions in production (none exist yet — pre-launch).
