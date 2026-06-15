# AI Concierge Service — Complete Guide

> The on-trip AI assistant that turns "I wish someone would just fix my
> itinerary" into a one-line chat request. Roammate's flagship, USP-defining
> feature for the *during-the-trip* experience.

---

## What it is, in one line

The **Concierge** is an AI chat that lives inside an active trip and can actually
*do things* to your itinerary — move events, add stops, find nearby places,
reschedule your day — in plain English, with a preview before it commits and an
undo after.

Where the Brainstorm chat helps you *plan* a trip beforehand, the Concierge is
your assistant *on the ground*, while the trip is happening.

---

## Why it exists — the problem it solves

Plans break in real life. You're standing outside a museum that's more crowded
than expected, it's raining, lunch ran long, and you want to grab coffee nearby
and push everything back 30 minutes. Doing that by hand means:

- Mentally recomputing every downstream time slot.
- Searching a map for a coffee place that's actually close.
- Editing five or six events one at a time on a small phone screen.
- Hoping you didn't create an impossible gap or double-book yourself.

The Concierge collapses all of that into a sentence: *"Find a coffee place near
the museum and push the rest of my afternoon back 30 minutes."* It understands
your whole trip, proposes the exact changes, shows you a clear before/after, and
applies them correctly — using the [Smart Ripple Engine](./smart-ripple-engine.md)
under the hood to keep the day feasible.

**This is the feature meant to make Roammate indispensable mid-trip** — the
difference between an app you use to plan and an app you keep open the whole
journey.

---

## The core value adds

| Value add | What it means for the user |
|---|---|
| **Natural-language itinerary control** | "Move dinner to 8," "add a sunset point near the beach," "shift my whole day 45 minutes." No menus, no manual time math. |
| **Preview before commit** | Every proposed change shows a scannable before → after diff — *which* events move, from when, to when — before anything is saved. |
| **Undo last action** | Changed your mind? One tap reverts the entire last action — the anchor event *and* every event the ripple shifted. |
| **Whole-trip awareness** | The Concierge reasons about your *entire* multi-day trip, not just today — so it understands context across the whole journey. |
| **Real travel-time reasoning** | It knows the *actual* driving times between your stops, so its suggestions and reschedules are physically realistic. |
| **Opening-hours awareness** | It avoids proposing visits when a venue is closed, and flags any change that would land you somewhere outside its hours. |
| **Shared group chat** | One Concierge conversation per trip, visible to the whole group — everyone sees what was asked and what changed, with author labels. |
| **Safe by design** | Changes are gated, previewed, and reversible. It assists; it never silently rewrites your trip. |

---

## What the Concierge can actually do

It's not just a chatbot that talks — it takes real, auditable actions on your
itinerary:

- **Move an event** to a new time (and ripple the rest of the day to match).
- **Add a new event** at a chosen time.
- **Find a nearby place** ("a tapas bar near our hotel") and slot it into the
  day, pushing later events as needed.
- **Shift the whole day** (or the rest of it) by a chosen amount.
- **Skip / unskip** events.
- **Answer itinerary questions** — "what's next?", "what does today look like?" —
  for *every* member of the trip, including those who can't make edits.

Every action that changes the itinerary is recorded so it can be previewed,
confirmed, and undone.

---

## The experience — how a request flows

1. **You ask in plain English** inside the trip's Concierge chat.
2. **The Concierge understands the request** against the full context of your
   trip — all days, real travel times between stops, and (where known) venue
   opening hours.
3. **It proposes a concrete change** — not just a sentence, but a structured
   **preview**: a before → after timeline diff showing each affected event's old
   and new times, a summary header ("Shifts 3 events, +40 min total"), and
   warning chips for anything questionable (tight travel gap ⚠, past midnight 🌙,
   venue closed 🕗).
4. **You review and confirm** — or cancel. Nothing is saved until you confirm.
5. **On confirm, the change is applied for real** — the Smart Ripple Engine does
   the feasible rescheduling, and the action is logged.
6. **If you regret it, undo** — the entire action reverts in one step.

The key idea: the Concierge **proposes, you dispose.** It does the hard thinking
and the tedious editing; you keep the final say.

