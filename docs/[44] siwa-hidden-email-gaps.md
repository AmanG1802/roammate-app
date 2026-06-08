# Sign in with Apple — Hidden Email: Auth Linking & Invite Gaps

## Context

Roammate supports Sign in with Apple (SIWA) on iOS. Apple gives users the option to
**hide their real email** during sign-in, providing either a private relay address
(`abc123@privaterelay.appleid.com`) or no email claim at all. This is common — Apple
surfaces the option prominently and many privacy-conscious users choose it.

The current backend was written assuming email is a reliable cross-provider identifier.
Two separate systems break when that assumption fails:

1. **OAuth account linking** — a user who signed up via Apple and later tries Google ends up with two accounts instead of one.
2. **Trip/group invitations** — friends cannot find or invite the user because the invite flow does an email-only lookup and nobody knows the user's synthetic address.

---

## Root Cause: Email as the Sole Identity Key

### What Apple actually returns

`backend/app/services/auth/oauth_apple.py:97-104`

```python
email = claims.get("email")   # Optional — absent when "Hide My Email" is used
```

`AppleIdentity.email` is `Optional[str]`. Three possible values at runtime:

| Apple behaviour | `claims.email` value stored as `User.email` |
|---|---|
| User shares real email | `user@gmail.com` |
| User hides email | `abc123@privaterelay.appleid.com` |
| No email in token | `apple_<sub>@no-email.local` (synthetic, `linking.py:85`) |

### Gap 1 — OAuth auto-link fails silently

`backend/app/services/auth/linking.py:57-81` — the cross-provider merge path:

```python
if claims.email:
    user = select(User).where(User.email == claims.email)
```

When the user later signs in with Google (real email `user@gmail.com`), the lookup
finds nothing because the existing `User` row holds a relay or synthetic address.
`find_or_create_user_for_oauth` falls through to **step 3 and creates a fresh user**,
silently splitting the account in two. No error is raised; no warning is shown.

**Effect:** the user now has two accounts — their Apple trips and Google trips are
completely separate. Their app data (trips, groups, subscriptions, preferences) is
fragmented. There is no post-hoc merge path.

### Gap 2 — Trip and group invitations are broken

Trip invite: `backend/app/api/endpoints/trips.py:722`

```python
stmt = select(User).where(User.email == invite.email)
invitee = (await db.execute(stmt)).scalars().first()
if not invitee:
    raise HTTPException(status_code=404, ...)
```

Group invite: `backend/app/api/endpoints/groups.py:319`

```python
invitee = (await db.execute(select(User).where(User.email == body.email))).scalars().first()
```

Both endpoints accept an email address typed by the inviter and do a single
`User.email` lookup. For a SIWA hide-email user:

- The inviter types `friend@gmail.com`
- The stored `User.email` is `abc123@privaterelay.appleid.com` or `apple_<sub>@no-email.local`
- Lookup returns `None` → **404**; the invite fails as if the user doesn't exist

The hidden-email user is effectively uninvitable. Since Roammate is a collaborative
group trip app, this is a first-class product failure for a significant fraction of iOS
users.

---

## Affected Code Locations

| File | Lines | Issue |
|---|---|---|
| `backend/app/services/auth/linking.py` | 57–81 | Email-only cross-provider merge; no fallback |
| `backend/app/services/auth/linking.py` | 85 | Synthetic email stored as canonical email |
| `backend/app/api/endpoints/trips.py` | 721–724 | Invite lookup by email only |
| `backend/app/api/endpoints/groups.py` | 319–320 | Invite lookup by email only |
| `backend/app/models/all_models.py` | `User` model | No username / stable handle field |

---

## Fix Options

### Option A — Username as the invite key (recommended)

Add a `username` field to `User` (unique, user-chosen or auto-generated at signup).
Invite flow accepts username instead of (or in addition to) email. SIWA users get a
suggested username on first login (derived from their display name or a random handle).

**Pros:** completely sidesteps the email problem; friendlier UX than asking for emails anyway.
**Cons:** requires a migration + unique-handle conflict resolution UX.

### Option B — In-app friend search by name + avatar

Rather than inviting by typed identifier, expose a search endpoint
(`GET /users/search?q=`) that matches on `User.name` and returns profile cards.
The inviter picks from search results. No email involved.

**Pros:** most natural mobile UX; works for all auth methods.
**Cons:** name collisions are common; needs pagination + relevance ranking; raises
discoverability/privacy concerns (any user searchable by name).

### Option C — Share link / deep link invite

Generate a per-trip invite link (`/invite/<token>`) that the trip owner shares via
iMessage, WhatsApp, etc. The recipient taps the link, signs in (any method), and is
added to the trip — no email lookup needed.

**Pros:** works regardless of how the invitee signed up; common pattern (Notion, Figma).
**Cons:** link-based invites are open (anyone with the link can join unless the token is
single-use and tied to a specific invitee slot); managing pending slots adds complexity.

### Option D — Link Apple private relay to real email at login

On SIWA with a relay address, surface a one-time prompt: "Add your real email so
friends can find you." Store a secondary `contact_email` column if provided. The invite
lookup checks both `User.email` and `User.contact_email`.

**Pros:** minimal schema change; preserves existing invite UX.
**Cons:** optional step that users skip; doesn't solve the no-email case at all; two
email columns is confusing.

---

## Recommended Approach

**Option A + C together** covers the problem cleanly:

- Username solves the "find me" problem for users who want to be discoverable.
- Share links solve the "invite a stranger / non-member" problem independently of any identifier.
- Option B (name search) can be layered on top later without conflict.

This avoids leaning on email as an identifier at all, which is the right long-term
direction given that Apple, passkeys, and phone-based auth all make email optional.

---

## Schema Changes Required (Option A)

```sql
ALTER TABLE users ADD COLUMN username VARCHAR(40) UNIQUE;
CREATE UNIQUE INDEX idx_users_username ON users(username) WHERE username IS NOT NULL;
```

- Auto-generate at signup if not provided: slugify display name + random suffix.
- Expose `PATCH /api/users/me` to let users change their handle (with uniqueness check).
- Add `GET /api/users/search?username=` endpoint for the invite flow.
- Update trip and group invite request bodies to accept `username` as an alternative to `email`.

---

## Out of Scope (deferred)

- Merging two already-split accounts (requires a dedicated account-merge flow with
  ownership conflict resolution — separate plan).
- Backfilling usernames for existing users (can be done lazily on next login).
- Passkey / phone-number auth (separate auth plan).
