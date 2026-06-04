# iOS Intro Cards — Polish, Interactivity & Airplane Transition

## Context

The 8-card iOS intro carousel was built in RM-035/036 (`docs/[34]`, `docs/[37]`). This plan covers the next layer of polish: layout fixes on 6 cards, interactive day-switching on Plan Mode, a background retheme of Concierge, and a dramatic "wow factor" airplane exit/enter animation when transitioning between the intro flow and the login page.

Web: only the Concierge section background changes (dark → light indigo) to stay in sync with iOS.

---

## Files Modified

| File | What changes |
|------|-------------|
| `ios/.../IntroCardScaffold.swift` | New `showLogoLockup`, `subtitle`, `showMockup` props on `IntroCardSpec`; subtitle rendering in scaffold |
| `ios/.../IntroCardsView.swift` | Updated card specs; `onAnimatedFinish` closure for airplane CTA |
| `ios/.../IntroMockups.swift` | All 8 mockups updated (see per-card sections below) |
| `ios/.../ContentView.swift` | ZStack-based transition engine + airplane overlay |
| `frontend/app/page.tsx` | Concierge section `bg-slate-900` → `bg-indigo-50` + text color fixes |

---

## Scaffold Changes (`IntroCardScaffold.swift`)

Add three optional fields to `IntroCardSpec`:

```swift
var showLogoLockup: Bool = false   // shows icon + "Roammate" above headline
var subtitle: String? = nil        // rendered below headline, above mockup
var showMockup: Bool = true        // when false, skips IntroMockupView entirely
```

In `IntroCardView.body`, the render order becomes:

1. **Logo lockup** (when `showLogoLockup`) — `HStack { airplane.circle.fill icon (44pt, .roammateIndigo) + "Roammate" text (.largeTitle, .black, .rounded) }` centered, replaces eyebrow pill.
2. **Eyebrow pill** (when `eyebrow != nil && !showLogoLockup`)
3. **Headline** (existing)
4. **Subtitle** (when `subtitle != nil`) — `.body .rounded`, `.roammateMuted`, reveal order 2
5. **Body copy** (when `body != nil`) — reveal order 3
6. **Mockup** (when `showMockup`) — reveal order 4

---

## Card-by-Card Changes

### Card 1 — Welcome
**Remove:** body text, the 3-column teaser table.  
**Add:** logo lockup above headline (icon + "Roammate" on one line).

Spec delta:
```swift
// remove: body, headlineSize: 34 → keep 36
// add:
showLogoLockup: true,
showMockup: false,
headlineSize: 36,
centered: true
```

`WelcomeMockup` → returns `EmptyView()`.

---

### Card 2 — Brainstorm
**Body:** shorten to `"Tell our AI what you're craving. It comes back with real places."`  
**Headline size:** `36` (up from 30).  
**Mockup:** replace single exchange with 2 full exchanges, matching Image #3:

| Turn | Content |
|------|---------|
| User | "3 days in Lisbon, foodie vibe, no museums" |
| AI | "Here's a starting list" + Time Out Market / Pastéis de Belém / Tasca da Esquina + "Add all to Idea Bin" chip |
| User | "Skip the markets — add something for nightlife" |
| AI | "Got it — swapped them out" + Tasca Bela (late-night Fado) / Park Bar (rooftop sundowners) / Pensão Amor (cocktails) |

Both AI reply blocks reuse the existing `VStack` + `PlaceLine` pattern. Wrap both exchanges in a `ScrollView(.vertical, showsIndicators: false)` inside `mockupCard()` so tall content doesn't overflow on small phones.

---

### Card 3 — Idea Bin
**Theme:** rose/red → indigo.

Spec delta:
```swift
accent: .roammateIndigo,
accentTint: .roammateIndigoTint,
background: .lightTint(.roammateIndigo)
```

`IdeaBinMockup` changes:
- Remove `showTrash: true` from Rock Bar item (all three items → `showTrash: false`).
- Add `time` to items 2 and 3:
  - Time Out Market → `time: "11:00 AM – 12:00 PM"`
  - Belém Tower → `time: "2:00 PM – 3:00 PM"`
- In `IntroIdeaCard`: when `time == nil`, still render the time row at `opacity(0)` so all three cards share the same height and layout is consistent.