---

## Preview + feasibility warnings (the trust layer)

The preview is what makes the Concierge safe to actually use on a real trip.
Before committing, it shows:

- **A before → after diff** — every affected event as a row, old time struck
  through, new time highlighted, color-coded by direction of the shift
  (e.g. `Dinner 7:30 → 8:40pm`).
- **A summary header** — "Shifts 3 events, +40 min total" — so you grasp the
  blast radius at a glance.
- **Non-blocking warning chips** for each feasibility issue:
  - ⚠ **Travel-infeasible** — the gap is smaller than the real drive.
  - 🌙 **Cross-midnight** — the change would push past the end of the day.
  - 🕗 **Opening-hours** — the venue is closed during the proposed window
    ("Louvre closes 6pm").

These warnings **inform but never block** (the "warn-and-allow" philosophy
inherited from Smart Ripple). The group might *deliberately* want a tight
schedule — the Concierge respects that, while making sure no one is surprised.

---

## Shared, group-wide conversation

The Concierge chat is **one conversation per trip, shared across the whole
group** — not a private thread per person. This matters for collaborative
travel:

- Everyone sees what was asked and what changed, with **author labels**
  ("Aman: push dinner to 8").
- A single proposed change is confirmed once by any eligible member — no
  duplicate edits, no confusion about who did what.
- It becomes a shared log of how the day evolved.

**Read for everyone, write for the right people.** *All* trip members can read
the conversation and ask questions (a natural place to show non-subscribers the
value). Making changes — proposing and confirming itinerary edits — is reserved
for trip admins on the Plus plan. Reading is open; editing is gated.

---

## Real context = better suggestions

Two things make the Concierge's advice trustworthy rather than generic:

- **Whole-trip, multi-day context.** It sees your full itinerary grouped by day,
  not just today — so it understands the shape of the whole journey when it
  reasons or reschedules.
- **Real travel times.** It uses the *actual* computed driving times between your
  consecutive stops, so it never proposes something that's physically impossible
  to pull off, and its reschedules land in realistic windows.
- **Opening-hours guidance.** Where venue hours are known, they're fed into the
  Concierge's reasoning so it tries to avoid suggesting closed-venue visits in
  the first place — and the preview catches any that slip through.

---

## How it fits with the rest of Roammate

- **Built on Smart Ripple.** Every reschedule, move, add, and nearby-insert the
  Concierge performs is executed through the
  [Smart Ripple Engine](./smart-ripple-engine.md), which guarantees the day stays
  travel-feasible and within bounds. The Concierge is the intelligent interface;
  Smart Ripple is the reliable mechanism.
- **Complements Brainstorm chat.** Brainstorm helps you *plan* (gather ideas into
  bins before the trip); the Concierge helps you *adapt* (change the live
  itinerary during the trip). Two AI surfaces, two jobs.
- **Tier-aware.** Reading is open to all members (an upsell surface for free
  users); itinerary-changing actions require Roammate Plus + admin role.

---

## Safety, access, and reversibility — at a glance

- **Gated writes** — only Plus admins can change the itinerary; everyone can read
  and ask questions.
- **Preview-first** — no change is committed without an explicit confirm.
- **Fully reversible** — undo reverts the complete last action, including every
  rippled event.
- **Honest** — feasibility and opening-hours warnings surface problems instead of
  hiding them.
- **Auditable** — actions are logged with their author in the shared thread.

---

## What it deliberately does *not* do (today)

- **No cross-day moves via chat.** Moving an event to a *different day* is done by
  dragging it on the timeline; the Concierge will tell you so rather than guess.
- **It proposes, it doesn't auto-apply.** Nothing changes without your confirm.
- **It warns, it doesn't overrule.** Feasibility and hours issues are flagged,
  never used to silently block or reorder your day.

---

## TL;DR

The Concierge is Roammate's **in-trip AI co-pilot**: ask for any itinerary change
in plain English, see a clear preview of exactly what will move, confirm, and
undo if you change your mind — all shared with your group and all kept feasible
by the Smart Ripple Engine. It's the feature designed to keep Roammate open and
useful for the entire trip, not just the planning phase.
