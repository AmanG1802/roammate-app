# Dashboard & Groups — Product Discovery Brainstorm

**Date:** 2026-04-17
**Method:** Multi-perspective ideation (PM / Designer / Engineer) — Teresa Torres, *Continuous Discovery Habits*
**Opportunity:** Evolve the post-login surface (Dashboard + Groups) into a daily-habit surface and a first-class collaborative travel primitive.

---

## Current State (2026-04-17)

**Dashboard sidebar:** Dashboard · My Trips · Trip Invitations · Groups (placeholder "Soon")

- **Dashboard tab:** greeting + grid of first 6 trips
- **My Trips:** full grid + search
- **Trip Invitations:** accept/decline collaborator invites on per-trip basis
- **Groups:** empty placeholder — no data model

**Core Roammate primitives already built:** `Trip`, `TripMember`, `Event`, `IdeaBinItem`, `NLPService`, `QuickAddService`, `RippleEngine`, `ConciergeActionBar`

---

## Ideation — 15 Ideas across Three Perspectives

### Product Manager (business value & outcomes)

- **P1 · Countdown Hero** — dashboard leads with nearest upcoming trip: days-to-go, weather, prep checklist, flight status
- **P2 · Cross-Trip Activity Feed** — aggregated updates across all trips (idea added, ripple fired, invite accepted)
- **P3 · Travel Stats & Milestones** — Strava-style gamification: cities/countries/days/distance, achievements
- **P4 · Inspiration Rail** — AI-recommended destinations based on past trips, season, group preferences
- **P5 · Post-Trip Memory Recap** — auto-generated recap (route, photos, stats) for shareability + retention

### Product Designer (UX & engagement)

- **D1 · Contextual "Today" Widget** — dashboard body swaps by trip state: pre-trip countdown, in-trip concierge panel, post-trip recap
- **D2 · Dashboard Quick-Add Bar** — NLP input: *"Cafe Gusto Rome Wed 8pm"* → routed to the right trip
- **D3 · Year-at-a-glance Timeline** — horizontal 12-month strip of all trips
- **D4 · Global Smart Search** — across events, ideas, collaborators, notes
- **D5 · Onboarding-as-Dashboard** — 3-step progress ring for first-time users

### Software Engineer (technical leverage)

- **E3 · Push/PWA Notifications** — actionable web-push for invites, ripples, alerts
- **E4 · Smart Inbox** — single signals feed: weather, flight delays, collaborator pings, price drops
- **E5 · Offline-First Dashboard** — Service Worker + IndexedDB cache

### New: Notification Center (Dashboard top-right)

- **N1 · In-app Notification Bell** — persistent bell icon on the main page header (top-right), unread count badge
- **N2 · Event Types covered:**
  - `Trip created` — *"You created Summer in Santorini"*
  - `Invite received` — *"Alex invited you to Tokyo 2026"*
  - `Invite accepted/declined` — *"You accepted Tokyo 2026"* · *"Sam declined Ski Trip"*
  - `Member added` — *"Priya was added to Italy 2026"*
  - `Member removed / left`
  - `Trip renamed / date changed` (by collaborator)
  - `Event added / moved / deleted` by collaborator
  - `Idea added to shared library` (Groups)
  - `Ripple fired` — *"Your 3pm museum was shifted to 4pm"*
  - `Vote on a poll` (Groups)
- **N3 · Dropdown panel UX:** grouped by day · unread ring · click routes to the relevant trip/group · "Mark all read" · "See all" opens a full notifications page

### Groups Section (all perspectives)


| #   | Idea                                                                            |
| --- | ------------------------------------------------------------------------------- |
| G1  | Persistent Groups as first-class entity (owns members + prefs + shared library) |
| G2  | Group Shared Idea Library (cross-trip idea persistence)                         |
| G3  | Group Voting & Consensus (polls, upvote/downvote, consensus rings)              |
| G5  | Group Memory Wall (all past trips together)                                     |
| G6  | Group Activity Feed                                                             |
| G9  | Group Polls (destinations/dates)                                                |
| G10 | Real-time Presence (avatar dots)                                                |
| G11 | Group Permissions Model (admin/member/viewer)                                   |


---

## Top Prioritized Ideas (across Dashboard + Groups)

### 1. Persistent Groups as First-Class Entity ⭐ *foundation*

Introduce `Group` model owning members, prefs, and shared idea library. Trips optionally belong to a group.

- **Why selected:** Foundation for every other Groups feature. Today each `Trip` re-invites people from scratch — huge friction for recurring travel squads. Directly serves the "group/family traveler" audience already called out in the brainstorm doc.
- **Assumptions:**
  - Users take ≥2 trips with overlapping collaborators
  - Pre-defining a group > ad-hoc per-trip invites
  - Group ownership of shared state feels useful, not over-structured

### 2. Contextual "Today" Widget on Dashboard (D1)

Hero slot swaps based on trip state: pre-trip countdown+prep · in-trip concierge quick actions · post-trip memory recap.

- **Why selected:** Implements the Travel Agent → Concierge transition on the home surface. Drives daily engagement — the hardest problem for travel apps.
- **Assumptions:**
  - Users return *during* trips (check session data mid-trip)
  - In-trip surface drives concierge action usage
  - Post-trip recap drives re-engagement / shareability

### 3. Group Voting & Consensus Tools (G3)

Upvote/downvote ideas, polls for dates/destinations, consensus indicators on ripple decisions.

- **Why selected:** Multiplayer planning is already a Phase 1 roadmap item. Voting is the killer feature for group travel (solves the 47-message WhatsApp thread problem).
- **Assumptions:**
  - Groups have ≥2 decision-makers (not planner + passengers)
  - Async voting preferred over chat for decisions
  - Consensus signals reduce planner burnout

