# iOS Intro Cards Redesign — Web Parity

## Context

The web landing page was redesigned (RM-035/036, `docs/[34]`) and now looks polished: per-section eyebrow badges, heavy tracking-tight headlines with a colored accent phrase, rich split-layout mockups (chat threads, the Idea Bin card, a Timeline+Map+Idea-Bin canvas), a dramatic dark Concierge section, a fuchsia Personas section, a Free-vs-Plus pricing teaser using the brand gradient, and a full-indigo "Ready to Roam" finale.

The iOS onboarding intro cards (`ios/Roammate/Views/Onboarding/IntroCardsView.swift`) are still the basic version: a centered icon orb + headline + body + a tiny flourish. They feel shabby next to the web. This plan rebuilds them to reach visual/UX parity with the web while staying native SwiftUI and reusing the existing design system.

**Outcome:** an 8-card swipeable onboarding carousel — Welcome → Brainstorm → Idea Bin → Plan Mode → Concierge → Personas → Roammate Plus → Ready to Roam — each with a web-matched eyebrow, punchy headline, body copy, and a high-fidelity mini-mockup; with per-card backgrounds (dark Concierge, indigo finale), staggered entrance animation, and full a11y support.

## Design system (reused, do not reinvent)

All tokens already exist in `ios/Roammate/Theme/RoammateTheme.swift`:
- Colors: `.roammateIndigo/IndigoDark/IndigoTint`, `.roammateInk` (#0F172A = slate-900, used as the dark Concierge bg), `.roammateMuted`, `.roammateViolet/VioletTint`, `.roammateFuchsia/FuchsiaTint`, `.roammateAmber/AmberTint`, `.roammateYellow`, `.roammatePurple`, category color/tint API `Color.categoryColor(_)/categoryTint(_)/categoryIcon(_)`.
- `RoammateGradient.plus` (indigo→fuchsia→amber) — legitimately allowed on the Plus card (it is a Plus surface).
- `RoammateSpacing`, `RoammateRadius`, `RoammateShadow.card`, `RoammatePrimaryButtonStyle`, `RoammateSecondaryButtonStyle`, `PillLabel` (`Theme/ViewModifiers.swift`), `PlusCrestView` (`Views/Paywall/PlusCrestView.swift`), `HapticManager.light()`.

**Two small token additions** in `RoammateTheme.swift`:
- `roammateRose` (#F43F5E) + `roammateRoseTint` (#FFF1F2) — Idea Bin accent (web uses rose-500; reuse the existing danger hex but expose a semantic name so it's not "danger" on a feature card).
- `roammateIndigo300` (#A5B4FC) + `roammateIndigo200` (#C7D2FE) — lighter indigo for accent phrases on dark/indigo backgrounds (Concierge "your day", Ready-to-Roam "Roam?").

## File structure

Replace the single-file view with a small set under `Views/Onboarding/`:

1. **`IntroCardsView.swift`** (rewrite) — the carousel shell: `TabView(.page)`, animated full-bleed background driven by the current card, adaptive top bar (Skip), adaptive page dots, adaptive bottom CTA, haptics, finish/advance, `onFinish` callback (unchanged contract — `ContentView` gating and `IntroCardsFlag` stay as-is).
2. **`IntroCardScaffold.swift`** (new) — the card data model + the stacked card layout (eyebrow pill → headline → body → mockup slot), plus a `Background` enum (`.lightTint(accent)`, `.dark`, `.indigo`) that resolves headline/body/eyebrow/chrome colors per card.
3. **`IntroMockups.swift`** (new) — the 8 presentational mini-mockups and their small shared subviews (`IntroChatBubble` light+dark, `IntroIdeaCard`, `IntroPlanCanvas`, `IntroPersonaAnswer`, `IntroPlusTeaser`). All hardcoded copy/data — no live stores, mirroring the web's static mockups.

## Card model

```swift
struct IntroCardSpec {
    let eyebrow: String?          // e.g. "BRAINSTORM" — nil on Welcome/Ready
    let eyebrowIcon: String?      // SF Symbol, e.g. "sparkles"
    let accent: Color             // section accent
    let accentTint: Color         // eyebrow pill bg (light cards)
    let headlineLead: String      // ink/white part
    let headlineAccent: String    // accent-colored part (rendered Text(lead)+Text(accent))
    let body: String
    let background: Background     // .lightTint(accent) | .dark | .indigo
    let mockup: Mockup            // enum -> view in IntroMockups
}
```

Headline render: `Text(lead) + Text(accent).foregroundStyle(accentForBackground)`, font `.system(size: 30, weight: .black)` with `.tracking(-0.5)` (default design, not rounded) to match the web's punchy type. Welcome & Ready-to-Roam use size ~40. Body stays friendly: `.system(size: 16, design: .rounded)` in muted (or white-opacity on dark/indigo). Eyebrow: `.system(size: 12, weight: .bold)`, `.tracking(1.5)`, uppercased, in a capsule (accentTint bg / accent text; translucent-white on dark/indigo).

## The 8 cards (verbatim web copy)

| # | Card | Eyebrow / icon | Accent | Background | Headline (lead / **accent**) |
|---|------|----------------|--------|-----------|------------------------------|
| 1 | Welcome | — (R logo mark) | indigo | light tint | "The travel planner that **travels with you.**" |
| 2 | Brainstorm | BRAINSTORM / `sparkles` | violet | light tint | "Turn loose ideas into **a real plan.**" |
| 3 | Idea Bin | IDEA BIN + VOTING | rose | light tint | "Group input without **group chat chaos.**" |
| 4 | Plan Mode | PLAN MODE / `square.stack.3d.up` | indigo | light tint | "Timeline. Map. Ideas. **One canvas.**" |
| 5 | Concierge | CONCIERGE / `wand.and.sparkles` | indigo300 | **dark** (`.roammateInk`) | "Plans change. So does **your day.**" |
| 6 | Personas | PERSONAS / `sparkles` | fuchsia | light tint | "AI that knows **your style.**" |
| 7 | Roammate Plus | ROAMMATE PLUS | indigo | light tint | "Free to start. **Plus when you outgrow it.**" |
| 8 | Ready to Roam | — | white-on-indigo | **indigo** | "Ready to **Roam?**" (accent italic, indigo200) |

Body copy (verbatim from web):
- **Welcome:** "Most apps stop the moment you board the plane. Roammate keeps working — re-routing your day, finding a coffee shop near your next stop, and re-balancing the group's plan in real time."
- **Brainstorm:** "Tell our AI what you're craving. It comes back with real places — already enriched with locations, opening hours, and everything you need to drop them into your day."
- **Idea Bin:** "Everyone's ideas land in one shared bin. Vote them up — or down. The plan reflects the group, not the loudest voice on WhatsApp."
- **Plan Mode:** "Drag an idea onto a day. Pick a time. The route emerges on the map. That's it."
- **Concierge:** "Running late by 45 minutes? Tap once. Roammate reflows the day, finds a coffee near you, and pings the group. Your co-pilot during the trip — not just before it."
- **Personas:** "Foodie, cultural deep-diver, slow traveler — pick a persona and every suggestion tilts to match. Same prompt, different answer."
- **Plus:** "Every core feature works for free. Plus removes the limits."
- **Ready to Roam:** (no body; large headline + CTA only)

## The mockups (high-fidelity, in `IntroMockups.swift`)

Each mockup sits in a white rounded container (`RoammateRadius.card`, `RoammateShadow.card`, 1px `roammateBorder`) except where noted. Built static; reuse existing visual patterns.

1. **Welcome** — branded hero: the Roammate "R" logo tile (indigo rounded-rect with white "R", like the web navbar) above a soft stack of 3 floating mini-panels (Timeline / Map / Ideas) hinting at Plan Mode. Subtle.
2. **Brainstorm** — chat thread: user bubble "3 days in Lisbon, foodie vibe, no museums" (right, slate-100), then an AI reply card (violet-tinted, `roammateVioletTint`) titled "✨ Here's a starting list" with 3 rows (Time Out Market / Pastéis de Belém / Tasca da Esquina) and a small "Add all to Idea Bin" pill. Bubble styling mirrors `Views/Chat/ChatMessageBubble.swift`.
3. **Idea Bin** — recreate image #9 exactly as a static `IntroIdeaCard`: purple category bar (left, 4px), title "Rock Bar, AYANA Resort", "Nightlife" pill (`categoryTint/Color("nightlife")` → purple), clock chip "6:00 PM – 7:00 PM" + pencil, thumbs-up/down counts, trash glyph. Stack one or two more (Time Out Market — Food/amber — 👍5; Belém Tower — Landmarks/yellow — 👍4) to show the shared bin + votes. Reuses `CategoryColorBar`, `PillLabel`, thumbs pattern from `Views/Trips/Plan/TimelineRow.swift`.
4. **Plan Mode** — mini canvas: a day-chip row ("Day 1" active = indigo pill, "Day 2"/"Day 3" muted), a small map tile (subtle gradient + grid) with an animated indigo polyline route and numbered pins (1/2/3), and 2–3 timeline rows (category bar + name + time chip). Compact, stacked for phone width.
5. **Concierge** (dark) — a 3-step storyboard row (`Clock` "Running late +45m" → `wand.and.sparkles` "Day reflows" → `bell.fill` "Group pinged") over a dark chat preview using a **dark `IntroChatBubble` variant** (user = white/10, AI = indigo/20 with indigo-100 text): "We're running 45 minutes late at lunch." → "Got it — pushed your 2pm to 2:45pm. Walking to Time Out Market is 8 min from here." → "Find a coffee place nearby?" → "Fábrica Coffee Roasters is 2 min away, 4.6★ — added between stops."
6. **Personas** — two stacked `IntroPersonaAnswer` cards: **Foodie** (amber chip + amber-tinted answer bubble: Tasca da Esquina / Pastelaria 1829 / Time Out Market) and **Cultural Deep-Diver** (fuchsia chip + fuchsia-tinted bubble: Jerónimos Monastery / Gulbenkian / Fado vadio in Alfama), each above the shared "3 days in Lisbon" prompt.
7. **Roammate Plus** — `IntroPlusTeaser`: a small Free card (white, 3 rows: "2 active trips", "15 AI brainstorms/mo", "Group voting & Plan Mode") next to/above a Plus card filled with `RoammateGradient.plus` (white text, 3 rows: ∞ "Unlimited trips & brainstorms", wand "Always-on AI Concierge", map.pin "Offline maps") topped by a small `PlusCrestView`.
8. **Ready to Roam** — no boxed mockup; the indigo card itself is the canvas. Large white "Ready to **Roam?**" headline (accent italic indigo200) + a `Compass` glyph; the bottom CTA carries the action.

## Carousel shell behavior (`IntroCardsView.swift`)

- Full-bleed background animates on page change (`.easeInOut(0.35)`): light cards = white→accent.opacity(0.08) gradient; Concierge = solid `roammateInk`; Ready = solid `roammateIndigo`.
- **Adaptive chrome:** Skip text, page dots, and CTA recolor for dark/indigo backgrounds (white Skip, white dots, and on the indigo finale a white-filled button with indigo text — matching the web's inverted CTA). Add a `whiteOnIndigo` button variant (or pass a tint param) for the last card.
- Page dots: active = wide capsule (indigo on light / white on dark+indigo), inactive = 0.3-opacity.
- Bottom CTA: non-last = "Next" (secondary; light variant on dark Concierge card); last = "Start Your First Trip" with `compass` icon (primary, white-on-indigo) → `finish()` → `onFinish()`.
- Skip top-right, hidden on last card, calls `finish()`.
- Per-card content wrapped in a `ScrollView` that vertically centers when it fits and scrolls on small devices (iPhone SE) so tall mockups never clip.

## Animation & a11y

- **Entrance:** when a card becomes active, stagger eyebrow → headline → body → mockup with a small offset+opacity (≈40ms apart). Mockup micro-motion: Plan Mode route draws in, Concierge bubbles appear in sequence, Plus crest shimmers (PlusCrestView already does this).
- **Reduce Motion:** gate every stagger/draw/shimmer on `@Environment(\.accessibilityReduceMotion)` — fall back to simple fades (pattern already in the current file at lines 100/163).
- **VoiceOver:** each card is one combined element labeled "Card N of 8. {headline}. {body}"; mockups `accessibilityHidden(true)` (decorative) or given a one-line label.
- **Dynamic Type:** headlines `fixedSize(vertical:)` + `minimumScaleFactor(0.8)`; verify at XL.
- **Contrast:** body on indigo/dark uses white (not muted); eyebrow pills keep ≥4.5:1.
- **Touch targets:** CTA full-width; Skip ≥44pt.

## Out of scope

- No change to `ContentView.swift` gating or `IntroCardsFlag` (`intro_cards_seen_v1`) — the `onFinish` contract is preserved.
- No new packages, fonts, or colors beyond the 4 token aliases above.
- Plus/Personas cards are illustrative only (pre-auth) — no navigation/paywall wiring.

## Verification

1. **Previews:** add `#Preview`s for `IntroCardsView` and each mockup in `IntroMockups.swift`; eyeball all 8 in Xcode canvas.
2. **Simulator (via `/run` or `xcodebuild` + `xcrun simctl`):** clear app data so `intro_cards_seen_v1` is unset, launch on an iPhone (and an iPhone SE for the small-screen scroll case). Walk all 8 cards: swipe + Next, confirm background animates light→dark (Concierge)→light→indigo (Ready), Skip works on cards 1–7 and is hidden on card 8, dots/CTA recolor correctly.
3. **Finish path:** tap "Start Your First Trip" → confirm `onFinish()` fires, `IntroCardsFlag.markSeen()` sets the flag, and the app transitions to `LoginView`; relaunch → intro does not reappear.
4. **A11y passes:** enable Reduce Motion (animations degrade to fades, nothing breaks), set Dynamic Type to XL (no clipping/overlap), run VoiceOver over a couple cards (labels read in order).
