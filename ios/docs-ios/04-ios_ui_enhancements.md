---
name: iOS UI Enhancements
overview: Comprehensive 12-point UI/UX overhaul of the Roammate iOS app covering Plan Trip drawer, Trip Landing Page, tab bar visibility, navigation menu, day tabs, Idea Bin voting, Brainstorm chat, notifications, dashboard widget, manual trip creation, and profile sub-page navigation.
todos:
  - id: e1-plan-trip-drawer
    content: "Enhancement 1: Redesign PlanTripDrawer with chat UI, phased layout (idle/planning/previewing), and re-prompt flow"
    status: completed
  - id: e2-trip-landing
    content: "Enhancement 2: Revamp TripLandingView with dark indigo background, centered hero, start-date-only, inline invite popup"
    status: completed
  - id: e3-hide-tab-bar-trips
    content: "Enhancement 3: Hide FloatingTabBar on Trip sub-pages (Plan, Brainstorm, Concierge, People) using environment key"
    status: completed
  - id: e4-overlay-dropdown-menu
    content: "Enhancement 4: Replace SideDrawer with overlay dropdown menu on TripSubPagesHost"
    status: completed
  - id: e5-day-tabs-redesign
    content: "Enhancement 5: Revamp DayTabsBar with arrows, Add Day button, remove Overview, solid white drawer"
    status: completed
  - id: e6-idea-bin-cards
    content: "Enhancement 6: Redesign IdeaRow with thumbs voting, delete, category-colored pin, expand/collapse details"
    status: completed
  - id: e7-brainstorm-chat
    content: "Enhancement 7: Revamp BrainstormChatView with empty state, background, timestamps, better extract button"
    status: completed
  - id: e8-brainstorm-bin
    content: "Enhancement 8: Restyle BrainstormBinView cards to match Idea Bin style with expand/collapse (no voting)"
    status: completed
  - id: e9-notifications-bell
    content: "Enhancement 9: Add notifications bell to Dashboard with overlay dropdown showing notification list"
    status: completed
  - id: e10-dashboard-widget
    content: "Enhancement 10: Enhance TodayWidget cards with richer content, CTAs, and better sizing"
    status: completed
  - id: e11-manual-trip-fix
    content: "Enhancement 11: Remove end date from CreateTripView, fix server error, redesign UI"
    status: completed
  - id: e12-profile-tab-bar
    content: "Enhancement 12: Hide FloatingTabBar on Profile sub-pages with animated return"
    status: completed
isProject: false
---

# iOS App UI/UX Enhancement Plan

## Enhancement 1: Plan Trip AI Drawer Redesign

**Current state:** [PlanTripDrawer.swift](ios/Roammate/Views/Chat/PlanTripDrawer.swift) has a three-phase flow (idle -> planning -> previewing) but lays everything out in a form-like structure with no chat paradigm. [PlanTripStore.swift](ios/Roammate/Store/PlanTripStore.swift) manages the state machine.

**Changes:**

- **Header**: Center "Plan a new trip" as a centered title at the top of the drawer. Move the close (X) button to the top-right corner.
- **Chat section (idle state)**: Replace the current `promptForm` with a chat-like layout. The center of the empty chat area shows a faded background text "AI turns your prompts into crafted trips". The chat input (single-line TextField + circular send button) is pinned at the bottom, directly above the "Plan" CTA button.
- **Chat section (planning state)**: When the user taps Send:
  - Immediately remove the background placeholder text.
  - Show the user's message as a right-aligned chat bubble at the top of the chat section.
  - Below the user bubble (above the chat input), show the "Planning Your Trip" banner with the witty phrases rotating every 3 seconds (update the current `1.8s` timer to `3s`).
  - The bottom "Plan" button text changes to "Planning..." and is disabled.
- **Chat section (previewing state)**: When result arrives:
  - The "Planning Your Trip" banner area is replaced with a summary card (trip name, number of days, number of brainstorm items).
  - The bottom button becomes a wide "Create Trip" button (80% width) with a small circular send button on the right (20%) for re-prompting.
- **Re-prompt flow**: If the user types in the chatbox and taps the circular send button, the new prompt appears as a second chat bubble below the first, the summary card is replaced with the "Planning Your Trip" banner again, and the cycle repeats.
- **Create Trip**: On tap, creates the trip and navigates to the Trip Landing Page.
- Store the conversation history as a `@Published var messages: [(role: String, text: String)]` array in `PlanTripStore`.

