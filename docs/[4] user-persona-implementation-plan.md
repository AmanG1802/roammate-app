# User Persona Feature — Implementation Plan

## Context

Roammate currently has no notion of a "user persona." The LLM service (`RoammateServiceV1`) treats every user identically — `_pack_trip_context()` only injects trip events and the user's role on the trip. As a result, brainstorm suggestions, plan-trip outputs, and concierge replies cannot adapt to whether the user is a foodie, a thrill-seeker, or a museum hopper.

We are adding:

1. A **Profile** area, opened via a 3-dot menu next to the user pill in the dashboard sidebar (which today only has a logout icon at `frontend/app/dashboard/page.tsx:245-261`).
2. A **User Persona** tab inside Profile — a Pinterest-style picker over **14 lifestyle persona traits** (decoupled from the existing 10 activity Categories used for extraction).
3. A **forced onboarding** step on first signup that reuses the same persona picker.
4. **LLM personalisation** by injecting the user's selected personas into `_pack_trip_context()` so every prompt (brainstorm/plan/concierge) sees them.

> **Note on "14 vs 10":** Persona traits are a **separate taxonomy** from `backend/app/schemas/llm.py:Category` (which constrains LLM activity extraction). Personas describe *who the user is*; Categories describe *what kind of activity*. No changes to the Category enum.

---

## Product Manager Perspective

**Goal:** raise perceived AI quality without changing model/provider — same tokens, better personalisation.

**Success metrics (post-launch, 30-day window):**

- ≥60% of new signups complete onboarding persona selection (forced, so target should be >90%; gap = drop-offs).
- ≥25% of existing users edit personas from the Profile page within 30 days of release.
- Qualitative: regression-test 10 stock prompts (foodie vs adventure vs religious user) — outputs should diverge meaningfully.

**Scope (in):**

- Profile shell with left nav: **Edit Profile (default tab)**, Subscription (Coming Soon), User Persona.
- **Comprehensive, interactive Edit Profile tab** — editable name, email (with verification stub), avatar upload + crop, password change, timezone, home city, travel-style blurb, account-deletion danger zone. Inline validation, optimistic save with toasts, "unsaved changes" guard on tab switch.
- Persona picker (14 rectangular chips, multi-select, modify/save).
- **Single persona catalog config** at `backend/app/config/persona_catalog.py` — single source of truth for slugs, labels, icons, LLM descriptions; exposed via a small `/users/personas/catalog` endpoint so the frontend renders from server data instead of hard-coding (cheap iteration loop, no FE redeploy when we tweak the list).
- Forced onboarding on first login as a **mid-size modal over the login page** (see Designer section).
- **"Skip for now" link** in onboarding → PUTs `personas = []` and shows a soft, dismissible banner on the dashboard sidebar prompting the user to set their persona later.
- Backend: `User.personas: JSON` column + `GET/PUT /users/me/personas` + extended `PUT /users/me` for the new profile fields.
- LLM: persona injection in `_pack_trip_context()`.

**Scope (out, deferred):**

- Subscription tab content (placeholder only).
- Persona-weighted ranking inside brainstorm extraction (we chose system-prompt-only injection — keep ranking neutral for now).
- Multi-language persona labels.
- Real email-change verification flow (stub only; mark TODO).

**Non-goals:** persona analytics dashboards, A/B testing infrastructure, persona-derived recommendations outside of LLM output.

**Risks:**

- *Forced onboarding hurts activation* → mitigated by the "Skip for now" link (now in scope) that writes `personas = []` and triggers a dismissible soft-prompt banner on the dashboard, so the user can opt in later without friction.
- *14 traits feel arbitrary* → mitigated by `persona_catalog.py` (now in scope) as the single source of truth, served to the frontend at runtime — we can add/remove/rename traits in one place and ship without a frontend redeploy.
- *LLM context bloat* → persona names are short; even all 14 selected adds ≤120 tokens to the system prompt.
- *Edit Profile scope creep* → strictly cap fields to the list above; defer email-change verification + 2FA.

**Rollout:**

- Ship behind no flag (small surface, additive).
- Backfill: existing users have `personas = NULL` → treated as "no preference," LLM behaviour unchanged for them until they visit Profile.

---

