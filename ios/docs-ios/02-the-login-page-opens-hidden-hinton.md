# Roammate iOS Frontend Plan

## Context

The iOS Swift client (services, stores, models) is complete and the app builds and logs in successfully against the local FastAPI backend. The current UI is throw-away scaffolding (a 2-tab `MainTabView` with a basic trip list / detail). This plan replaces it with a proper SwiftUI frontend that visually matches the web app and ships the screens the user described.

**What gets built in this pass:** a design-token foundation, a 5-tab floating pill navigation, a full Dashboard with the 3-state TodayWidget carousel, an AI chat drawer (large detent), Trips / Invitations / Groups / Profile tabs, a redesigned Trip Landing page, and stubs for the four Trip sub-pages (Plan, Brainstorm, Concierge, People).

**Locked design decisions (from user):**
- Color scheme: match web — indigo-600 primary, slate-900 ink, soft white/slate-50 surfaces
- Font: **SF Pro Rounded** (system, native, no bundling)
- Animations: SwiftUI native springs (`.smooth`, `.bouncy`) — smooth and idiomatic
- Bottom nav: **floating pill / island** (rounded capsule, blurred material, shadow)
- TodayWidget: **3-state swipe carousel** matching web (pre / in / post-trip)
- Trip list rows: **name + date range only** (no avatars, no thumbnails)
- AI chat drawer: **large detent (~85%)** with drag handle, swipe-down to dismiss
- Trip Landing 4 sections: **vertical list of cards** with icon + chevron
- Invitations tab: **trip invitations only** (no group invites here)
- Profile tab: **full settings menu** (edit profile, personas, notifications, password, delete account, about, logout)

---

## Design system to extract from web

Translation of the web tokens (audited at `frontend/app/globals.css`, `app/page.tsx`, `Toast.tsx`, `Navbar.tsx`) into SwiftUI primitives:

| Token | Web value | SwiftUI |
|---|---|---|
| Primary | `#4F46E5` (indigo-600) | `Color.roammateIndigo` |
| Primary dark | `#4338CA` (indigo-700) | `Color.roammateIndigoDark` |
| Primary tint | `#EDE9FE` (indigo-50) | `Color.roammateIndigoTint` |
| Ink | `#0F172A` (slate-900) | `Color.roammateInk` |
| Muted ink | `#64748B` (slate-500) | `Color.roammateMuted` |
| Surface | `#FFFFFF` | `Color.roammateSurface` |
| Background | `#F8FAFC` (slate-50) | `Color.roammateBackground` |
| Border | `#E2E8F0` (slate-200) | `Color.roammateBorder` |
| Success | `#10B981` (emerald-500) | `Color.roammateSuccess` |
| Danger | `#F43F5E` (rose-500) | `Color.roammateDanger` |
| Card radius | `rounded-[2.5rem]` (40 px) | `RoammateRadius.card = 32` |
| Button radius | `rounded-[1.5rem]` (24 px) | `RoammateRadius.button = 18` |
| Pill / nav | `rounded-full` | `Capsule()` |
| Card shadow | `shadow-xl shadow-indigo-900/5` | indigo-tinted shadow, `y: 8, radius: 24, opacity: 0.05` |
| Glass nav | `bg-white/90 backdrop-blur-xl` | `.background(.ultraThinMaterial)` |
| Headline weight | `font-black` (900) | `.font(.system(.largeTitle, design: .rounded, weight: .black))` |
| Body weight | `font-medium` (500) | `.font(.system(.body, design: .rounded, weight: .medium))` |

---

## Architecture

### File structure

**New files (24):**