**Files to modify:**
- [PlanTripDrawer.swift](ios/Roammate/Views/Chat/PlanTripDrawer.swift) -- full rewrite of the view hierarchy
- [PlanTripStore.swift](ios/Roammate/Store/PlanTripStore.swift) -- add messages array, adjust phase logic

---

## Enhancement 2: Trip Landing Page Revamp

**Current state:** [TripLandingView.swift](ios/Roammate/Views/Trips/TripLandingView.swift) has a white background with left-aligned trip name, date range text, a travellers strip, and four section buttons. The web app uses a dark `slate-950` background with indigo gradient blurs, centered trip name in a large cinematic layout.

**Changes:**

- **Background**: Change from `Color.roammateBackground` (light gray) to a dark indigo gradient background, matching the web app's `slate-950` with subtle indigo/violet blur orbs.
- **Top 40% Hero Section** (center-aligned):
  - Trip name in large `.largeTitle` white text, centered.
  - Start date only (not a range) in white/muted text, with a pencil icon button to edit the start date. Tapping the pencil shows an inline `DatePicker` sheet.
  - Travellers list + "+" invite button enclosed in a rounded rectangle container with a subtle border. The avatars should use white borders instead of the current `roammateBackground` borders.
  - If "+" is tapped, show a small overlay popup (not a full sheet) on the same page with email, role picker, and invite button.
- **Bottom Section**: The four navigation buttons (Plan, Brainstorm, Concierge, People) styled with semi-transparent white/indigo cards to match the dark background.
- **Date display**: Only show start date, remove end date reference. Format as "MMM d, yyyy". Remove the `dateRangeText` computed property.

**Files to modify:**
- [TripLandingView.swift](ios/Roammate/Views/Trips/TripLandingView.swift) -- full UI overhaul
- [TravellersStrip.swift](ios/Roammate/Views/Trips/TravellersStrip.swift) -- update border colors for dark background, wrap in rounded rectangle
- [InviteSheet.swift](ios/Roammate/Views/Trips/InviteSheet.swift) -- convert from `.sheet` to an inline overlay popup

---

## Enhancement 3: Hide Tab Bar on Sub-pages

**Current state:** [MainShell.swift](ios/Roammate/Views/MainShell.swift) always shows the `FloatingTabBar`. When navigating to Trip sub-pages (Plan, Brainstorm, etc.) via `NavigationLink`, the tab bar remains visible.

**Changes:**

- Add a `@State private var hideTabBar: Bool = false` to `MainShell`.
- Pass it down via an `EnvironmentKey` (e.g., `TabBarVisibilityKey`).
- In [TripSubPagesHost.swift](ios/Roammate/Views/Trips/TripSubPagesHost.swift), set `hideTabBar = true` on appear and `false` on disappear.
- In `MainShell`, conditionally show `FloatingTabBar` with a slide-down/fade animation when `hideTabBar` is false.

**Files to modify:**
- [MainShell.swift](ios/Roammate/Views/MainShell.swift) -- add environment key, conditional tab bar display
- [FloatingTabBar.swift](ios/Roammate/Views/FloatingTabBar.swift) -- add transition animation
- [TripSubPagesHost.swift](ios/Roammate/Views/Trips/TripSubPagesHost.swift) -- toggle tab bar visibility
- New: Create a `TabBarVisibility` environment key (can be added to `ViewModifiers.swift` or a new file)

---

## Enhancement 4: Overlay Dropdown Menu (Replace Side Drawer)

**Current state:** [TripSubPagesHost.swift](ios/Roammate/Views/Trips/TripSubPagesHost.swift) uses `.sideDrawer()` modifier from [SideDrawer.swift](ios/Roammate/Theme/SideDrawer.swift) to show a right-side drawer with [SubPageMenu.swift](ios/Roammate/Views/Trips/SubPageMenu.swift).

**Changes:**

- Replace the side drawer with an overlay dropdown that pops down from the top-right menu button.
- The dropdown covers approximately 30% of the screen height, with a rounded card containing the four options (Plan, Brainstorm, Concierge, People) with their icons.
- Add a dimmed scrim behind the dropdown that dismisses it on tap.
- The dropdown should animate in from the top (scale + opacity) anchored to the top-right corner.