## Designer Perspective

**Information architecture:**

```
Dashboard sidebar (bottom-left user pill)
   └─ ⋮ menu  →  Profile  /  Logout
                   │
                   └─ /profile
                        ├─ Edit Profile          (left nav, DEFAULT tab)
                        ├─ User Persona          (left nav)
                        └─ Subscription (Soon)   (left nav, badge)

Login page  ──first signup──▶  Onboarding modal (mid-size popup, blurred login behind)
                                 ├─ Persona picker
                                 └─ Skip for now → soft-prompt banner on dashboard
```

**Key screens:**

1. **3-dot menu (popover):** anchored to the user pill, opens upward. Two items: Profile (User icon), Logout (LogOut icon — moves out of the existing inline button into this menu).
2. **Profile page (`/profile`):** two-column layout. Left rail (~240px) with vertical tab list, active state = indigo left-border + bg tint to match existing dashboard sidebar. Right pane = active tab content. Persistent header with avatar + name on top. **Default landing tab is Edit Profile.**
3. **Edit Profile tab (default, comprehensive & interactive):**
  - **Header card:** large circular avatar (96px) on the left, name + email + "Member since" on the right. Hovering the avatar reveals a camera-icon overlay → click opens an upload + crop modal (square crop, drag-to-position, zoom slider).
  - **Identity section:** inline-editable name field (click pencil icon to edit, Enter to commit, Esc to cancel — no separate "edit mode"). Email field with a "Change" button that opens a small inline panel (new email + current password + verification stub) — copy reads "Verification coming soon, change applies on confirm."
  - **Preferences section:** Timezone (searchable dropdown), Home city (city autocomplete reusing brainstorm city search if available), Preferred currency (USD/EUR/INR/GBP/…), Travel-style blurb (free-text textarea, ~280 chars, also fed to the LLM context as a one-liner).
  - **Security section:** Change password (current + new + confirm; show strength meter), active sessions list (read-only stub for now).
  - **Danger zone:** "Delete account" button (red ghost) → confirmation modal that requires typing the user's email to proceed.
  - **UX details:** every field saves on blur with optimistic update + checkmark animation; failed saves revert + red toast. A persistent "Unsaved changes" pill appears top-right if any field is mid-edit; switching tabs warns via a confirm modal. Skeleton loaders while initial fetch resolves. All labels have helper text on focus.
  - Layout: cards stacked vertically with a max-width of 720px; subtle dividers between sections; rounded-2xl card surfaces matching the dashboard aesthetic.
