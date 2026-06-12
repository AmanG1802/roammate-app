# [45] Account Delete & Profile Section Hardening

## Context
Audit of the Account Delete and Profile Section workflows surfaced confirmed bugs and missing safeguards across backend, web, and iOS. Two user-visible bugs exist in the web frontend (stuck delete button, silent inline-field save failures), one security-relevant inconsistency exists in iOS (password min-length 6 vs backend's 8), and the backend is missing email notifications and input validation. All three surfaces need targeted fixes.

---

## Todo

### Backend

- [ ] **`update_me`** — add field validation:
  - `travel_blurb` max length 280 (match frontend cap) → HTTP 422
  - `timezone` validate against `zoneinfo.available_timezones()` → HTTP 422
  - `currency` validate against `{"INR","USD","EUR","GBP","AUD","JPY","CAD","SGD"}` → HTTP 422
- [ ] **`update_me`** — call `send_password_changed_notice(email, name)` after `revoke_all_for_user()` on password change
- [ ] **`delete_me`** — cancel active Razorpay subscription before DB cleanup: if `subscription_provider == "razorpay"` and `subscription_external_id` and `subscription_status in ("active", "authenticated")`, call `razorpay_service.cancel_subscription(subscription_external_id)` in a `try/except` (log failure, never abort deletion)
- [ ] **`delete_me`** — call `send_account_deleted_notice(email, name)` after `db.commit()` (capture email + name before `db.delete()`)
- [ ] **`auth/email.py`** — add `send_password_changed_notice(to, name)` function
- [ ] **`auth/email.py`** — add `send_account_deleted_notice(to, name)` function
- [ ] **New template** `backend/app/services/auth/templates/password_changed.html`
- [ ] **New template** `backend/app/services/auth/templates/account_deleted.html`
- [ ] **Tests** — add `test_intg_users.py` cases for field validation (travel_blurb > 280, invalid timezone, invalid currency)
- [ ] **Tests** — patch `_send` to assert it is called on password change and account deletion

### Web Frontend

- [ ] **`EditProfile.tsx` — `DeleteAccountModal`**: Fix stuck "Deleting…" state — wrap `await onConfirm()` in `try/finally` so `setDeleting(false)` always runs even if deletion API call throws
- [ ] **`EditProfile.tsx` — `InlineField`**: Add `fieldError` state; on `onSave` returning false, set error and keep editing open instead of silently closing
- [ ] **`frontend/app/profile/persona/page.tsx`**: Add rose error banner when `updatePersonas` returns false (mirrors existing success banner pattern)

### iOS

- [ ] **`EditProfileView.swift`** — fix password min-length: `newPassword.count >= 6` → `>= 8`
- [ ] **`EditProfileView.swift`** — fix password placeholder: `"New password (min 6 chars)"` → `"New password (min 8 chars)"`
- [ ] **`EditProfileView.swift`** — fix default timezone: both `@State` default and `hydrate()` use `"Asia/Calcutta"` → change to `"Asia/Kolkata"`
- [ ] **`EditProfileView.swift`** — add unsaved-changes guard:
  - Track `@State private var isDirty = false`, set in `.onChange` of all editable fields
  - Reset in `hydrate()` and on successful `save()`
  - Hide default back button when dirty (`.navigationBarBackButtonHidden(isDirty)`) + custom leading toolbar button
  - Show `.confirmationDialog("Discard changes?")` with "Discard" (destructive) and "Keep Editing" (cancel)

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/api/endpoints/users.py` | Validation + Razorpay cancel + email calls |
| `backend/app/services/auth/email.py` | 2 new send functions |
| `backend/app/services/auth/templates/password_changed.html` | New template |
| `backend/app/services/auth/templates/account_deleted.html` | New template |
| `backend/tests/integration/test_intg_users.py` | New validation test cases |
| `frontend/components/EditProfile.tsx` | Fix stuck modal + InlineField error state |
| `frontend/app/profile/persona/page.tsx` | Error banner on failed save |
| `ios/Roammate/Views/Profile/EditProfileView.swift` | Password length, timezone default, unsaved-changes guard |

---

## Verification

1. `pytest backend/tests/integration/test_intg_users.py -v` — all new validation cases pass
2. Web: trigger account delete with API returning 500 → button resets to "Delete my account" (no infinite spin)
3. Web: force a network error on an inline field save → field stays open with error text instead of silently closing
4. Web: save personas with API returning error → rose error banner appears
5. iOS: type a 7-char new password → Save button stays disabled
6. iOS: edit fields without saving, tap Back → discard confirmation dialog appears
7. Confirm Resend email is triggered (check logs) on both password change and account deletion