**Files to modify:**
- [TripSubPagesHost.swift](ios/Roammate/Views/Trips/TripSubPagesHost.swift) -- replace `.sideDrawer()` with an overlay dropdown
- [SubPageMenu.swift](ios/Roammate/Views/Trips/SubPageMenu.swift) -- restyle as a compact dropdown card instead of a full-height drawer

---

## Enhancement 5: Day Tabs Bar Revamp with Add Day

**Current state:** [DayTabsBar.swift](ios/Roammate/Views/Trips/Plan/DayTabsBar.swift) shows an "Overview" pill followed by "Day N" pills in a horizontal scroll. No "Add Day" functionality exists in the UI. [TripDetailStore.swift](ios/Roammate/Store/TripDetailStore.swift) already has an `addDay(date:)` method.

**Changes:**

- Remove the "Overview" tab entirely.
- Add a permanent "<" (chevron.left) button on the far left and ">" (chevron.right) on the far right, both outside the ScrollView.
- Each day is shown as a rounded rectangular box (not a capsule pill).
- After the last day, show an "Add Day" rounded rectangular box that is always visible.
- Clicking "Add Day" calls `store.addDay(date:)` with the next sequential date, inserts the new day to the left of "Add Day", and scrolls to it.
- "<" button is disabled when the first day is selected; ">" button is disabled when the last day is selected.
- Clicking a day directly selects it.
- **Timeline Drawer**: Change the `BottomDrawer` background from `.ultraThinMaterial` to a solid shade of white (e.g., `Color.roammateSurface` or `Color.white`).
- Update `selectedDayIndex` logic: index 0 now maps to the first day (not "Overview"). Adjust [TimelineDrawerContent.swift](ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift) accordingly.

**Files to modify:**
- [DayTabsBar.swift](ios/Roammate/Views/Trips/Plan/DayTabsBar.swift) -- redesign with arrows, add day, remove overview
- [TimelineDrawerContent.swift](ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift) -- adjust index mapping (no more "overview" at index 0)
- [BottomDrawer.swift](ios/Roammate/Theme/BottomDrawer.swift) -- change `.ultraThinMaterial` to solid white

---

## Enhancement 6: Idea Bin Card Redesign (Voting + Expand/Collapse)

**Current state:** [IdeaRow.swift](ios/Roammate/Views/Trips/Plan/IdeaRow.swift) shows each idea with a photo, title, category pill, and a vertical Up/Down chevron `VoteControl`. Delete is via context menu only. The web app uses ThumbsUp/ThumbsDown buttons with individual counts.

**Changes:**

- **Voting**: Replace the vertical chevron `VoteControl` with horizontal ThumbsUp + ThumbsDown buttons positioned at the bottom-right of the card. Each thumb shows its individual count (e.g., "ThumbsUp 3" and "ThumbsDown 1"). Use `hand.thumbsup.fill` / `hand.thumbsdown.fill` SF Symbols. Green tint for upvote active, rose tint for downvote active. Match web's `emerald-100`/`rose-100` style.
- **Delete button**: Add a trash icon at the top-right corner of each card.
- **Location pin icon**: On the left side, use a `mappin.fill` icon colored by the item's category color (using `Color.categoryColor()`). Replace the current photo/placeholder with this colored pin.
- **Category colors**: Already defined in [RoammateTheme.swift](ios/Roammate/Theme/RoammateTheme.swift) `categoryColor()` -- ensure both the pin icon and the category pill use the same color.
- **Expand/collapse**: Tapping a card expands it vertically to show:
  - Description (enriched details)
  - Address
  - Rating
  - "Added by" info
  - Photo (if available)
- Tapping again collapses it. Only one card can be expanded at a time (expanding one auto-collapses the previous).
- Track the expanded card ID with `@State private var expandedId: Int?` in `IdeaBinView`.

**Files to modify:**
- [IdeaRow.swift](ios/Roammate/Views/Trips/Plan/IdeaRow.swift) -- full redesign with thumbs voting, delete, expand/collapse, category-colored pin
- [IdeaBinView.swift](ios/Roammate/Views/Trips/Plan/IdeaBinView.swift) -- add `expandedId` state, pass it to IdeaRow
- [TimelineRow.swift](ios/Roammate/Views/Trips/Plan/TimelineRow.swift) -- update `VoteControl` to use thumbs style (shared component)