4. **User Persona tab:**
  - Hero: "Tell us what makes you tick" + 1-line subhead.
  - **Cluster of 14 rectangular chips**, centred, multi-line, auto-flowing (like Pinterest's interest grid). Chips of varying widths driven by label length; rows wrap naturally — no rigid grid.
  - Each chip: rounded-lg, py-2.5 px-4, emoji or lucide icon + label, default border `border-slate-200`, **selected state = `border-indigo-600 border-2 + bg-indigo-50 + scale-105` with check badge top-right**. Hover = lift + border darken.
  - Subtle entrance animation: chips stagger-fade-in (50ms each) on mount.
  - Sticky footer bar with **Save** (primary, indigo) and **Reset** (ghost). Save is disabled until selection differs from server state. Toast confirmation on save.
  - Empty-state copy if 0 selected: "Pick at least one — your concierge gets smarter the more it knows."
5. **Onboarding modal (over the login page):**
  - **Not** a full-screen route. After successful first signup, the user stays on the login page; the page background is **blurred (`backdrop-blur-md`) and dimmed (`bg-slate-900/40`)**, and a centred mid-size modal (~640px wide, ~auto height, `rounded-3xl`, `shadow-2xl`) animates in (fade + slight scale-up).
  - Modal contents: short hero ("Welcome to Roammate — what makes you tick?"), the same `<PersonaPicker layout="onboarding" />`, and a footer with **Skip for now** (ghost link, left) and **Continue** (primary indigo, right; disabled when 0 selected unless skipping).
  - Modal is **non-dismissible by clicking the backdrop or pressing Esc** — the user must either Continue or Skip, so we always end up with a deterministic `personas` value (`null` → set to `[]` or a list).
  - On Continue/Skip → modal exit animation, then `router.push('/dashboard')`.
  - If the user *skipped*, the dashboard sidebar shows a small dismissible banner: "Set your travel persona for smarter suggestions →" (links to `/profile/persona`). Dismissal stored in `localStorage` (`persona_soft_prompt_dismissed`) — does not re-appear in the same browser unless cleared.

**The 14 personas (proposed):**


| #   | Label                | Icon (lucide / emoji) |
| --- | -------------------- | --------------------- |
| 1   | Foodie               | 🍜 / Utensils         |
| 2   | Culture Buff         | 🎭 / Theater          |
| 3   | Nature Lover         | 🌿 / Leaf             |
| 4   | Adventure Seeker     | 🧗 / Mountain         |
| 5   | Beach Bum            | 🏖️ / Waves           |
| 6   | History Nerd         | 📜 / Scroll           |
| 7   | Nightlife Enthusiast | 🍸 / Wine             |
| 8   | Shopaholic           | 🛍️ / ShoppingBag     |
| 9   | Wellness Seeker      | 🧘 / Sparkles         |
| 10  | Photographer         | 📸 / Camera           |
| 11  | Family Traveller     | 👨‍👩‍👧 / Users      |
| 12  | Solo Explorer        | 🎒 / Backpack         |
| 13  | Luxury Traveller     | 💎 / Gem              |
| 14  | Budget Hacker        | 💸 / Wallet           |


**Microcopy & delight:**

- On 5+ selections, animate a small "🔥 You're getting specific" micro-toast.
- Save button label morphs: `Save` → `Saving…` → `Saved ✓` (then back to `Save` after 2s).

**Accessibility:**

- Chips render as `<button role="checkbox" aria-checked>` with focus ring; full keyboard support.
- Colour contrast: indigo-600 on indigo-50 ≥ AA.
- Reduced-motion media query disables stagger and scale.

**Style alignment:** matches existing dashboard — Tailwind, `font-black` headings, indigo-600 primary, slate neutrals, lucide icons (already in deps).

---

## Software Engineer Perspective

### Backend

**1. User model** — `backend/app/models/all_models.py:7-12`

```python
class User(Base):
    # ...existing columns...
    personas      = Column(JSON, nullable=True, default=None)   # list[str] | None
    avatar_url    = Column(String, nullable=True)
    home_city     = Column(String, nullable=True)
    timezone      = Column(String, nullable=True)
    currency      = Column(String(8), nullable=True)
    travel_blurb  = Column(String, nullable=True)               # short free-text, also fed to LLM
    created_at    = Column(DateTime, server_default=func.now()) # for "member since" if not present
```

Auto-migrate (`backend/app/db/auto_migrate.py`) will add the new columns on next FastAPI startup. `personas = NULL` ⇒ "never set"; `[]` ⇒ "explicitly skipped." This distinction drives the onboarding gate.

**2. Persona catalog (single source of truth)** — new file `backend/app/config/persona_catalog.py`

```python
from enum import Enum

class Persona(str, Enum):
    FOODIE = "foodie"
    CULTURE_BUFF = "culture_buff"
    NATURE_LOVER = "nature_lover"
    ADVENTURE_SEEKER = "adventure_seeker"
    BEACH_BUM = "beach_bum"
    HISTORY_NERD = "history_nerd"
    NIGHTLIFE = "nightlife_enthusiast"
    SHOPAHOLIC = "shopaholic"
    WELLNESS = "wellness_seeker"
    PHOTOGRAPHER = "photographer"
    FAMILY = "family_traveller"
    SOLO = "solo_explorer"
    LUXURY = "luxury_traveller"
    BUDGET = "budget_hacker"

PERSONA_LABELS: dict[Persona, str] = { Persona.FOODIE: "Foodie", ... }
PERSONA_DESCRIPTIONS: dict[Persona, str] = {
    Persona.FOODIE: "Loves local cuisine, street food, and reservation-only restaurants.",
    # ...one short LLM-friendly hint per persona...
}
```

Descriptions are the *LLM-facing* hints — concise, flavourful, prompt-ready. **This file is the only place where the catalog is defined**; both API and frontend consume it via the catalog endpoint below. To iterate the list, edit one file and ship.

**3. API endpoints** — extend `backend/app/api/endpoints/users.py`

```
GET  /users/personas/catalog  → [{ slug, label, icon, description }, ...]      # public; FE renders chips from this
GET  /users/me/personas       → { "personas": ["foodie", "wellness_seeker"] | [] | null }
PUT  /users/me/personas       body { "personas": [...] }  → 200 + updated record   # [] is valid (explicit skip)
PUT  /users/me                body { name?, avatar_url?, home_city?, timezone?,
                                     currency?, travel_blurb?, password? }     # comprehensive profile edit
POST /users/me/avatar         multipart file upload  → { "avatar_url": "..." } # stores under /static or S3 stub
```

Validate persona input against the `Persona` enum (reject unknown values with 422). Empty list is allowed and represents explicit skip. Reuse existing `get_current_user` dependency.

**4. LLM injection** — `backend/app/services/llm/services/v1/roammate_v1.py:_pack_trip_context()` (line 87-113)

Add a helper:

```python
def _pack_user_persona(user: User) -> str:
    if not user.personas:
        return ""
    descriptors = [PERSONA_DESCRIPTIONS[Persona(p)] for p in user.personas
                   if p in Persona._value2member_map_]
    if not descriptors:
        return ""
    return "User preferences: " + " ".join(descriptors)
```

Append the result to the context string built in `_pack_trip_context()`. All three prompt entry points (`chat`, `plan_trip`, brainstorm extract) receive context through the same packer, so one injection covers all three. Validate by token-counting before/after — should add <120 tokens worst case.

> **Only persona slugs are sent to the LLM.** `home_city`, `travel_blurb`, `timezone`, `currency`, and `avatar_url` are stored and shown on the Edit Profile tab but **not** injected into prompts. We keep the LLM change tightly scoped to personas; we can revisit injecting profile fields later once we have signal on persona impact.

Update prompt templates in `backend/app/services/llm/services/v1/prompts/` only if needed to acknowledge the new context line; in practice the existing "Use the provided context" instruction already covers it.

**5. Tests** — `backend/tests/`

- `test_users_personas.py`: GET/PUT roundtrip, invalid persona slug → 422, auth required.
- `test_roammate_v1_persona.py`: build a User with 2 personas, assert `_pack_trip_context()` output contains both descriptors and trip data still intact.
- Snapshot test: brainstorm chat with persona vs without — assert prompts diverge in the expected line.

### Frontend

**6. 3-dot menu** — `frontend/app/dashboard/page.tsx:245-261`

Replace the inline `LogOut` button with a `MoreVertical` icon trigger. New component `frontend/components/UserMenu.tsx`:

- Renders the user pill (initials + name + email) — extract from current dashboard.
- 3-dot trigger opens a small popover (use a lightweight click-outside hook; no Radix needed to stay dep-light).
- Items: **Profile** → `router.push('/profile')`; **Logout** → existing `handleLogout`.

**7. Profile shell** — new `frontend/app/profile/page.tsx` + `frontend/app/profile/layout.tsx`

- `layout.tsx` renders the two-column shell with left nav and child route content.
- Sub-routes:
  - `/profile` → redirects to `/profile/edit` (**default tab**).
  - `/profile/edit` → comprehensive Edit Profile form (see component spec below).
  - `/profile/persona` → the picker.
  - `/profile/subscription` → "Coming Soon" placeholder card.
- Reuse `useAuth()` hook from `frontend/hooks/useAuth.tsx`; gate with redirect to `/login` if no token.

**7a. Edit Profile component** — new `frontend/components/EditProfile.tsx`

- Sections matching the design spec (Header card, Identity, Preferences, Security, Danger zone).
- Sub-components:
  - `AvatarUploader.tsx` — drag-and-drop + crop (use `react-easy-crop` if dep allowed; otherwise a small custom crop using a canvas; emit a Blob → `POST /users/me/avatar`).
  - `InlineEditField.tsx` — pencil-icon-driven inline edit with optimistic save on blur/Enter, revert on Esc.
  - `PasswordChangeBlock.tsx` — three inputs + zxcvbn-style strength bar (no new dep — implement a small heuristic).
  - `DeleteAccountModal.tsx` — type-to-confirm.
- Uses a single `useProfile()` hook that wraps `GET /users/me` + `PUT /users/me` with SWR-style caching (manual via `useState` + `fetch`; no need for SWR dep). Tracks `dirty` per-field for the unsaved-changes pill.

**8. Persona picker** — new `frontend/components/PersonaPicker.tsx`

Props:

```ts
type PersonaPickerProps = {
  initial: string[];
  onSave: (selected: string[]) => Promise<void>;
  layout?: "page" | "onboarding"; // controls hero copy + footer style
};
```

Internals:

- **Catalog fetched at runtime** from `GET /users/personas/catalog` (cached in a top-level React context after first load). No hard-coded persona list on the frontend — adding/removing personas requires only a backend redeploy.
- Local state for selected slugs; `dirty = !arraysEqual(selected, initial)`.
- Render chips with Tailwind classes per design spec; selected state toggles `border-indigo-600 border-2 bg-indigo-50`.
- Save button calls `onSave`, optimistic update + toast.
- Used by both the `/profile/persona` tab and the onboarding modal.

**9. Onboarding modal (over the login page)** — new `frontend/components/OnboardingPersonaModal.tsx`

- **Not** a separate route. Rendered conditionally by the login page (`frontend/app/(auth)/login/page.tsx`) after a successful signup or after a login where the server returns `personas === null`.
- Implementation: a fixed-position overlay with `backdrop-blur-md bg-slate-900/40` covering the login form, plus a centred mid-size modal (`max-w-[640px] w-[90vw] rounded-3xl bg-white shadow-2xl`) with a fade + scale-up entry animation.
- Modal locks focus inside itself (focus trap), and the backdrop click + Esc are **suppressed** — the user must Continue or Skip to dismiss. This guarantees `personas` is always set to a list (never left as `null`) once the user reaches the dashboard.
- Calls `PUT /users/me/personas` with the selected list (or `[]` for skip), then `router.push('/dashboard')`.
- If skipped, sets `localStorage.persona_soft_prompt_shown = '0'` so the dashboard banner appears.

**9a. Onboarding gate** — update `frontend/hooks/useAuth.tsx`

- After login/signup, expose `user.personas` (now part of `/users/me` payload).
- The login page reads this and renders `<OnboardingPersonaModal />` when `personas === null`. Existing users with `[]` or a list bypass the modal entirely and go straight to `/dashboard`.

**9b. Soft-prompt banner** — new `frontend/components/PersonaSoftPrompt.tsx`

- Rendered in the dashboard sidebar (above the user pill) when `user.personas?.length === 0` and `localStorage.persona_soft_prompt_dismissed !== '1'`.
- Compact card: "Set your travel persona →" with a small ✕ to dismiss (writes the localStorage flag). Clicking the body navigates to `/profile/persona`.

**10. API client** — extend `frontend/lib/api.ts` (or wherever the existing `users/me` fetch lives) with `getPersonas()` and `updatePersonas(slugs: string[])`. Bearer token already handled.

### Implementation order (single PR)

All changes ship in one PR. Suggested commit-by-commit build order to keep the diff reviewable:

1. **Backend foundation** — `persona_catalog.py`, extended `User` columns, all new endpoints (`/users/personas/catalog`, `GET/PUT /users/me/personas`, extended `PUT /users/me`, `POST /users/me/avatar`), backend tests.
2. **LLM injection** — `_pack_user_persona()` wired into `_pack_trip_context()`, snapshot tests.
3. **Profile shell + UserMenu** — dashboard 3-dot menu, `/profile/`* routes, Subscription stub.
4. **Edit Profile (comprehensive)** — `EditProfile.tsx` and sub-components (avatar uploader, inline edit, password change, danger zone). Highest UX surface — give it the most manual QA.
5. **Persona picker** — `PersonaPicker` (catalog-driven), `/profile/persona` page.
6. **Onboarding modal + soft prompt** — `OnboardingPersonaModal` over login, `PersonaSoftPrompt` banner, `useAuth` updates.

Open the PR only after step 6 + full verification pass.

### Files to create / modify

**Create:**

- `backend/app/config/persona_catalog.py`
- `backend/tests/test_users_personas.py`
- `backend/tests/test_users_profile.py`
- `backend/tests/test_roammate_v1_persona.py`
- `frontend/app/profile/layout.tsx`
- `frontend/app/profile/page.tsx`         (redirects to `/profile/edit`)
- `frontend/app/profile/edit/page.tsx`
- `frontend/app/profile/persona/page.tsx`
- `frontend/app/profile/subscription/page.tsx`
- `frontend/components/EditProfile.tsx`
- `frontend/components/AvatarUploader.tsx`
- `frontend/components/InlineEditField.tsx`
- `frontend/components/PasswordChangeBlock.tsx`
- `frontend/components/DeleteAccountModal.tsx`
- `frontend/components/PersonaPicker.tsx`
- `frontend/components/OnboardingPersonaModal.tsx`
- `frontend/components/PersonaSoftPrompt.tsx`
- `frontend/components/UserMenu.tsx`
- `frontend/hooks/useProfile.ts`
- `frontend/contexts/PersonaCatalogContext.tsx`

**Modify:**

- `backend/app/models/all_models.py` (User model — new columns)
- `backend/app/api/endpoints/users.py` (catalog, persona, profile, avatar endpoints)
- `backend/app/services/llm/services/v1/roammate_v1.py` (`_pack_trip_context` + helper)
- `frontend/app/dashboard/page.tsx` (UserMenu + soft-prompt banner)
- `frontend/app/(auth)/login/page.tsx` (render onboarding modal when `personas === null`)
- `frontend/hooks/useAuth.tsx` (expose `personas` + extended profile fields)
- `frontend/lib/api.ts` (persona, profile, avatar API client functions)

---

## Verification

**Backend:**

1. `cd backend && pytest tests/test_users_personas.py tests/test_roammate_v1_persona.py -v` — all pass.
2. Restart FastAPI; confirm auto-migrate logs show `personas` column added to `users` table.
3. With a JWT, `curl -X PUT /users/me/personas -d '{"personas":["foodie","adventure_seeker"]}'` returns 200; GET reflects the value.
4. Invalid slug returns 422.

**LLM:**
5. Run a brainstorm chat for a user with `personas=["foodie"]` and another with `personas=["wellness_seeker"]` on the same prompt ("Plan a day in Lisbon"). Outputs should differ in tone/recommendations. Capture both as snapshot fixtures.
6. Confirm token usage delta < 200 tokens/request (log via existing token counter in `RoammateServiceV1`).

**Frontend (manual):**
7. `cd frontend && npm run dev`. Sign up a fresh user → login page background blurs and dims, mid-size onboarding modal appears centred. Backdrop click + Esc do not dismiss it.
8. Select 3 chips inside the modal → borders turn indigo, scale up. Click Continue → modal animates out → land on `/dashboard`.
9. From dashboard, click ⋮ next to user pill → menu opens with Profile / Logout. Profile navigates to `/profile` which redirects to `/profile/edit` (default).
10. **Edit Profile tab:** edit name inline (Enter saves, Esc reverts). Upload an avatar → crop modal opens → confirm → header avatar updates with optimistic UI. Change timezone, currency, home city, travel blurb — each saves on blur with a checkmark animation. Try changing tabs mid-edit → "Unsaved changes" guard appears.
11. Switch to **User Persona** tab → previously selected chips highlighted; modify selection → Save button enables → click Save → toast → reload page, selection persists.
12. Visit `/profile/subscription` → see "Coming Soon" stub.
13. Logout from menu → returns to login page. Sign up a second new user, this time click **Skip for now** in the onboarding modal → land on dashboard with the soft-prompt banner visible above the user pill. Click banner → navigates to `/profile/persona`. Dismiss banner with ✕ → reloads do not show it again (localStorage flag).
14. Run a concierge chat as the onboarded user → output should reference their selected personas + travel_blurb at least implicitly (e.g., foodie user gets restaurant-heavy suggestions).
15. Edit `persona_catalog.py` to rename one persona → restart backend → frontend reflects the change with no FE redeploy (catalog endpoint test).

**Regression:**
14. Existing users with `personas=NULL` continue to receive identical LLM output to pre-feature behaviour (snapshot test).
15. Type-check + lint clean: `npm run typecheck && npm run lint`.