```
ios/Roammate/
├── Theme/
│   ├── RoammateTheme.swift         # Colors, radii, shadows, spacing
│   ├── ViewModifiers.swift         # .roammateCard(), .pillBackground(), .hapticPress()
│   └── HapticManager.swift         # UIImpactFeedbackGenerator wrapper
├── Views/
│   ├── ContentView.swift           # (update) auth gate → MainShell or LoginView
│   ├── MainShell.swift             # NEW — replaces MainTabView; floating pill nav
│   ├── FloatingTabBar.swift        # NEW — custom 5-tab pill component
│   ├── Dashboard/
│   │   ├── DashboardView.swift     # NEW — widget + trip list + FAB
│   │   ├── TodayWidget.swift       # NEW — 3-state carousel (pre/in/post)
│   │   ├── TodayWidgetCards.swift  # NEW — PreTripCard, InTripCard, PostTripCard
│   │   └── ChatFAB.swift           # NEW — floating chat button
│   ├── Trips/
│   │   ├── TripsTabView.swift      # NEW — pure trip list (replaces TripListView)
│   │   ├── TripRow.swift           # NEW — name + date row with chevron
│   │   ├── CreateTripView.swift    # (keep, restyle)
│   │   ├── TripLandingView.swift   # NEW — replaces TripDetailView
│   │   ├── TravellersStrip.swift   # NEW — avatar row + invite button
│   │   ├── InviteSheet.swift       # NEW — email + role picker
│   │   └── SubPages/
│   │       ├── TripPlanView.swift       # blank stub
│   │       ├── TripBrainstormView.swift # blank stub
│   │       ├── TripConciergeView.swift  # blank stub
│   │       └── TripPeopleView.swift     # blank stub
│   ├── Invitations/
│   │   ├── InvitationsTabView.swift  # NEW — list of pending trip invites
│   │   └── InvitationRow.swift       # NEW — accept/decline inline
│   ├── Groups/
│   │   └── GroupsTabView.swift       # NEW — group list (basic for now)
│   ├── Profile/
│   │   ├── ProfileTabView.swift      # NEW — replaces ProfileView in MainTabView
│   │   ├── EditProfileView.swift     # NEW — name/city/timezone/currency/blurb
│   │   ├── PersonasView.swift        # NEW — pick travel personas
│   │   ├── ChangePasswordView.swift  # NEW — current + new password
│   │   └── AboutView.swift           # NEW — version, links
│   ├── Chat/
│   │   ├── AIChatDrawer.swift        # NEW — sheet content with .large detent
│   │   ├── ChatMessageBubble.swift   # NEW — user/assistant bubble rendering
│   │   └── QuickActionsBar.swift     # NEW — "My day", "What's next?", "Find nearby"
│   └── Auth/                         # (keep, restyle LoginView + RegisterView)
```

**Files to delete:**
- `Views/Main/MainTabView.swift` (replaced by `MainShell.swift`)
- `Views/Trips/TripListView.swift` (replaced by `Trips/TripsTabView.swift`)
- `Views/Trips/TripDetailView.swift` (replaced by `Trips/TripLandingView.swift`)
- The `Views/Main/` directory (no longer needed)

**Files to update:**
- `App/RoammateApp.swift` — register `NotificationStore` and `TripStore` as `@StateObject`s so they survive across tabs; apply global rounded font via `.font(.system(.body, design: .rounded))` on root
- `Views/ContentView.swift` — swap `MainTabView()` → `MainShell()`
- `Views/Auth/LoginView.swift` — restyle to match web (indigo button, rounded inputs, hero title)
- `Views/Auth/RegisterView.swift` — restyle to match
- `Views/Trips/CreateTripView.swift` — restyle, indigo CTA

After file changes: re-run `cd ios && xcodegen generate` since project.yml uses path-based source inclusion.

---

## Implementation details by screen

### 1. Theme foundation (`Theme/RoammateTheme.swift`)

Static namespaces for tokens. Color helpers as `extension Color`. Radius constants. Pre-built shadow modifiers. Pre-built `.roammateCard()`, `.roammatePillButton()`, `.glassBlur()` view modifiers. A `HapticManager` wrapper for `.light` / `.medium` / `.success` haptics fired on key taps (tab switch, accept/decline, send chat).

### 2. MainShell + FloatingTabBar

`MainShell.swift` is a `ZStack`:
- Bottom layer: `TabView` with `.tabViewStyle(.page(indexDisplayMode: .never))` so we get smooth swipe between tabs but hide the system tab bar via `.toolbar(.hidden, for: .tabBar)`.
- Top overlay: `FloatingTabBar` pinned to `.bottom` with `.padding(.horizontal, 20).padding(.bottom, 16)`.