---

## Enhancement 7: Brainstorm Chat UI Revamp

**Current state:** [BrainstormChatView.swift](ios/Roammate/Views/Trips/Brainstorm/BrainstormChatView.swift) is a plain white chat with basic message bubbles. The input bar is functional but the overall experience feels generic.

**Changes:**

- **Empty state**: When there are no messages, show a centered placeholder with an AI avatar and text like "Start brainstorming ideas for your trip" with suggested prompt chips (e.g., "Best restaurants in...", "Must-see attractions", "Hidden gems").
- **Chat background**: Add a subtle pattern or gradient background instead of flat `roammateBackground`.
- **Message bubbles**: Keep the existing [BrainstormMessageBubble.swift](ios/Roammate/Views/Trips/Brainstorm/BrainstormMessageBubble.swift) style (it already has good indigo gradient for user, white for AI) but add:
  - Timestamps on messages (subtle, below each bubble).
  - Markdown rendering for AI responses (bold, lists, etc.) using `AttributedString`.
- **Input bar**: Add a subtle shadow above the input bar. Slightly increase padding and make the send button more prominent (filled circle with arrow, matching the indigo theme).
- **Extract button**: Style it as a floating pill above the input bar with a pulse animation to draw attention.
- **Typing indicator**: Already exists -- keep as-is but ensure the animation is smooth.

**Files to modify:**
- [BrainstormChatView.swift](ios/Roammate/Views/Trips/Brainstorm/BrainstormChatView.swift) -- add empty state, background, extract button styling
- [BrainstormMessageBubble.swift](ios/Roammate/Views/Trips/Brainstorm/BrainstormMessageBubble.swift) -- add timestamp, improve markdown rendering

---

## Enhancement 8: Brainstorm Bin Items (Match Idea Bin Style)

**Current state:** [BrainstormBinView.swift](ios/Roammate/Views/Trips/Brainstorm/BrainstormBinView.swift) shows items with a colored bar on the left, title, category pill, and a delete button. No expand/collapse.

**Changes:**

- Match the card design from Enhancement 6 but **without** voting options.
- Category-colored location pin icon on the left.
- Delete button on the top-right of each card.
- Expand/collapse on tap to show enriched details (description, address, rating, added by, photo).
- Only one card expanded at a time.
- Remove the existing colored bar accent, replace with the pin icon approach.

**Files to modify:**
- [BrainstormBinView.swift](ios/Roammate/Views/Trips/Brainstorm/BrainstormBinView.swift) -- redesign `brainstormRow` to match Idea Bin card style with expand/collapse

---

## Enhancement 9: Notifications Bell on Dashboard

**Current state:** [DashboardView.swift](ios/Roammate/Views/Dashboard/DashboardView.swift) has no notifications bell. [NotificationStore.swift](ios/Roammate/Store/NotificationStore.swift) already has full notification support (load, mark read, mark all read, unread count).

**Changes:**