### 4. Dashboard NLP Quick-Add Bar (D2)

Single NLP input at dashboard top → AI routes to the matching trip; disambiguation card when ambiguous.

- **Why selected:** Leverages existing NLPService + QuickAddService. Makes the dashboard a *capture tool*, not just a list.
- **Assumptions:**
  - Multi-trip routing accuracy ≥85% on first pass
  - Capture-on-the-go is a real user moment
  - Disambiguation UX doesn't feel annoying

### 5. Group Shared Idea Library (G2)

Ideas live at the group level and can be pulled into any trip owned by the group.

- **Why selected:** Makes Groups compound over time. Extends the existing IdeaBin primitive — lower lift than a new concept. Data compounds → stickiness.
- **Assumptions:**
  - Users remember and revisit places across trips
  - Library UX scales past ~50 ideas
  - Group-scope > personal-favorites scope

### 6. Notification Center (N1–N3)

Top-right bell on the main page, unread badge, dropdown panel showing grouped notifications across all trips and groups.

- **Why selected:** Closes the loop on every collaborative action. Today a user has no way to know Alex added an idea or Priya accepted an invite without manually hunting. A notification feed turns all the existing `TripMember` / `Event` / invite events into a real-time awareness layer.
- **Assumptions:**
  - Users want passive awareness of collaborator actions
  - Unread badge drives return visits
  - Grouping by day + routing on click is enough UX polish for v1 (no per-type filters needed yet)

---

## Phased Implementation Plan

### Phase 1 — Groups Foundation + Notification Center

**Backend — Groups**

- `Group` model (`id`, `name`, `owner_id`, `created_at`)
- `GroupMember` with roles (admin/member/viewer)
- `Trip.group_id` (nullable FK — preserves solo trips)
- `IdeaBinItem.group_id` (nullable — trip-scoped *or* group-scoped)
- Endpoints: `POST/GET /groups`, `POST /groups/{id}/invite`, `GET /groups/{id}/ideas`

**Backend — Notifications**

- `Notification` model (`id`, `user_id`, `type`, `payload` JSON, `trip_id?`, `group_id?`, `read_at?`, `created_at`)
- Event-emission hooks at existing action sites: trip create, invite create/accept/decline, member add/remove, event mutation, ripple fire, poll vote (once G3 ships)
- Endpoints: `GET /notifications` (paginated) · `POST /notifications/{id}/read` · `POST /notifications/mark-all-read` · `GET /notifications/unread-count`

**Frontend — Groups**

- Replace "Coming Soon" placeholder with Group list → Group detail
- Trip creation: optional "Part of a group?" selector
- Trip IdeaBin: tab between "Trip Ideas" / "Group Library"

**Frontend — Notifications**

- Bell icon in `/dashboard` header top-right (next to New Trip button)
- Unread count badge
- Dropdown panel: grouped by day · click routes to trip/group · "Mark all read" · "See all"
- Poll on an interval for v1; upgrade to WebSocket in a later phase

**Ship gate:** internal dogfood + 5 external users; measure group creation → 2nd trip conversion; measure notification click-through rate.

### Phase 2 — Dashboard Today Widget + NLP Quick-Add

- Dashboard state machine: no-trip / pre-trip / in-trip / post-trip variants
- Pre-trip: countdown + prep checklist · In-trip: sticky ConciergeActionBar + current event · Post-trip: auto-recap card
- Quick-Add input → existing NLPService, extended to multi-trip routing
- Disambiguation drawer when confidence < 0.8

### Phase 3 — Voting & Library Depth

- Voting primitives on `IdeaBinItem` **and** `Event` (timeline items). Up/down per member.
- Role gate: only `admin` and `view_with_vote` can cast votes; `view_only` can read tallies.
- Vote transfer: when an idea is promoted to the timeline (bin → event) or demoted back (event → bin), vote rows migrate with the item so history isn't lost.
- Group library search (`q`), tag filter (`tag`), source-trip filter (`trip_id`), and `sort=top|recent|title`.
- `IdeaTag(idea_id, tag)` model — lowercase, deduped, free-form; per-group tag cloud endpoint.
- Cross-trip copy endpoint with provenance via `IdeaBinItem.origin_idea_id` — tags travel with the copy.
- Ripple Engine locked to trip admins; `ConciergeActionBar` hidden from non-admins on the Live view.

### Phase 4 — Extensions (informed by prior phases)

Group memory wall · web push for notifications · real-time presence · offline-first dashboard — all have a Group home to hang from.

---

## Future Scope (post-Phase 4)

Ideas parked for now to keep the critical path tight.

### Ripple Decision Consensus (group-owned trips)

*Was originally drafted into Phase 3; deferred until voting + library + notifications have user data to validate the UX.*

When a trip is attached to a group, Ripple becomes a **proposal** rather than an immediate action:

- `RippleProposal(trip_id, proposer_id, delta_minutes, start_from_time, status, expires_at)` + `RippleApproval(proposal_id, user_id, decision)`.
- Small shifts (≤ 15m) auto-apply with a broadcast notification.
- Medium shifts (15–60m) require majority approval, else auto-apply after a 24h timeout.
- Large shifts (> 60m) require unanimous admin approval.
- Solo / non-group trips keep today's admin-only immediate behavior.

**Why deferred:** depends on the proposal/approval primitive that Phase 4's memory wall and offline sync may also want. Building it once we see how groups actually use voting avoids premature over-design.

---

## Recommended First Move

Start Phase 1 with the `Notification` model + emit hooks *first*, because every subsequent feature (Groups creation, invites, shared library) emits notification events. Building the notification plumbing up front means later features auto-populate the feed without retrofits.