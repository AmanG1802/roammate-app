# Smart Ripple Engine — Complete Guide

> The travel-time-aware re-scheduler that keeps a trip day feasible after any
> single change. Move one event, and the rest of the day "ripples" to stay on
> schedule — automatically.

---

## What it is, in one line

When you push, pull, or resize one event on a trip day, the **Smart Ripple
Engine** intelligently shifts every downstream event by the right amount —
accounting for real driving time between venues — so the day still makes sense.

Think of it as the difference between a static calendar and a living itinerary.
A calendar just holds boxes of time. Smart Ripple understands that those boxes
are *places on a map* that take time to travel between, and it keeps the whole
chain honest whenever one link moves.

---

## Why it exists — the problem it solves

Group trips are fragile. A single real-world change cascades:

- Lunch runs 45 minutes late → the museum slot, the coffee stop, and dinner are
  all now wrong.
- You decide to swap a 2pm activity for one across town → the old "30-minute
  gap" to the next stop is no longer enough; it's now a 50-minute drive.
- You drag dinner an hour earlier → everything after it should slide too, but
  manually re-typing six time slots is tedious and error-prone.

Before Smart Ripple, the user had to hand-edit every affected event, one by one,
re-doing the mental math of "if this moves, what else moves, and by how much?"
That's exactly the kind of bookkeeping software should do for you.

**Smart Ripple removes the busywork and the mistakes.** One change in, a
correct, travel-aware day out.

---

## The core value adds

| Value add | What it means for the user |
|---|---|
| **One-touch rescheduling** | Change one event; the day re-flows itself. No manual cascade edits. |
| **Travel-time awareness** | Shifts respect *real* driving time between venues, not guesses. A tighter gap than the drive allows gets flagged. |
| **Respects what you've locked** | Events you pin ("our flight is at 6pm, don't touch it") are never moved — but they're still counted as stops on the route. |
| **Same-day safety** | Ripple stays within the day it started in. It won't silently bleed into tomorrow. |
| **Honest about feasibility** | If a shift would push an event past midnight, or outside a venue's opening hours, it tells you instead of producing a broken plan. |
| **Works from the timeline AND the AI Concierge** | Whether you drag an event by hand or ask the Concierge to "push everything 30 minutes," the same engine guarantees the same correct result. |

---

## How it behaves — the mental model

1. **You change one event** — move its start time, resize it, add a new event,
   or insert a nearby stop.
2. **That event becomes the "anchor."** Everything *before* it stays put.
   Everything *after* it is a candidate to shift.
3. **The engine walks forward through the day**, event by event, asking at each
   step: given when the previous stop *actually* ends, and how long it takes to
   *travel* to this next stop, when can this one realistically start?
4. **It slides each downstream event** to keep the chain feasible — preserving
   your intended gaps where it can, and closing or widening them based on real
   travel time.
5. **Locked events are treated as fixed waypoints** — never moved, but always
   counted, so travel time is measured *from* and *to* them correctly.
6. **It stops at the end of the day.** The cascade never crosses midnight; if a
   shift would, you get a clear message rather than a corrupted next day.

---

## What can trigger a ripple

Smart Ripple is invoked anywhere a single timing change can knock the rest of
the day out of alignment:

- **Moving an event** to a new start time.
- **Resizing an event** (making it longer or shorter).
- **Adding a new event** with a start time into an existing sequence.
- **Adding a "nearby" stop** via the Concierge (e.g. "find a coffee place near
  the museum and slot it in") — the inserted stop pushes later events.
- **A direct "shift my whole day by N minutes"** request.

Critically, every one of these paths — whether the user dragged something on the
timeline or asked the AI in plain English — funnels through the *same* engine.
That's what makes the behavior predictable: there's one source of truth for
"what a correct day looks like."

---

## The guardrails (why it's trustworthy)

A reschedule engine is only useful if you can trust it not to quietly wreck your
plan. Smart Ripple's guardrails are as much a feature as the shifting itself:

- **Cross-midnight protection.** A late-running cascade won't roll silently into
  the next day. If an event *would* land past midnight, the engine stops at the
  last safe event and reports exactly where it stopped ("Shifted 4 events —
  Dinner would run past midnight, so I stopped there"). Nothing gets corrupted.
- **Locked events are sacred.** Pin the things that genuinely can't move (flights,
  reservations, a show with fixed tickets). They're never shifted — but they're
  still part of the route math, so travel times around them stay correct.
- **Travel-infeasibility warnings.** If the resulting gap between two stops is
  smaller than the real drive between them, you're warned — the plan isn't
  silently presented as fine.
- **Opening-hours awareness.** When venue hours are known, a shift that would
  land you at a place after it closes (or before it opens) raises a flag —
  e.g. "Louvre closes 6:00pm — this lands 6:40–8:10pm." *Warn-and-allow:* it
  never blocks you or reorders your day on its own; it just makes sure you're
  not surprised.
- **Resilient to map hiccups.** If a travel-time lookup fails transiently, the
  engine retries before falling back — so a momentary network blip doesn't
  silently truncate your cascade and leave half the day un-shifted.
- **Caller-controlled commit.** When something can't be completed cleanly, the
  change is either fully applied or cleanly rolled back — never left half-done.

---

## "Warn-and-allow" — the design philosophy

Smart Ripple intentionally **never blocks** you and **never reorders** your day
behind your back. Its job is to do the mechanical shifting correctly and to
*surface* anything that looks off — overlaps, tight travel gaps, midnight
spillover, closed venues. The human stays in control of the final call.

This matters for a group-trip app: people make deliberate, weird-looking
choices ("yes I know the café closes at 5, we're grabbing it to-go"). The engine
respects that. It informs; it doesn't overrule.

---

## How it fits with the rest of Roammate

- **Powers the Concierge.** When the AI Concierge moves, adds, or reschedules
  anything, Smart Ripple is what makes those edits land correctly. The Concierge
  is the brain; Smart Ripple is the hands that keep the day feasible. See the
  [Concierge Service guide](./concierge-service.md).
- **Feeds the preview/undo experience.** Smart Ripple can run in a **dry-run**
  mode — computing the *full* projected cascade without committing anything. This
  is what lets the Concierge show a "before → after" preview of a change *before*
  you confirm it, and what makes a clean undo possible.
- **Reuses the day's real route data.** It leans on the same travel-time and
  route information the app already computes for drawing map routes, so it's both
  accurate and efficient at scale.

---

## What it deliberately does *not* do (today)

Being explicit about the boundaries keeps expectations honest:

- **No cross-day cascade.** A late event won't roll work onto tomorrow — it stops
  at the day boundary and tells you. (Multi-day roll-forward is a future idea.)
- **Driving-only travel times.** Walking, transit, and cycling durations aren't
  modeled yet; estimates assume driving.
- **No cross-day moves via chat.** Moving an event to a different day is done by
  dragging it on the timeline, not by asking the Concierge.
- **It detects, it doesn't auto-fix feasibility.** Overlaps and closed-venue
  warnings are surfaced, not silently resolved by reordering your day.

---

## TL;DR

Smart Ripple turns a brittle list of timed events into a **living, travel-aware
day plan**. Change one thing and the rest stays correct — automatically, with
real driving times, respect for what you've locked, and honest warnings when
something won't fit. It's the quiet engine that makes both manual timeline edits
and AI Concierge changes *just work*.