- Add a bell icon button (`bell.fill`) to the top-right of the Dashboard, next to the greeting.
- Show a red badge with `unreadCount` on the bell when > 0.
- Tapping the bell opens an overlay dropdown popup (similar to Enhancement 4's menu) covering ~40% of the screen from the top-right.
- The popup shows:
  - A "Notifications" header with a "Mark all as read" button.
  - A scrollable list of `AppNotification` items with actor name, type-based description, and timestamp.
  - Unread items have a subtle indigo-tint background.
- Load notifications on dashboard appear via `notificationStore.load()`.

**Files to modify:**
- [DashboardView.swift](ios/Roammate/Views/Dashboard/DashboardView.swift) -- add bell button, notifications overlay
- Create a new `NotificationDropdown.swift` view (or inline in DashboardView)
- Wire `NotificationStore` as `@EnvironmentObject` or `@StateObject` in DashboardView

---

## Enhancement 10: Dashboard Widget Improvements

**Current state:** [TodayWidget.swift](ios/Roammate/Views/Dashboard/TodayWidget.swift) and [TodayWidgetCards.swift](ios/Roammate/Views/Dashboard/TodayWidgetCards.swift) show pre-trip, in-trip, and post-trip cards. The web app has richer content: event slots (ongoing, next, upcoming), progress bars, and direct "Open Trip" / "Plan Itinerary" CTAs.

**Changes:**

- **PreTripCard**: Add a "Plan Itinerary" CTA button, show the start date in a more detailed format (e.g., "Wednesday, May 20").
- **InTripCard**: Show event slots if available -- "Ongoing", "Up Next", "Coming Up" similar to the web widget. This requires fetching today's events from a `/dashboard/today` endpoint or using existing trip data. Add an "Open Trip" button.
- **PostTripCard**: Show total events count and total days if available. Add a "See Recap" CTA.
- **Sizing**: The current `aspectRatio(1)` makes it a square which is very tall. Change to a more landscape/adaptive ratio (e.g., `aspectRatio(0.85)` or remove the fixed ratio).
- **Page indicators**: Keep the existing TabView with page indicators.

**Files to modify:**
- [TodayWidget.swift](ios/Roammate/Views/Dashboard/TodayWidget.swift) -- adjust aspect ratio
- [TodayWidgetCards.swift](ios/Roammate/Views/Dashboard/TodayWidgetCards.swift) -- enhance all three card types with CTAs and richer content

---

## Enhancement 11: Manual Trip Creation Fix

**Current state:** [CreateTripView.swift](ios/Roammate/Views/Trips/CreateTripView.swift) shows a Form with trip name, start date, and end date. It sends both `startDate` and `endDate` to `TripService.createTrip()`. An internal server error occurs on creation.

**Changes:**

- **Remove End Date**: Remove the end date `DatePicker` and its `@State` variable. Send `endDate: nil` in the `TripCreate` payload (already supported by the model).
- **Fix the internal server error**: The backend likely rejects the end date or date format. Investigate the `TripCreate` encoding -- dates may need explicit ISO formatting. Check if the `APIClient` encoder uses `.iso8601` date strategy. The `TripCreate` struct already supports `endDate: nil`, so just ensure it's sent as null.
- **UI Enhancement**: Replace the stock `Form` with a custom styled view:
  - Centered trip name `TextField` with a large font, underline style (not a box).
  - A styled `DatePicker` for just the start date.
  - A prominent "Create Trip" button at the bottom matching the app's button style.
  - Remove the `Section` wrappers and raw Form look.

**Files to modify:**
- [CreateTripView.swift](ios/Roammate/Views/Trips/CreateTripView.swift) -- remove end date, fix error, redesign UI
- Potentially [APIClient.swift](ios/Roammate/Network/APIClient.swift) -- check date encoding strategy

---

## Enhancement 12: Profile Sub-page Tab Bar Hide

**Current state:** [ProfileTabView.swift](ios/Roammate/Views/Profile/ProfileTabView.swift) uses `NavigationLink` to push sub-pages (Edit Profile, Travel Persona, Notifications, Subscription, About). The floating tab bar remains visible on these sub-pages.

**Changes:**

- Use the same `TabBarVisibility` environment key from Enhancement 3.
- When a profile sub-page is pushed (detected via `NavigationStack` path or via `.onAppear` of sub-views), set `hideTabBar = true`.
- When returning to the Profile root, set `hideTabBar = false` with a slide-up animation.
- The tab bar should animate back with a `transition(.move(edge: .bottom).combined(with: .opacity))`.

**Files to modify:**
- [ProfileTabView.swift](ios/Roammate/Views/Profile/ProfileTabView.swift) -- detect navigation depth, toggle tab bar visibility
- The environment key mechanism from Enhancement 3 handles the rest

---

## Shared / Cross-cutting Changes

- **New ThumbsVoteControl**: Create a reusable `ThumbsVoteControl` component (to be used by both Enhancement 6 and potentially Enhancement 8) as a replacement for the current vertical chevron `VoteControl`. Place it in [TimelineRow.swift](ios/Roammate/Views/Trips/Plan/TimelineRow.swift) or extract to a shared file.
- **TabBarVisibility environment key**: Shared between Enhancements 3 and 12. Add to [ViewModifiers.swift](ios/Roammate/Theme/ViewModifiers.swift).
- **Overlay Dropdown component**: A reusable overlay dropdown view modifier (shared between Enhancements 4 and 9). Add to a new file or [ViewModifiers.swift](ios/Roammate/Theme/ViewModifiers.swift).