---

### Card 4 — Plan Mode
**Layout flip:** map moves to top, drawer below. Add interactive day switching.

New `PlanModeMockup` structure (replaces existing VStack):

```
ZStack (card shell, no mockupCard() wrapper — builds its own shell)
  VStack(spacing: 0)
    // Map — top half
    ZStack
      gradient (indigo tint → emerald tint)
      RouteShape (animated, resets on day change)
      numbered pins
    .frame(height: 160)
    .clipShape(top-corners-only RoundedRectangle, radius 20)

    // Drawer — white sheet below
    VStack(alignment: .leading, spacing: 10)
      Text("Try it yourself")
        .font(.caption2 .bold .rounded)
        .foregroundStyle(.roammateMuted)
        .padding(.bottom, 2)
      HStack(spacing: 8) { day chips (Day 1 · Thu, Day 2, Day 3) }
      ForEach(dayItems[selectedDay]) { timelineRow(...) }
    .padding(14)
    .background(Color.roammateSurface)
    .clipShape(bottom-corners-only RoundedRectangle, radius 20)
  .overlay(RoundedRectangle full stroke .roammateBorder)
  .shadow(RoammateShadow.card)
```

State:
```swift
@State private var selectedDay: Int = 0
@State private var routeProgress: CGFloat = 0
```

On day chip tap: `withAnimation(.spring(response: 0.4)) { selectedDay = idx; routeProgress = 0 }` then re-trigger route animation.

Day data (Lisbon):

| Day | Item 1 | Item 2 |
|-----|--------|--------|
| Day 1 · Thu | Pastéis de Belém — 09:00 (Food) | Jerónimos Monastery — 11:30 (Landmarks) |
| Day 2 | Belém Tower — 10:00 (Landmarks) | LX Factory — 14:00 (Shopping) |
| Day 3 | Alfama Walk — 10:30 (Culture) | Fado Show — 20:00 (Entertainment) |

Each day also has its own `[CGPoint]` pin positions for the map route.

---

### Card 5 — Concierge
**Background:** `.dark` (slate-900) → `.lightTint(.roammateIndigo)`.  
**Title size:** `36` (up from default 30).  
**Remove** `body` text entirely.  
**Add** `subtitle: "Your co-pilot during the trip."`.

`ConciergeMockup` adapts to light background:
- Remove `dark: true` from all `IntroChatBubble` calls.
- Step chip container fill: `Color.roammateIndigo.opacity(0.12)` → `Color.roammateIndigoTint`.
- Chat container fill: `Color.white.opacity(0.05)` → `Color.roammateBackground`.

**Web (`frontend/app/page.tsx`):**
- Section outer class: `bg-slate-900` → `bg-indigo-50`
- All `text-white` in section → `text-slate-900`
- All `text-white/70` → `text-slate-500`
- Badge: `bg-indigo-500/20 text-indigo-300` → `bg-indigo-100 text-indigo-600`
- Feature cards: `bg-white/5 border-white/10` → `bg-white border-slate-200`

---

### Card 6 — Roammate Plus
**Remove** `PlusCrestView(size: 36)` and its `Spacer()` from the Plus card's header `HStack`. The `HStack` becomes just `Text("PLUS")`.

Both Free and Plus cards already share `padding(16)` and `spacing: 10` — removing the crest makes the header lines equal height and the two tables visually consistent.

---

### Card 7 — Ready to Roam
**Remove:** `ReadyMockup` (circle + compass icon).  
**Headline:** scale up dramatically.

Spec delta:
```swift
showMockup: false,
headlineSize: 64,
centered: true,
accentItalic: true  // "Roam?" rendered italic
```

Full screen is just the large two-line centered headline at 64pt black. No icon, no body.

CTA: `IntroCardsView.bottomCTA` — the "Start Your First Trip" button calls `onAnimatedFinish()` (new closure from `ContentView`) instead of `finish()` directly.

---

## Airplane Transition Animation (`ContentView.swift`)

### State

```swift
@State private var introSeen: Bool = IntroCardsFlag.hasSeen()
@State private var transitionState: TransitionState = .idle
@State private var foregroundSlideY: CGFloat = 0
@State private var airplaneY: CGFloat = -80
@State private var airplaneVisible: Bool = false

enum TransitionState { case idle, introExiting, loginExiting }
```