`FloatingTabBar.swift`:
- 5 `Capsule()`-clipped items inside a parent `Capsule()` background filled with `.ultraThinMaterial` and a soft indigo-tinted shadow.
- SF Symbols: `house.fill`, `map.fill`, `envelope.fill`, `person.3.fill`, `person.crop.circle.fill`.
- Selected item: indigo background pill with white icon. Unselected: SF Symbol in slate-500.
- `matchedGeometryEffect` for the selection pill so it slides between tabs with a `.spring(response: 0.35, dampingFraction: 0.75)`.
- Light-haptic on selection change.

### 3. Dashboard (`Dashboard/DashboardView.swift`)

Layout (top → bottom):
- Scrollable `ScrollView`
- Hero greeting (e.g. "Hi, Aman" — pulled from `AuthManager.currentUser.name.split(.first)`)
- `TodayWidget` — square (aspect ratio 1:1), corner radius 32, card shadow, with three pages
- "My Trips" section header + horizontal "See all" link to Trips tab
- Trip rows (max 5 most recent, then "View all" link)
- Bottom padding equal to `FloatingTabBar.height + 16` so nothing is occluded
- `ChatFAB` overlaid in the bottom-right corner, above the tab bar, also offset to avoid the pill

`TodayWidget.swift`:
- Uses `TabView(selection:)` with `.tabViewStyle(.page)` for the swipe carousel
- Three child views: `PreTripCard`, `InTripCard`, `PostTripCard`
- Data sourced from `TripStore.trips` — pick the most relevant trip (current trip if today falls in range; else nearest upcoming; else most recent past)
- Page indicator dots styled in indigo
- Each card: indigo / amber / rose gradient background (per web), big trip name in `.title.bold()`, contextual content (countdown / day-of / recap)

`ChatFAB.swift`:
- Circle button, 60×60, indigo background, white `bubble.left.fill` icon, indigo-tinted shadow
- `.scaleEffect(isPressed ? 0.92 : 1.0)` with `.spring()` for press feedback
- On tap: medium haptic + sets a `@State var showChatSheet = true` in `DashboardView`
- `DashboardView` presents `AIChatDrawer` via `.sheet(isPresented:)` with `.presentationDetents([.large])` and `.presentationDragIndicator(.visible)` so the drag-handle shows and swipe-down dismisses

**No active trip case:** `ChatFAB` is still shown but tapping it presents a small inline message "Plan a trip first to chat with your concierge" — because every concierge endpoint requires `trip_id`.

### 4. Trips tab (`Trips/TripsTabView.swift`)

- Title: "My Trips" with a `+` button in toolbar to present `CreateTripView`
- `List` of `TripRow`s — name + date range + chevron, tap → push `TripLandingView`
- Pull-to-refresh on `TripStore.load()`
- Empty state when `store.trips.isEmpty`: SF Symbol `map`, "No trips yet", "Tap + to start planning"
- Uses the **shared** `TripStore` from `App` environment (so dashboard and this tab stay in sync)

### 5. Invitations tab (`Invitations/InvitationsTabView.swift`)

- Calls `TripStore.loadInvitations()` on appear and refresh
- Each `InvitationRow`: trip name, "Invited by {name}", role badge ("Admin" / "Viewer" / "Voter"), two buttons: `Accept` (indigo filled) and `Decline` (slate outlined)
- On Accept → `TripStore.acceptInvitation()`, row animates out, success haptic
- On Decline → confirmation alert → `TripStore.declineInvitation()`
- Empty state: SF Symbol `envelope.open`, "No pending invitations"

### 6. Groups tab (`Groups/GroupsTabView.swift`)

