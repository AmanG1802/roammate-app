# [34] Marketing Landing Page Refresh + iOS First-Launch Intro Cards

## Context

Roammate's web marketing landing (`frontend/app/page.tsx`) was the very first
surface built and has not been touched since. It still pitches a generic
"self-healing itinerary" tagline and mentions almost none of the features
that now make up the product — Brainstorm chat, Idea Bin + voting, group
roles, Plan Mode's single canvas, Concierge magic moment, Personas,
native iOS, Plus subscription. With feature freeze in place ahead of the
production launch sequence ([25]), the landing page needs to reflect what
the product actually does so sales/marketing/investor traffic lands on a
truthful, current pitch.

Separately, the iOS app currently drops first-time users directly into the
Login screen with no product context. Per the sales pitch
([32]), the most compelling moments (Concierge, group voting, personas) are
not discoverable until someone has signed up and built a trip. A short
swipeable intro — shown **once per install**, dismissable, never re-shown —
closes that gap without adding friction for returning users.

Both surfaces are pre-login marketing copy, so this plan is content,
visual, and routing only. No backend, no schema, no LLM. Existing theme
tokens and component patterns are reused; no new asset pipeline.

This plan is **complementary** to [33] (in-app guided NYC tour, fires
post-login), not a replacement.

---

## Decisions (from clarifying questions)


| Topic                          | Decision                                                                     |
| ------------------------------ | ---------------------------------------------------------------------------- |
| Web landing scope              | **Full replacement** of `frontend/app/page.tsx` in place.                    |
| Hero visual                    | **HTML/CSS Plan Mode mockup** (Timeline · Map · Idea Bin) — no image assets. |
| iOS persistence                | **Once per install** — UserDefaults global flag, survives logout/login.      |
| iOS lead feature after Welcome | **Brainstorm** (ideas → plan), then Group → Plan → Concierge → Personas.     |


---

# Part 1 — Website Landing Page

## 1.1 Surface

Single file rewrite of `frontend/app/page.tsx`. The existing
`components/layout/Navbar.tsx` and `app/layout.tsx` (Inter font,
`EntitlementProvider`, `ToastProvider`, `PaywallModal`) are reused as-is.
Middleware already classifies `/` as public — no routing changes.

## 1.2 Visual system — reuse what exists

All tokens already in `frontend/tailwind.config.ts` and
`frontend/app/globals.css`:

- **Primary:** `indigo-600` / `indigo-800` (matches iOS `roammateIndigo`).
- **Accents:** `violet-600`, `rose-500`, `amber-500`, `emerald-500`,
`fuchsia-500` (one per feature section, used sparingly for icon tints).
- **Neutrals:** `slate-50 → slate-950` scale, white surfaces.
- **Font:** Inter (already loaded).
- **Animation:** GSAP + ScrollTrigger (already in deps) for scroll
reveals; Framer Motion (already in `/pricing`) for in-section motion;
`prefers-reduced-motion` already wired in `globals.css`.
- **Icons:** `lucide-react` (already used) — `Sparkles`, `Users`,
`Map`, `Clock`, `Wand2`, `Smartphone`, `Apple`, `Globe`,
`MessageSquare`, `Check`.

No new fonts, no new colors, no new packages, no image assets.

## 1.3 Page structure (top → bottom)

1. **Sticky Navbar** (existing component, content additions only)
  - Add a `Pricing` link in the unauthenticated nav (currently absent).
  - Keep existing transparent-on-hero behavior.
2. **Hero**
  - Eyebrow chip: `Web · iOS` (slate-100 pill).
  - Headline: **"The travel planner that travels with you."**
  - Sub: "Most apps stop the moment you board the plane. Roammate keeps
  working — re-routing your day when you're late, finding a coffee shop
  near your next stop, and re-balancing the group's plan in real time."
  - CTAs: primary `Start free` → `/login?signup=true`; secondary `See it in action` → `#plan-mode` (smooth scroll).
  - Trust strip below CTAs: tiny inline icons + text — "Native iOS",
  "Mobile-first web", "Google + Apple sign-in".
  - Right column (`lg:` and up; stacks below on mobile): **HTML/CSS
  mockup of Plan Mode**. Three side-by-side rounded panels —
  `Timeline` (3 stacked event chips with times), `Map` (gradient
  square with a stylized polyline SVG + 4 pins), `Idea Bin` (4 vote
  chips with up-arrows). Whole composition wrapped in a `shadow-2xl`
  rounded-3xl card. Uses Tailwind only — no real map.
  - GSAP fade-up on title + subhead; mockup floats in with a 200ms
  delay.