### ZStack layout (bottom → top)

```
GeometryReader { geo in
  ZStack {
    // 1. Login — always present as background
    LoginView(onReplayIntro: triggerAirplaneEnter)
      .offset(y: loginBackgroundOffset(geo))  // slides from -geo.height to 0 during introExiting

    // 2. Intro cards — present when needed
    if !introSeen || transitionState == .loginExiting {
      IntroCardsView(
        onFinish: { /* not used during animation */ },
        onAnimatedFinish: triggerAirplaneExit
      )
      .offset(y: transitionState == .introExiting ? foregroundSlideY : 0)
    }

    // 3. Airplane overlay
    if airplaneVisible {
      airplaneView(geo: geo)
    }
  }
}
```

### Exit sequence — Intro → Login (`triggerAirplaneExit`)

```swift
func triggerAirplaneExit(geo: GeometryProxy) {
  transitionState = .introExiting   // login appears behind immediately
  airplaneY = -80
  airplaneVisible = true

  // Phase 1: airplane swoops into view (0.35s)
  withAnimation(.easeOut(duration: 0.35)) {
    airplaneY = geo.size.height * 0.3
  }

  // Phase 2: airplane + card fly out together (1.4s, starts at 0.25s)
  DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
    withAnimation(.easeIn(duration: 1.4)) {
      airplaneY = geo.size.height + 100
      foregroundSlideY = geo.size.height + 80
    }
  }

  // Completion: clean up (1.7s total)
  DispatchQueue.main.asyncAfter(deadline: .now() + 1.7) {
    HapticManager.light()
    IntroCardsFlag.markSeen()
    introSeen = true
    transitionState = .idle
    foregroundSlideY = 0
    airplaneVisible = false
    airplaneY = -80
  }
}
```

Login background offset: during `introExiting`, login starts at `-geo.size.height` and animates to `0` over 1.4s with the same timing, creating the "appearing from behind" effect.

### Enter sequence — Login → Intro (`triggerAirplaneEnter`)

Mirror of the above:
- `transitionState = .loginExiting`
- `introSeen = false` (intro cards appear in ZStack behind login)
- Login is the foreground (slides down via `foregroundSlideY`)
- Intro cards are the background (already at offset 0)
- Same airplane fly-down, same timing
- On completion: `transitionState = .idle`, `foregroundSlideY = 0`

### Airplane view

```swift
private func airplaneView(geo: GeometryProxy) -> some View {
  Image(systemName: "airplane.fill")
    .font(.system(size: 52, weight: .bold))
    .foregroundStyle(Color.roammateIndigo)
    .rotationEffect(.degrees(90))  // nose pointing down
    .shadow(color: Color.roammateIndigo.opacity(0.45), radius: 16, y: 8)
    .position(x: geo.size.width / 2, y: airplaneY)
    .animation(.easeIn(duration: 1.4), value: airplaneY)
}
```

`accessibilityReduceMotion`: when enabled, skip the animation entirely — call `finish()` / `onReplayIntro()` directly without showing the airplane.

---

## Verification Checklist

- [ ] All 8 cards render correctly on iPhone 15 Pro and iPhone SE
- [ ] Card 1: logo + name on one line above headline; no body, no table
- [ ] Card 2: 2-exchange chat visible, headline noticeably larger
- [ ] Card 3: indigo theme throughout; no trash icons; all 3 items have time + consistent height
- [ ] Card 4: map on top, drawer below; tapping Day 2 / Day 3 updates items + redraws route
- [ ] Card 5: light indigo background; readable mockup chat; subtitle line present
- [ ] Card 6: no crest; Free and Plus layout visually equal
- [ ] Card 7: full-screen 64pt headline only; no icon
- [ ] "Start Your First Trip" → airplane flies top-to-bottom, card follows, login appears behind (~2s)
- [ ] "See What's Inside" → same airplane animation, login flies away, intro appears behind
- [ ] `accessibilityReduceMotion` skips airplane entirely, transitions directly
- [ ] Web: Concierge section is light indigo; all text readable on light background