- Calls `GroupStore.load()` on appear
- Simple `List` of groups: name, member count + trip count badges, chevron
- Tap → no destination for now (placeholder push to a "Group detail" view we'll build later)
- `+` toolbar button → simple alert prompt to create a group (calls `GroupStore.create`)
- Empty state: SF Symbol `person.3`, "No groups yet"

### 7. Profile tab (`Profile/ProfileTabView.swift`)

Sectioned `List` (grouped):
1. **Header** (cell): big avatar circle with initials, name, email
2. **Account** section
   - "Edit Profile" → pushes `EditProfileView`
   - "Travel Personas" → pushes `PersonasView`
   - "Change Password" → pushes `ChangePasswordView`
3. **Notifications** section (stubbed UI — toggles backed by `UserDefaults` for now until backend prefs endpoint exists)
   - "Trip activity", "Invitations", "AI suggestions" toggles
4. **About** section
   - "App Version" → static cell showing `Bundle.main` version
   - "Privacy Policy" → opens roammate.app/privacy in `SFSafariViewController`
5. **Danger zone**
   - "Log Out" (slate text, role: `.destructive` on red)
   - "Delete Account" (red, confirmation alert → `AuthService.deleteAccount()`)

Each sub-screen:
- `EditProfileView`: Form with name, home city, timezone (picker), currency (picker), travel blurb (TextEditor). On save → `AuthService.updateMe()` → updates `AuthManager.currentUser`.
- `PersonasView`: Grid of persona chips from `/users/personas/catalog`, multi-select, save → `AuthService.updatePersonas()`.
- `ChangePasswordView`: Form with current password, new password, confirm. Calls `AuthService.updateMe(ProfileUpdate(password:..., currentPassword:...))`.

### 8. Trip Landing (`Trips/TripLandingView.swift`)

Layout top → bottom (all centered horizontally):
- Back button in toolbar
- Trip title — `.font(.system(.largeTitle, design: .rounded, weight: .black))`, centered
- Date range — `.font(.subheadline)`, slate-500, centered, below title
- `TravellersStrip` — overlapping avatar circles + "+ Invite" button (admin only) that presents `InviteSheet`
- 4 vertical cards (per the chosen layout):
  ```
  ┌──────────────────────────┐
  │ 📍  Plan              >  │
  ├──────────────────────────┤
  │ 💡  Brainstorm        >  │
  ├──────────────────────────┤
  │ 🤖  Concierge         >  │
  ├──────────────────────────┤
  │ 👥  People            >  │
  └──────────────────────────┘
  ```
  Each card: 72pt tall, `.roammateCard()` styling, SF Symbol icon (`mappin.and.ellipse`, `lightbulb`, `sparkle.magnifyingglass`, `person.2`), title, chevron. Tap → push the matching sub-page.

`InviteSheet`: small sheet with email field + role picker (Admin / Viewer / Voter), Send button → `TripDetailStore.invite()`.

### 9. Trip sub-pages (stubs)

`TripPlanView`, `TripBrainstormView`, `TripConciergeView`, `TripPeopleView` — each is a `NavigationStack`-friendly view that just renders the title in the navigation bar and shows `ContentUnavailableView("Coming soon", systemImage: "...")` in the body. Real implementations come in a later pass after the user reviews this design.

### 10. AI Chat Drawer (`Chat/AIChatDrawer.swift`)

- Presented as `.sheet` with `.presentationDetents([.large])`, `.presentationDragIndicator(.visible)`, and `.presentationBackgroundInteraction(.disabled)` (so the dashboard underneath is dimmed)
- Owns its own `@StateObject var store: ConciergeStore` initialized with the active trip's id (passed in from `DashboardView`)
- Layout:
  - Top: title "Concierge" + close button (also dismissible by drag-down)
  - Quick actions chip row: "My day", "What's next?", "Find nearby" — each triggers a corresponding `ConciergeStore` call and appends a message
  - Scrollable `ChatMessageBubble` list
  - Pending-confirmation bar (shown when `store.pendingResponse != nil`): "Confirm" / "Nevermind" buttons → `store.confirmPending()` / `store.cancelPending()`
  - Input bar pinned to bottom (above keyboard): rounded TextField + indigo send button
- Auto-scroll to bottom when new message lands, smooth-spring animation

---

## Critical files to reuse / depend on

- `Store/TripStore.swift` — feeds Dashboard widget, Trips tab, TripLanding
- `Store/TripDetailStore.swift` — feeds TripLanding (members, invite)
- `Store/ConciergeStore.swift` — feeds AIChatDrawer
- `Store/GroupStore.swift` — feeds Groups tab
- `Store/AuthManager.swift` — feeds Profile tab + auth gating
- `Store/NotificationStore.swift` — feeds future badge on Invitations / app-wide unread indicator (not implemented this pass)
- `Network/MemberService.getPendingInvitations / acceptInvitation / declineInvitation` — Invitations tab
- `Network/AuthService.updateMe / updatePersonas / deleteAccount` — Profile sub-screens

`TripStore`, `NotificationStore`, and `GroupStore` should be promoted to **app-level `@StateObject`s** in `RoammateApp.swift` and injected via `.environmentObject(...)` so the same instance is shared across tabs (avoids redundant fetches).

---

## Animation principles

- **Tab switch**: spring `.spring(response: 0.35, dampingFraction: 0.75)` on the matched-geometry selection pill
- **Card press**: `.scaleEffect(isPressed ? 0.97 : 1.0)` + light haptic
- **Chat send**: keyboard scroll-to-bottom with `.spring(.smooth)`
- **List item appear**: `.transition(.opacity.combined(with: .move(edge: .top)))` on Accept/Decline
- **TodayWidget swipe**: SwiftUI `TabView .page` style — already smooth by default
- **FAB press**: scale + indigo glow shadow expansion
- **Sheet present**: native `.large` detent transition (already perfect)

Everything uses native SwiftUI springs — no Lottie, no Framer Motion port, no custom Core Animation. Matches "smooth + good UX" intent without complexity.

---

## Implementation order

1. **Theme + utility layer** (1 batch): `RoammateTheme.swift`, `ViewModifiers.swift`, `HapticManager.swift` — unblocks everything else
2. **Shell** (1 batch): `MainShell.swift`, `FloatingTabBar.swift`, update `ContentView.swift`, delete old `MainTabView.swift`
3. **Dashboard** (1 batch): `DashboardView.swift`, `TodayWidget.swift`, `TodayWidgetCards.swift`, `ChatFAB.swift`
4. **Trips tab + Trip Landing + sub-page stubs** (1 batch): `TripsTabView.swift`, `TripRow.swift`, `TripLandingView.swift`, `TravellersStrip.swift`, `InviteSheet.swift`, 4 sub-page stubs, delete old `TripListView.swift`/`TripDetailView.swift`
5. **Invitations + Groups tabs** (1 batch): `InvitationsTabView.swift`, `InvitationRow.swift`, `GroupsTabView.swift`
6. **Profile tab + sub-screens** (1 batch): `ProfileTabView.swift`, `EditProfileView.swift`, `PersonasView.swift`, `ChangePasswordView.swift`, `AboutView.swift`
7. **AI Chat drawer** (1 batch): `AIChatDrawer.swift`, `ChatMessageBubble.swift`, `QuickActionsBar.swift`, wire into `DashboardView`
8. **Auth screens restyle** (1 batch): update `LoginView.swift`, `RegisterView.swift`, `CreateTripView.swift`
9. **Regenerate Xcode project**: `cd ios && xcodegen generate`

After each batch, run the simulator and confirm no regressions before moving to the next.

---

## Verification

End-to-end smoke test after all batches:

1. `cd ios && xcodegen generate && open Roammate.xcodeproj`
2. `cd /Users/aman.gupta1/roammate-app && docker compose up -d`
3. In Xcode: `⌘R` to run on iPhone 15 Pro simulator
4. **Login** with existing account → land on Dashboard with floating pill nav visible
5. **Dashboard**: TodayWidget renders correct state for your active trip; swipe between pages; trip list shows below; tap a row → push to Trip Landing
6. **Trip Landing**: title + dates centered, travellers strip visible, 4 cards tappable, each goes to a blank "Coming soon" stub
7. **Tap chat FAB** on Dashboard → drawer slides up to ~85%; type a message → response renders; swipe down → drawer dismisses, back on Dashboard
8. **Trips tab**: same trip list, `+` opens CreateTripView, create a trip → list refreshes
9. **Invitations tab**: shows any pending invitations or empty state; accept/decline works against the API
10. **Groups tab**: lists groups or empty state; `+` creates a group
11. **Profile tab**: header shows your data; tap Edit Profile, update name, save → reflects in header; Personas screen loads catalog and saves; Logout returns to LoginView and `DiskCache` is cleared

If everything above passes, the iOS frontend is complete and ready for the next round (real Trip sub-page content, MapKit integration, push notifications).