3. **Problem strip** — "Plans break the moment the trip starts."
  - Three columns, each with a lucide icon + one sentence:
  1. `Layers` — "Seventeen browser tabs, one Google Doc, zero
    single source of truth."
  2. `MessageSquareOff` — "Decisions die in the group chat."
  3. `Snowflake` — "Your itinerary is frozen the moment things
    change."
    ain slate background. No animation beyond fade-in.
4. **Insight section** — one sentence centered:
  - "Inspiration, planning, and the live trip should be **one connected
   loop** — not three different apps."
5. **Feature 1 — Brainstorm** ("Turn loose ideas into a real plan")
  - Two columns. Right: HTML chat mockup — 3 rounded bubbles (user
   prompt + AI reply with a 3-item bullet list + a "+ Add to Idea
   Bin" pill).
  - Copy bullet points: AI per trip · auto-enriches places · duplicate
  detection.
  - Accent: `violet-600`.
6. **Feature 2 — Idea Bin + Voting** ("Group input without group chat chaos")
  - Two columns. Left: 4 stacked rounded cards each with a photo
   placeholder square, a category chip, a vote tally (`▲ 3`).
   Right: copy + the 4 role badges as inline chips (Admin · Editor ·
   Voter · Viewer) with one line each. Highlight Voter role — the
   "deliberate design choice" line from the pitch.
  - Accent: `rose-500`.
7. **Feature 3 — Plan Mode (the single canvas)** *(anchor `#plan-mode`)*
  - Full-width section. Larger version of the hero mockup, this time
   with the day-switcher (`Day 1 / Day 2 / Day 3`) visible above and a
   conflict-detection pill ("No conflicts ✓") below.
  - Copy: "Drag an idea onto a day. Pick a time. The route emerges on
  the map. Conflicts flag themselves. That's it."
  - Accent: `indigo-600` (primary).
8. **Feature 4 — Concierge (the magic moment)**
  - 3-frame storyboard mockup (CSS-only, animated with Framer Motion
   in-view): Frame 1 "Running late +45 min" chip. Frame 2 day
   reflowing (rows shifting down with motion). Frame 3 group
   notification toast.
  - Copy: the four concierge superpowers as a 2x2 grid (Running late,
  Skip next, Find X near me, Free-form chat).
  - Accent: `amber-500`.
  - This is the visual highlight of the page; GSAP pin-on-scroll for
  desktop, plain reveal on mobile.
9. **Feature 5 — Personas** ("AI that knows your style")
  - Side-by-side mini chat mockups: same prompt "3 days in Lisbon"
   with `Foodie` vs `Cultural Deep-Diver` persona chip selected, AI
   replies visibly differ in tone/items.
  - Accent: `fuchsia-500`.
10. **Feature 6 — Native iOS**
  - Stylized phone frame (rounded-[3rem] black border + notch) with a
    mini Concierge screen inside, next to a stylized desktop frame
    with Plan Mode.
    - Copy: SwiftUI, Apple Maps, Apple Sign-In, native bottom sheets,
    pull-to-refresh, StoreKit 2 Plus subscription, offline tolerance.
    - CTA: `App Store coming soon` placeholder badge (no live link yet
    — gated until App Store listing goes live; track in TODO).
    - Accent: `slate-900` (Apple-y).
11. **Trust strip** — six small tiles, one line each:
  Accessibility · Timezone-correct · Optimistic UI · Offline
    tolerance · Sub-second transitions · Razorpay + StoreKit 2.
12. **Pricing teaser**
  - Two capsule cards: `Free` (generous starter quota) and `Plus`
    (extended AI surfaces). "See Plus →" link to `/pricing`.
13. **Final CTA** — "Start planning the next one."
  - Primary button → `/login?signup=true`.
14. **Footer** — keep existing structure; update copy:
  - Product: Features, How it works, Pricing, iOS (placeholder)
    - Company: About, Contact, Privacy, Terms
    - Connect: socials (placeholder)

## 1.4 Responsive behavior

Mobile-first. All multi-column sections use Tailwind's
`grid-cols-1 md:grid-cols-2 lg:grid-cols-3` pattern that the current
landing already establishes. Hero mockup stacks below copy on mobile.
Verify at **320px** (project standard) — text scales down via
`text-4xl md:text-6xl lg:text-7xl`. The three-frame Concierge storyboard
collapses to a vertical stack on mobile.

## 1.5 Accessibility

- Each `<section>` gets a semantic id + `aria-labelledby`.
- Headings follow h1 → h2 → h3 hierarchy (one h1 for the hero).
- Animations gated behind `@media (prefers-reduced-motion: reduce)`
(already wired in `globals.css` line 25-35).
- All CTAs are real `<Link>` elements with discernible text.
- Icon-only nav items get `aria-label`.

## 1.6 Critical files

- `frontend/app/page.tsx` — full rewrite.
- `frontend/components/layout/Navbar.tsx` — add `Pricing` link in
unauthenticated nav.
- *(Optional)* `frontend/components/landing/*.tsx` — extract the larger
section components (Hero, PlanModeMockup, ConciergeStoryboard) if the
single file grows past ~600 lines. Otherwise keep inline like the
current page.
- `frontend/app/globals.css` — no changes expected; keyframes already
present.

---

# Part 2 — iOS First-Launch Intro Cards

## 2.1 Surface

A new full-screen swipeable view shown **before** `LoginView` on the
very first app launch after install. Six full-bleed cards, swipeable
horizontally, with page indicator dots and Skip / Next / Get Started
controls. Dismissing or completing marks a UserDefaults flag; the view
is never shown again on the same install.

## 2.2 Gating logic

Modify `ios/Roammate/Views/ContentView.swift`. Current branching:

```swift
if authManager.isAuthenticated { MainShell } else { LoginView }
```

Becomes:

```swift
if authManager.isAuthenticated {
    MainShell
} else if !IntroCardsFlag.hasSeen() {
    IntroCardsView(onFinish: { IntroCardsFlag.markSeen() })
} else {
    LoginView
}
```

Transition between `IntroCardsView → LoginView` uses the same
`.animation(.easeInOut(duration: 0.25))` already wrapping ContentView's
top-level switch.

## 2.3 Persistence — `IntroCardsFlag`

New file `ios/Roammate/App/IntroCardsFlag.swift`. Modeled on the
existing `PlusOnboardingFlag.swift` (`ios/Roammate/Subscription/`), but
**not** keyed on user_id — it's a single install-wide boolean.

```swift
enum IntroCardsFlag {
    private static let key = "intro_cards_seen_v1"
    static func hasSeen() -> Bool {
        UserDefaults.standard.bool(forKey: key)
    }
    static func markSeen() {
        UserDefaults.standard.set(true, forKey: key)
    }
    // No clear() — logout/login should NOT reset.
    // Reinstall naturally resets via OS clearing UserDefaults.
}
```

The `_v1` suffix lets us force-reshow later by bumping the key if we
overhaul the cards.

## 2.4 IntroCardsView

New file `ios/Roammate/Views/Onboarding/IntroCardsView.swift`.

Structure:

```swift
struct IntroCardsView: View {
    let onFinish: () -> Void
    @State private var page: Int = 0
    private let totalPages = 6

    var body: some View {
        ZStack(alignment: .top) {
            currentBackgroundGradient  // per-card tinted gradient
            VStack {
                topBar           // Skip button (top-trailing)
                TabView(selection: $page) { /* 6 IntroCard views */ }
                    .tabViewStyle(.page(indexDisplayMode: .never))
                pageDots         // custom dots (reuse PaneSlider pattern)
                bottomCTA        // Next / Get Started
            }
        }
    }
}
```

### Per-card content (`IntroCard` reusable struct)

Each card is a vertical composition:

- **Icon orb** (~120pt circle, tinted gradient background, SF Symbol
inside)
- **Headline** (28pt, semibold, rounded design, `roammateInk`)
- **Body** (17pt, `roammateMuted`, ~3 lines)
- **Inline visual flourish** (chip row / mini cards / 2x2 grid) where
it adds value


| #   | Theme          | Icon (SF Symbol)                      | Accent            | Headline                                          | Body                                                                                                                                                                                                 |
| --- | -------------- | ------------------------------------- | ----------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Welcome        | `airplane.circle.fill`                | `roammateIndigo`  | "Welcome to Roammate."                            | "The travel planner that travels with you. Swipe to see how."                                                                                                                                        |
| 2   | Brainstorm     | `sparkles.rectangle.stack.fill`       | `roammateViolet`  | "From a thought to a plan."                       | "Tell our AI what you're craving. It turns loose ideas into a real list of places — with photos, ratings, and addresses ready to schedule."                                                          |
| 3   | Group + Voting | `person.3.fill`                       | `roammateRose`    | "Everyone has a voice. One person owns the plan." | "Invite friends as Admin, Editor, Voter, or Viewer. Vote ideas up. The plan reflects the group — not the loudest chat message." (Inline: 4 role chips)                                               |
| 4   | Plan Mode      | `square.grid.3x1.below.line.grid.1x2` | `roammateEmerald` | "Timeline. Map. Ideas. One canvas."               | "Drag an idea onto a day. Watch the route appear. Switch days with one tap. Conflicts flag themselves." (Inline: 3 tiny stacked cards)                                                               |
| 5   | Concierge ⭐    | `wand.and.sparkles`                   | `roammateAmber`   | "Plans change. So does your day."                 | "Running late by 45 minutes? Tap once. Roammate reflows the day, finds a coffee near you, and pings the group. Your co-pilot during the trip — not just before it." (Inline: 3-step mini storyboard) |
| 6   | Personas + CTA | `person.crop.circle.badge.checkmark`  | `roammateFuchsia` | "AI that knows your style."                       | "Foodie? Slow traveler? Cultural deep-diver? Pick a persona — the AI tailors every suggestion to you. You can change it anytime."                                                                    |


Card 6 also surfaces the **primary CTA** at the bottom: `Get started`
(RoammatePrimaryButtonStyle) — calls `onFinish()` to mark seen and
reveal `LoginView`.

### Controls

- **Skip** button (top-trailing): visible on cards 1-5, hidden on card 6
(replaced by "Get started"). Tapping calls `onFinish()` immediately.
Style: plain text, `roammateMuted`, 15pt.
- **Page dots**: 6 dots, active = `roammateIndigo` filled capsule,
inactive = `roammateMuted.opacity(0.3)` circle. Reuse styling pattern
from `Theme/PaneSlider.swift`.
- **Next** button (bottom): visible on cards 1-5,
`RoammateSecondaryButtonStyle` capsule. Advances `page` with
`withAnimation(.spring(response: 0.35, dampingFraction: 0.85))`.
- **Get started** button (bottom, card 6 only):
`RoammatePrimaryButtonStyle`, full-width capsule.
- **Swipe** between cards: native TabView paging. `HapticManager.light()`
on page change.

### Background gradients (per card)

Subtle linear gradient from white → accent.opacity(0.08), full-bleed.
Card-specific accent tints lend a distinct feel to each page without
clobbering the content.

### Visual tokens (all already in `RoammateTheme.swift`)

- Colors: `roammateIndigo`, `roammateViolet`, `roammateRose`,
`roammateEmerald`, `roammateAmber`, `roammateFuchsia`,
`roammateInk`, `roammateMuted`, `roammateSurface`,
`roammateBackground`.
- Spacing: `RoammateSpacing.lg` / `.xl` / `.xxl` between elements.
- Radius: `RoammateRadius.card` for inline previews,
`RoammateRadius.pill` for chips.
- Shadow: `RoammateShadow.indigoGlow` on the icon orb.
- Buttons: `RoammatePrimaryButtonStyle`, `RoammateSecondaryButtonStyle`.

### Accessibility

- Each card sets `accessibilityElement(children: .combine)` with a
combined label "Card N of 6: . ".
- VoiceOver users hear page changes via `accessibilityValue("Page \(page+1) of 6")`.
- If `UIAccessibility.isReduceMotionEnabled` is true: replace the
spring transition with a crossfade.
- Dynamic Type supported via `.font(.system(..., design: .rounded))`.
- Color contrast meets WCAG AA against the gradient backgrounds.

## 2.5 Critical files

- `ios/Roammate/App/IntroCardsFlag.swift` *(new)* — UserDefaults
wrapper, modeled on `Subscription/PlusOnboardingFlag.swift`.
- `ios/Roammate/Views/Onboarding/IntroCardsView.swift` *(new)* — the
full-screen swipeable cards container + 6 `IntroCard` instances.
- `ios/Roammate/Views/ContentView.swift` — add the
`IntroCardsFlag.hasSeen()` branch between unauthenticated and
`LoginView` (3-way switch).
- `ios/Roammate/Theme/PaneSlider.swift` — reference only for the page
dots styling; do not modify (it's used elsewhere).

---

## 3. Out of scope

- Changing the iOS persona onboarding sheet (already correctly fires
post-login on first sign-in — unchanged).
- Tutorial spotlight tour (planned separately in [33], post-login).
- App Store listing copy / screenshots — handled by ASO doc, not here.
- Web app dashboard / authenticated surfaces — unchanged.
- A/B testing infrastructure for landing variants — full replacement
per decision; future plans can A/B from a `/v2` route if needed.
- Marketing analytics events (e.g. CTA click tracking) — if a basic
analytics layer exists, wire CTAs to it; otherwise defer.

---

## 4. Verification

### Web landing

1. `cd frontend && pnpm dev`. Visit `http://localhost:3000/`.
2. Verify the hero renders with the Plan Mode mockup; scroll through
  all 12 sections in order; section anchors (`#plan-mode`) jump
   correctly.
3. CTAs:
  - "Start free" / "Join Free" → `/login?signup=true`
  - "See Plus" → `/pricing`
  - "See it in action" → smooth-scrolls to `#plan-mode`
4. Resize browser: verify layouts at **320px**, 768px (tablet),
  1280px (desktop). The Plan Mode mockup stacks below copy on mobile;
   the Concierge storyboard becomes vertical.
5. Toggle macOS "Reduce Motion" preference and reload — confirm GSAP
  reveals fall back to plain visibility.
6. Visit `/` while logged in — navbar should show Dashboard / Planner,
  landing content still renders (no auth redirect on `/`).
7. `pnpm vitest run` — confirm no existing tests break (none target
  the landing page directly).
8. `pnpm build` — verify Lighthouse-friendly markup (no console errors,
  semantic headings).

### iOS intro cards

1. Open `ios/Roammate.xcodeproj` in Xcode. Build and run on simulator.
2. **First-launch path**: delete the app from the simulator (`xcrun
  simctl uninstall booted com.roammate.app`), build & run.
  - Intro cards should appear immediately (before LoginView).
  - Swipe through all 6; verify haptic feedback and dot updates.
  - Tap "Skip" mid-flow on any card 1-5 → LoginView appears.
  - Re-delete, reinstall: tap "Get started" on card 6 → LoginView
  appears.
3. **No-reshow path**: after dismissing once, kill the app and
  relaunch. LoginView appears immediately, no cards.
4. **Logout doesn't reset**: sign in, sign out, relaunch.
  LoginView appears immediately, no cards (proves `IntroCardsFlag`
   isn't keyed on user_id and isn't cleared on logout).
5. **Reduce Motion**: enable in Simulator
  (Settings → Accessibility → Motion → Reduce Motion). Verify
   page-change animation falls back to crossfade.
6. **VoiceOver**: enable in Simulator. Swipe through cards — each card
  should announce "Card N of 6: ".
7. **Dark mode**: switch simulator to dark mode — gradients/colors
  should still pass contrast (gradients are white → accent.opacity, so
   verify white isn't hard-coded; use `roammateSurface` /
   `roammateBackground` tokens that auto-adapt).
8. Inspect UserDefaults via Xcode Devices window or
  `xcrun simctl get_app_container booted com.roammate.app data` → look
   for `intro_cards_seen_v1 = true` after first dismissal.
9. If Swift unit tests exist (none currently), add a smoke test for
  `IntroCardsFlag.hasSeen/markSeen` round-trip.

---

## 5. Risks & open items

- **App Store badge** on web landing iOS section is currently a
placeholder; replace with the real App Store link once the iOS app is
approved (tracked in [25] production launch sequence).
- **No real product screenshots** are used; the HTML/CSS mockups need
to be visually credible. If they read as too abstract during
internal review, swap in real screenshots — but that means populating
`frontend/public/` with images and a maintenance burden when the UI
changes.
- **Intro cards copy** intentionally avoids over-pitching AI as a
category (per sales pitch positioning guardrails). Review tone with
marketing before merge.
- The new `Pricing` link in the navbar pushes the unauthenticated nav
to four items on mobile — confirm hamburger menu still renders
cleanly.

