# Roammate — Sales & Marketing Pitch

> **Internal knowledge base** for sales, marketing, and landing-page copy.
> **Owner:** Aman Gupta · **Last updated:** 2026-05-22

---

## The one-liner

**Roammate is an AI-native travel planner that doesn't just help you build
a trip — it adapts with you while you're on it.**

Most travel apps stop the moment you board the plane. Roammate keeps working: re-routing your day when you're running late, suggesting a coffee shop near your next stop, and re-balancing the group's itinerary when plans change in real time.

Available on the **web** and as a **native iOS app**, with the same trip living seamlessly across both surfaces.

---

## The problem we solve

Planning a trip today is a mess of seventeen browser tabs, a shared Google Doc nobody updates, a Notes app full of half-remembered recommendations, and a Maps app that has no idea why you're going where you're going. And the moment something changes — a delayed flight, a closed restaurant, a friend who's running late — the whole carefully built plan falls apart, because nothing is actually connected.

We see three concrete failure points:

1. **Inspiration → Plan is broken.** People collect ideas everywhere (Instagram, blogs, friends' recommendations) but converting them into a structured day-by-day itinerary is manual, tedious, and nobody enjoys it.
2. **Group planning is painful.** Two-to-six people can't agree on what to do, where to eat, or who's "in" on a side trip. Decisions happen in group chats, get lost, and nobody owns the source of truth.
3. **Live trips have no co-pilot.** Once the trip starts, your tools become read-only. Nothing reacts to reality. Run late by 45 minutes and you're back to manually rescheduling on a phone screen at a bus stop.

Roammate addresses all three with one connected product.

---

## Who it's for

| Segment | Why they love us |
|---|---|
| **Group travelers** (friends, couples, families) | We turn the messy group chat into a structured, voted-on itinerary. |
| **Curious explorers** | We surface ideas they'd never find on their own and let them organise visually. |
| **Type-A planners** | Drag-drop timeline, conflict detection, multi-day routing — finally a tool that matches the depth of their planning instinct. |
| **First-time international travelers** | The AI concierge holds their hand when something goes wrong abroad. |
| **Mobile-first travelers** | A real native iOS app — not a wrapped webview — for when planning happens on the move. |

We are **not** trying to be a booking engine (Booking.com / Expedia) or a route planner (Google Maps). We sit *above* those tools — owning the trip narrative end-to-end and integrating with the booking/routing layer underneath.

---

## What we offer — features by surface

### 1. Brainstorm Mode — turn loose ideas into a real plan

A private AI chat for each trip. Travelers describe what they're
thinking ("we want a long weekend in Lisbon, foodie vibes, no
big-bus tourist stuff") and Roammate proposes places, neighbourhoods,
day themes, and hidden gems. With one tap, those suggestions become
structured **Idea Bin** entries — each enriched with photos, ratings,
addresses, and category tags — ready to be scheduled. Duplicate
detection keeps the bin clean even after multiple brainstorm sessions.

**Value:** collapses the "inspiration → plan" gap from days of
copy-pasting to a five-minute conversation.

### 2. Idea Bin — the shared whiteboard before scheduling

A drag-and-droppable list of places, restaurants, and activities the
group is considering. Members vote (up/down) on each idea. The bin
auto-enriches every entry in the background with category, rating, and
photo so cards aren't blank rectangles. Filter by category, see who
added what, and re-rank by votes.

**Value:** every group member can contribute and have a voice **without
hijacking the plan**. The vote tally surfaces consensus before the
itinerary gets touched.

### 3. Plan Mode — the visual day-by-day timeline

The core scheduling surface. Three connected panels (Timeline · Map ·
Idea Bin) let users drag an idea onto a day, pick a time, see the route
emerge on the map, and watch conflict detection flag any overlapping
events instantly. Multi-day trips get day-by-day navigation with
automatic route legs (driving vs. walking) and travel-time estimates.
Timezone-aware throughout — a Tokyo morning event reads correctly
whether you're scheduling it from London or Mumbai.

**Value:** the *only* itinerary tool that gives travelers a single
canvas where ideas, time, and geography coexist. No more reconciling a
shared doc with Google Maps in your head.

### 4. Concierge Mode — the live trip co-pilot

This is our most differentiated surface. Once the trip starts, Roammate
flips into a real-time assistant:

- **"Running late by X minutes"** — Roammate ripple-shifts every
  downstream event on today's itinerary and pings the group.
- **"Skip next"** — drop the upcoming stop with a single tap;
  Roammate compresses the schedule.
- **"Find coffee" (or anything) near me** — uses live location to
  surface three highly-ranked options with photos and travel time;
  one tap inserts the stop into your day.
- **Free-form chat** — ask the AI anything ("museum open after
  7pm?", "vegetarian dinner walking distance from our hotel?") and
  get an answer grounded in the rest of your itinerary.

**Value:** every other planner becomes useless the moment reality
diverges from the plan. Roammate gets more useful.

### 5. People Mode — group coordination that doesn't suck

Invite collaborators by email with one of four roles:

- **Admin** — full edit access.
- **Editor** — can modify the plan but not change roles or delete
  the trip.
- **Voter** — view-only, but can vote on ideas to influence the plan.
- **Viewer** — read-only.

Plus a **Groups** surface for recurring travel circles ("Annual
roommates trip"), so future trips inherit the social graph.

**Value:** clear authority over the plan without locking your friends
out of the conversation. The voter role is a deliberate design choice
— the loud opinion holder doesn't drown out the quiet one.

### 6. Personas — preferences that make the AI yours

On first login (web or iOS) users pick from curated personas
(e.g. "Foodie", "Slow Traveler", "Active Adventurer", "Cultural
Deep-Diver"). The brainstorm AI and concierge weight their suggestions
accordingly. Skipped now? No problem — set it anytime from your profile.
iOS surfaces the persona picker as a native bottom sheet during
onboarding.

**Value:** the AI's suggestions feel like a knowledgeable friend who
knows your taste, not a generic top-10 listicle.

### 7. Maps that finally understand your trip

Multi-day routing, day filtering, walk-vs-drive leg detection, route
refresh when the timeline changes, fit-all-markers, fullscreen mode,
legend overlay, and a fully mobile-responsive overlay layer. Markers
are clustered intelligently when the trip spans a city. Per-provider
location biasing means searching "Central Park" inside a Mumbai trip
no longer returns the one in New York. On iOS, the same map experience
runs on **Apple Maps natively**.

**Value:** the map shows *your* day, not a soup of pins. Switching
between Day 2 and Day 4 takes one tap.

### 8. Notifications & activity feed

Every meaningful action — someone joined the trip, an idea was added,
a role changed, a day was deleted — surfaces in the bell with a single
tap to the relevant trip. New notifications make the bell shake so
you don't miss them.

**Value:** group context without having to re-read the chat.

### 9. Native iOS app

A first-class SwiftUI app, not a wrapped webview. MVVM architecture,
StoreKit 2 subscriptions, Apple Maps integration, native bottom-sheet
persona onboarding, disk-cached offline tolerance, and pull-to-refresh
across dashboard and trip surfaces. Sign-in supports Google and Apple
out of the box.

**Value:** mobile is where travelers actually live during a trip. A
real native app makes the concierge feel like a phone-first experience,
not a desktop tool squeezed onto a screen.

### 10. Plus subscription — the upgrade tier

A paid tier gates the heaviest AI surfaces (extended brainstorm
sessions, unlimited concierge usage, advanced re-flow). Free users get
a generous starter quota; Plus removes the ceiling. Razorpay handles
India billing on the web; StoreKit 2 handles in-app purchases on iOS,
with a clean onboarding flow decoupled from the persona picker.

**Value:** a clear monetization path that doesn't compromise the free
experience for casual users while funding the AI cost of power users.

---

## What makes Roammate different

| Most travel tools | Roammate |
|---|---|
| Static itineraries you build and forget | A **live plan** that adapts during the trip |
| One person owns the doc; everyone else suggests in chat | **Structured group input** via votes + roles |
| AI bolted on as a chatbot | AI **woven into every surface** — brainstorm, planning, concierge |
| Map and itinerary live in different apps | **Single canvas** with timeline, map, ideas connected |
| Generic recommendations | **Persona-aware** suggestions tailored to traveler style |
| Plan ends when the trip starts | **Concierge mode** activates day-of and stays useful |
| Web-only or wrapped-webview mobile | **Real native iOS** alongside a polished web app |

---

## How the pieces add up — the magic moment

A four-person friend group plans a weekend in Lisbon. One opens
Roammate, brainstorms with the AI for ten minutes, and ends up with
twenty enriched ideas in the bin. Invites the other three. They each
upvote what they're excited about. The Admin drags the top-voted
ideas onto a day-by-day timeline; the map updates as they go. Day-of,
their morning museum runs forty minutes long. They tap *Running Late
+45 min* on their phone. The whole day re-flows. After lunch the
rooftop bar they wanted is closed. *Find Bar near me*. Three options.
One tap. Inserted. Group chat doesn't even need to happen.

**That's the pitch in one paragraph.**

---

## Trust & polish signals (what's already there)

These are concrete UX investments worth name-checking on the landing
page and in demos:

- **Native on iOS, polished on web** — not a hybrid hack; SwiftUI on
  iOS, Next.js on web, one backend.
- **Mobile-first web** — every web surface works at 320px width
  (sidebar drawer, tabbed plan-mode, kebab map menu).
- **Optimistic UI** — drag-drop, voting, time edits feel instant; the
  app reconciles with the server in the background.
- **Real error feedback** — if something fails, the user knows and can
  retry. No silent dropped actions.
- **Accessibility** — keyboard-friendly modals, `aria-live` regions for
  AI responses, dialog roles on confirmations, `prefers-reduced-motion`
  respected.
- **Sub-second route transitions** — view transitions API + prefetched
  data caches.
- **Offline tolerance** — cached profile when the network drops on
  web; on-disk cache on iOS; user is told they're seeing stale data.
- **Timezone-correct everywhere** — events display in the trip's local
  time regardless of the device's timezone.
- **Auth that fits the platform** — Google + Apple Sign-In, email
  verification, refresh tokens; native Apple Sign-In on iOS.
- **Secure payments** — Razorpay for web (India), StoreKit 2 for iOS.

---

## Coming up next

The product roadmap from here. Items are ordered by current priority
but not committed to specific dates.

### Near term (next 4–6 weeks)

- **Brainstorm token streaming** — bring the brainstorm chat to parity
  with the concierge chat (which already streams). Backend SSE work is
  scoped.
- **Smart conflict resolver** — when the timeline detects a conflict,
  offer one-tap reflow suggestions ("move dinner 30 min later",
  "swap activity A and B").
- **Booking integrations** — link Idea Bin entries to OpenTable,
  Resy, GetYourGuide, Booking.com so reservations live on the trip
  instead of in inboxes. Highest commercial-value item still open.
- **iOS push notifications** — wire the activity feed through APNs so
  the concierge can ping the group from the lock screen.
- **Public trip share links + PDF export** — read-only URLs and a
  day-by-day printout for travelers who want a paper backup.
- **Frontend + backend test backfill** — Vitest specs for the Wave 1–5
  modules; pytest coverage for `roammate_v1` envelope and idea-bin LLM
  upgrade.

### Mid term (Q3 2026)

- **Idea Bin LLM upgrade** — the last originally-planned Phase 1 item;
  smarter category inference and cross-trip dedup.
- **Calendar sync** — two-way Google Calendar / Apple Calendar.
- **Flight & accommodation parsing** — forward a confirmation email
  to a trip address; we auto-create the events.
- **Trip templates & remixing** — start a new trip from someone
  else's public itinerary or from a curated template ("3 days in
  Tokyo, foodie focus").
- **Budget tracking** — per-event cost estimates, per-person split,
  multi-currency.
- **AI image grounding** — paste a photo URL or Instagram link, we
  extract the location and convert it to an Idea Bin entry.
- **Vibe Check & Smart Timeboxing** — morning energy prompt that
  swaps the day; transit-aware impossible-day warnings.

### Long term / vision

- **Marketplace of local guides** — verified local experts answer
  trip-specific questions inside the concierge.
- **Trip memories** — post-trip recap that auto-generates a
  photo-and-narrative wrap-up the group can share.
- **Multi-trip planning** — for digital nomads and "annual
  pilgrimage" groups, a higher-level view that spans years.
- **Offline-first sync layer** — Dexie/IndexedDB on web, deeper
  CoreData-style sync on iOS, so a trip is fully usable on a plane.
- **Android app** — natural extension once iOS economics validate.

---

## Asks for sales / marketing

When pitching, lean on these — in roughly this order — and reinforce
with the screenshots/recordings called out at the end of each item.

1. **The live concierge.** It is the most visceral demo and the
   clearest competitive moat. Always show this last after the planning
   flow so the prospect sees the full arc: ideas → plan → live
   adaptation. *Demo asset:* a 30-second clip of "Running Late +45m"
   reflowing a day on iOS.
2. **The group-with-roles model.** Anyone who has tried to plan a
   trip with three friends recognizes the pain immediately. The voter
   role lands particularly well with parents and trip organisers who
   want input without giving everyone edit rights. *Demo asset:* a
   side-by-side of the four role badges and a vote count flipping the
   bin order.
3. **Persona-based AI.** Most travel chatbots are generic; ours
   isn't. Show a side-by-side of the same prompt ("3 days in Lisbon")
   with "Foodie" vs. "Cultural Deep-Diver" selected — the brainstorm
   responses diverge meaningfully.
4. **Native iOS, not a webview.** Demo on a phone, not a simulator.
   Pull-to-refresh, native Apple Maps, Apple Sign-In, the persona
   bottom sheet — these all read as "real app" cues that a wrapped
   webview cannot fake.
5. **Mobile-first storytelling.** Lead with phone shots, not desktop,
   when the audience is consumer-leaning. Our mobile experience is
   genuinely good now — both web at 320px and the native iOS app.
6. **Single canvas (Timeline · Map · Ideas).** This is the most
   "obvious in hindsight" hook for type-A planners. A 5-second
   screenshot of the three panels with a route drawn out beats a
   paragraph of feature copy.
7. **Plus tier as proof of monetization.** When pitching investors or
   partners, the existence of a working subscription on both web
   (Razorpay) and iOS (StoreKit 2) demonstrates that the unit
   economics aren't hypothetical.

**Positioning guardrails:**

- **Don't over-index on "AI" as a category.** Position Roammate as
  *a better travel planner that happens to use AI*, not as "ChatGPT
  for travel." The latter is crowded and forgettable.
- **Don't pitch us as a booking site.** We sit *above* booking and
  routing layers; framing us as a Booking/Expedia competitor invites
  the wrong comparison.
- **Don't lead with feature counts.** Lead with the magic moment
  (concierge re-flowing a day) — features are the proof, not the hook.
- **Don't show the admin/internal surfaces.** They exist and are
  useful internally, but they confuse a consumer pitch.

---

## Pitch deck — slides at a glance

A tight 10-slide deck for investor/partner conversations. Each line is
the slide's single big idea — keep one headline, one supporting visual,
one stat or quote per slide. Do not crowd.

1. **Title.** "Roammate — the travel planner that travels with you."
   Logo, tagline, web + iOS badges.
2. **The problem.** "Plans break the moment the trip starts." Three
   icons: 17 tabs, dead group chat, frozen itinerary. One stat about
   travel-plan abandonment if available.
3. **The insight.** "Inspiration, planning, and the live trip should
   be one connected loop — not three different apps."
4. **The product in one image.** Single screenshot of Plan Mode
   (Timeline · Map · Ideas) with a route drawn. Caption: "One canvas.
   Ideas, time, geography."
5. **The magic moment — Concierge.** 3-frame storyboard: "Running
   late +45m" → day reflows → group notified. This is the slide that
   sells the deck.
6. **Group planning, solved.** The four role badges (Admin / Editor /
   Voter / Viewer) and a vote count reshuffling the bin. One-line
   value: "Everyone has a voice. One person owns the plan."
7. **AI that knows you — Personas.** Side-by-side of the same prompt
   with two personas selected, showing divergent suggestions.
8. **Built for mobile — native iOS.** A real phone shot of the iOS app
   running concierge, next to the web app on a laptop. Caption:
   "Same trip, both surfaces, fully native."
9. **Traction & monetization.** Plus tier (Razorpay + StoreKit 2),
   user/trip counts, retention or engagement stat, App Store presence.
   Adjust to current numbers before each pitch.
10. **What's next + the ask.** Booking integrations, push, calendar
    sync on the near-term roadmap. End with the specific ask
    (investment, partnership, hire, beta access).

**Optional appendix slides** to keep in reserve, not in the main flow:

- Competitive matrix (the "Most travel tools vs. Roammate" table).
- Architecture diagram (web + iOS + one backend) — for technical
  audiences only.
- Trust & polish signals (a11y, timezone, offline) — for
  detail-oriented enterprise buyers.
- Long-term vision (marketplace of local guides, trip memories,
  Android) — for investors asking about TAM.
