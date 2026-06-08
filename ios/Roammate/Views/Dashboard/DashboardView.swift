import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var authManager: AuthManager
    @EnvironmentObject var tripStore: TripStore
    @EnvironmentObject var notificationStore: NotificationStore
    @EnvironmentObject var subscriptionStore: SubscriptionStore
    @EnvironmentObject var tabBarVisibility: TabBarVisibility
    @EnvironmentObject var tutorial: TutorialStore

    @State private var showPlanTrip = false
    @State private var showNotifications = false
    @State private var notifShadowVisible = false
    @State private var path = NavigationPath()
    @State private var activeTripEvents: [Event] = []
    // id of the tutorial trip we've pushed onto `path`, so we push/pop exactly once.
    @State private var tutorialTripPushed: Int? = nil
    // True while the Plan-a-trip sheet is running the tutorial's canned demo.
    @State private var planDemoMode = false
    // Set when the demo's "Create Trip" is tapped so the tour advances (and the
    // trip is pushed) only after the sheet has fully dismissed — pushing onto the
    // stack while the sheet is still animating away intermittently drops the push.
    @State private var advanceAfterDemoDismiss = false

    private var firstName: String {
        authManager.currentUser?.name?
            .split(separator: " ")
            .first
            .map(String.init) ?? "there"
    }

    var body: some View {
        NavigationStack(path: $path) {
            ZStack(alignment: .bottomTrailing) {
                ScrollView {
                    VStack(alignment: .leading, spacing: RoammateSpacing.lg) {
                        HStack(alignment: .top) {
                            greeting
                            Spacer()
                            notificationBell
                        }
                        .padding(.horizontal, RoammateSpacing.md)

                        PastDueBanner()
                            .padding(.horizontal, RoammateSpacing.md)

                        OneTimeExpiryBanner()
                            .padding(.horizontal, RoammateSpacing.md)

                        FreeUsageStrip()
                            .padding(.horizontal, RoammateSpacing.md)

                        TodayWidget(trips: tripStore.trips, activeTripEvents: activeTripEvents) { trip in
                            path.append(trip)
                        }
                        .padding(.horizontal, RoammateSpacing.md)

                        tripListSection
                    }
                    .padding(.top, RoammateSpacing.md)
                    .padding(.bottom, RoammateLayout.contentBottomPadding)
                }
                .background(Color.roammateBackground.ignoresSafeArea())
                .refreshable {
                    async let trips: Void = tripStore.load()
                    async let notifs: Void = notificationStore.load()
                    async let subs: Void = subscriptionStore.refresh()
                    _ = await (trips, notifs, subs)
                    await loadActiveTripEvents()
                }

                ChatFAB {
                    HapticManager.medium()
                    showPlanTrip = true
                }
                .tutorialAnchor("new-trip-btn")
                .padding(.trailing, RoammateSpacing.lg)
                .padding(.bottom, RoammateLayout.tabBarHeight + RoammateLayout.tabBarBottomInset + 12)

                if showNotifications {
                    Rectangle()
                        .fill(.ultraThinMaterial)
                        .opacity(0.55)
                        .overlay(Color.black.opacity(0.15))
                        .ignoresSafeArea()
                        .contentShape(Rectangle())
                        .onTapGesture { toggleNotifications() }
                        .transition(.opacity)
                }
                if showNotifications {
                    notificationsOverlay
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: Trip.self) { trip in
                TripLandingView(trip: trip, popToRoot: { path.removeLast(path.count) })
            }
            .task {
                if tripStore.trips.isEmpty { await tripStore.load() }
                await notificationStore.load()
                await loadActiveTripEvents()
            }
            .sheet(isPresented: $showPlanTrip, onDismiss: {
                planDemoMode = false
                // Advance only after the sheet is fully gone, so applyTutorialNav
                // pushes the trip onto a settled NavigationStack rather than
                // racing the sheet's dismiss animation (which sometimes left
                // Step 4 floating over the dashboard). A plain swipe-to-dismiss
                // never sets the flag, so it just closes the planner.
                if advanceAfterDemoDismiss {
                    advanceAfterDemoDismiss = false
                    Task { await tutorial.advance(to: TutorialScript.number(of: .tripOverview)) }
                }
            }) {
                PlanTripDrawer(
                    onTripCreated: { created in
                        Task { await tripStore.load() }
                        // Push the newly created trip's landing view.
                        path.append(created)
                    },
                    demoMode: planDemoMode,
                    onDemoPreviewShown: {
                        Task { await tutorial.advance(to: TutorialScript.number(of: .planPreview)) }
                    },
                    onDemoCreate: {
                        // Skip the real POST — the seeded tutorial trip already
                        // exists. Just close the sheet; the advance + trip push
                        // happen in onDismiss once the sheet has fully dismissed.
                        advanceAfterDemoDismiss = true
                        planDemoMode = false
                        showPlanTrip = false
                    }
                )
                .presentationDetents([.large])
                .presentationDragIndicator(.visible)
            }
            .onReceive(NotificationCenter.default.publisher(for: .tutorialStartPlanDemo)) { _ in
                // Commit `planDemoMode` first, then present on the next runloop.
                // Flipping both in the same update let the sheet capture a stale
                // `demoMode = false`, so the drawer opened without running the
                // demo on the first "Try Now" tap.
                planDemoMode = true
                DispatchQueue.main.async { showPlanTrip = true }
            }
            .onChange(of: path) { _, newPath in
                if newPath.isEmpty {
                    withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                        tabBarVisibility.isVisible = true
                    }
                    // If the stack was emptied (back-swipe etc.) while the tour
                    // still wants the trip open, clear the flag and re-push.
                    if tutorialTripPushed != nil {
                        tutorialTripPushed = nil
                        applyTutorialNav()
                    }
                    Task {
                        await tripStore.load()
                        await loadActiveTripEvents()
                    }
                }
            }
            // Tutorial: open / close the tutorial trip on this stack as the tour
            // advances. The tour runs entirely on the Dashboard tab.
            .onChange(of: tutorial.currentStep) { _, _ in applyTutorialNav() }
            .onChange(of: tutorial.status) { _, _ in applyTutorialNav() }
            .onChange(of: tutorial.tutorialTripId) { _, _ in applyTutorialNav() }
            .onChange(of: tripStore.trips.count) { _, _ in applyTutorialNav() }
            .onAppear { applyTutorialNav() }
        }
    }

    /// Push or pop the tutorial trip on the Dashboard stack to match the current
    /// step. Pushes exactly once (tracked by `tutorialTripPushed`); if the seeded
    /// trip isn't loaded yet it triggers a load and re-runs via the trips onChange.
    private func applyTutorialNav() {
        let loc = TutorialScript.location(for: tutorial.currentStep)
        let wantTrip = tutorial.isActive && loc.openTrip
        if wantTrip {
            guard let tid = tutorial.tutorialTripId,
                  let trip = tripStore.trips.first(where: { $0.id == tid }) else {
                // Seeded trip not in the store yet — load and let the trips /
                // tripId onChange re-run this.
                if !tripStore.isLoading { Task { await tripStore.load() } }
                return
            }
            // Push if we haven't pushed this trip, or the stack was cleared out
            // from under us (keeps Step 3 reliable rather than trusting the flag).
            if tutorialTripPushed != tid || path.isEmpty {
                path.removeLast(path.count)
                path.append(trip)
                tutorialTripPushed = tid
            }
        } else if tutorialTripPushed != nil || (tutorial.isActive && !path.isEmpty) {
            // Steps 1–2, going Back to the dashboard, or the tour ending (incl.
            // deleting the trip) — return to the dashboard root. Guarded so a
            // non-tutorial user browsing a trip is never yanked back.
            path.removeLast(path.count)
            tutorialTripPushed = nil
        }
    }

    private func loadActiveTripEvents() async {
        guard let active = TodayWidget.activeTrip(from: tripStore.trips) else { return }
        do {
            let events = try await EventService.getEvents(tripId: active.id, dayDate: nil)
            activeTripEvents = events
        } catch {}
    }

    // MARK: - Sub-views

    private var greeting: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("Hi, \(firstName)")
                .font(.system(.largeTitle, design: .rounded, weight: .black))
                .foregroundStyle(Color.roammateInk)
            Text("Let's plan something good.")
                .font(.system(.subheadline, design: .rounded, weight: .medium))
                .foregroundStyle(Color.roammateMuted)
        }
    }

    // MARK: - Notification Bell

    private var notificationBell: some View {
        Button {
            HapticManager.light()
            toggleNotifications()
        } label: {
            bellIconContent
        }
        .buttonStyle(.plain)
    }

    /// The actual bell artwork — extracted so we can render an identical
    /// instance above the scrim while the panel is open (so the real bell
    /// underneath isn't dimmed by the scrim).
    private var bellIconContent: some View {
        ZStack(alignment: .topTrailing) {
            Image(systemName: "bell.fill")
                .font(.system(size: 20, weight: .medium))
                .foregroundStyle(Color.roammateInk)
                .frame(width: 40, height: 40)
                .background(
                    Circle().fill(Color.roammateSurface)
                )
                .overlay(
                    Circle().stroke(Color.roammateBorder, lineWidth: 1)
                )

            if notificationStore.unreadCount > 0 {
                Text("\(min(notificationStore.unreadCount, 99))")
                    .font(.system(size: 10, weight: .black, design: .rounded))
                    .foregroundStyle(.white)
                    .frame(minWidth: 18, minHeight: 18)
                    .background(Circle().fill(Color.roammateDanger))
                    .offset(x: 4, y: -4)
            }
        }
    }

    private func toggleNotifications() {
        if showNotifications {
            // Closing: fade the shadow out first so the panel doesn't feel like
            // it's collapsing under its own weight.
            withAnimation(.easeIn(duration: 0.12)) {
                notifShadowVisible = false
            }
            withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                showNotifications = false
            }
        } else {
            withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                showNotifications = true
            }
            // Shadow eases in after the panel has nearly finished scaling.
            withAnimation(.easeOut(duration: 0.22).delay(0.18)) {
                notifShadowVisible = true
            }
        }
    }

    // MARK: - Notifications Overlay

    private var notificationsOverlay: some View {
        ZStack(alignment: .topTrailing) {
            // Keep the bell crisp above the scrim so it feels like the focal
            // point users tapped to open the panel. Mirrors the dashboard
            // bell's position (top-right with the same padding) and forwards
            // the tap to the same toggle.
            VStack {
                HStack {
                    Spacer()
                    Button(action: toggleNotifications) {
                        bellIconContent
                    }
                    .buttonStyle(.plain)
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.top, RoammateSpacing.md)
                Spacer()
            }

            VStack(spacing: 0) {
                HStack {
                    Text("Notifications")
                        .font(.system(.headline, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.roammateInk)
                    Spacer()
                    if notificationStore.unreadCount > 0 {
                        Button {
                            Task {
                                await notificationStore.markAllRead()
                                try? await Task.sleep(nanoseconds: 600_000_000)
                                toggleNotifications()
                            }
                        } label: {
                            Text("Mark all read")
                                .font(.system(.caption, design: .rounded, weight: .semibold))
                                .foregroundStyle(Color.roammateIndigo)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.vertical, 12)

                Divider()

                if notificationStore.notifications.isEmpty {
                    VStack(spacing: 8) {
                        Image(systemName: "bell.slash")
                            .font(.system(size: 28))
                            .foregroundStyle(Color.roammateMuted)
                        Text("No notifications yet")
                            .font(.system(.subheadline, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.roammateMuted)
                    }
                    .padding(.vertical, RoammateSpacing.xl)
                } else {
                    ScrollView {
                        LazyVStack(spacing: 0) {
                            ForEach(notificationStore.notifications.prefix(20)) { notif in
                                notificationRow(notif)
                                Divider().padding(.leading, RoammateSpacing.md)
                            }
                        }
                    }
                    .frame(maxHeight: UIScreen.main.bounds.height * 0.38)
                }
            }
            .frame(width: UIScreen.main.bounds.width * 0.82)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(Color.roammateSurface)
                    // Shadow opacity is driven by `notifShadowVisible`, which
                    // ramps in after the scale-in (see toggleNotifications) so
                    // the panel doesn't appear to land with a thud.
                    .shadow(
                        color: .black.opacity(notifShadowVisible ? 0.18 : 0),
                        radius: notifShadowVisible ? 24 : 0,
                        y: notifShadowVisible ? 10 : 0
                    )
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .stroke(Color.roammateBorder, lineWidth: 0.5)
            )
            // 64pt clears the 40pt bell + safe-area inset comfortably so the
            // bell remains fully visible above the panel.
            .padding(.trailing, RoammateSpacing.md)
            .padding(.top, 64)
        }
        .transition(.asymmetric(
            insertion: .scale(scale: 0.01, anchor: .topTrailing).combined(with: .opacity),
            removal: .scale(scale: 0.01, anchor: .topTrailing).combined(with: .opacity)
        ))
    }

    private func notificationRow(_ notif: AppNotification) -> some View {
        let rendered = Self.renderNotification(notif)
        return HStack(alignment: .top, spacing: 10) {
            Text(rendered.emoji)
                .font(.system(size: 20))
                .frame(width: 32, height: 32)
                .background(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(notif.isRead ? Color.roammateBackground : Color.roammateIndigoTint)
                )

            VStack(alignment: .leading, spacing: 3) {
                Text(rendered.text)
                    .font(.system(.caption, design: .rounded, weight: .medium))
                    .foregroundStyle(Color.roammateInk)
                    .lineLimit(3)
                Text(relativeTime(notif.createdAt))
                    .font(.system(.caption2, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateMuted.opacity(0.7))
            }

            Spacer()

            if !notif.isRead {
                Circle()
                    .fill(Color.roammateIndigo)
                    .frame(width: 8, height: 8)
            }
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 10)
        .background(notif.isRead ? Color.clear : Color.roammateIndigoTint.opacity(0.3))
        .contentShape(Rectangle())
        .onTapGesture {
            if !notif.isRead {
                Task { await notificationStore.markRead(id: notif.id) }
            }
        }
    }

    // MARK: - Notification Rendering (matches web app)

    static func renderNotification(_ notif: AppNotification) -> (emoji: String, text: String) {
        let p = notif.payload
        let tripName = p["trip_name"]?.stringValue ?? "a trip"
        let actorName = p["actor_name"]?.stringValue ?? notif.actor?.name ?? "Someone"
        let isSelf = p["self"]?.boolValue ?? false

        switch notif.type {
        case "trip_created":
            return ("🌍", "You created \(tripName).")
        case "trip_renamed":
            let from = p["from"]?.stringValue ?? "?"
            let to = p["to"]?.stringValue ?? "?"
            if isSelf { return ("✏️", "You renamed \(from) to \(to).") }
            return ("✏️", "\(actorName) renamed \(from) to \(to).")
        case "trip_date_changed":
            if isSelf { return ("📅", "You changed dates for \(tripName).") }
            return ("📅", "\(actorName) changed dates for \(tripName).")
        case "trip_deleted":
            if isSelf { return ("🗑️", "You deleted \(tripName).") }
            return ("🗑️", "\(actorName) deleted \(tripName).")
        case "invite_received":
            let inviter = p["inviter_name"]?.stringValue ?? "Someone"
            return ("✉️", "\(inviter) invited you to \(tripName).")
        case "invite_accepted":
            if isSelf { return ("✅", "You accepted \(tripName).") }
            let joined = p["joined_user_name"]?.stringValue ?? "Someone"
            return ("👋", "\(joined) joined \(tripName).")
        case "invite_declined":
            let declined = p["declined_user_name"]?.stringValue ?? "Someone"
            return ("❌", "\(declined) declined the invite to \(tripName).")
        case "member_removed":
            if isSelf { return ("🚪", "\(actorName) removed you from \(tripName).") }
            let removed = p["removed_user_name"]?.stringValue ?? "a member"
            return ("🚪", "\(actorName) removed \(removed) from \(tripName).")
        case "member_role_changed":
            let newRole = p["new_role"]?.stringValue ?? "member"
            return ("🎭", "\(actorName) changed your role on \(tripName) to \(newRole).")
        case "group_created":
            let groupName = p["group_name"]?.stringValue ?? ""
            return ("👥", "You created group \(groupName).")
        case "group_invite_received":
            let inviter = p["inviter_name"]?.stringValue ?? "Someone"
            let groupName = p["group_name"]?.stringValue ?? ""
            return ("👥", "\(inviter) invited you to group \(groupName).")
        case "group_invite_accepted":
            let groupName = p["group_name"]?.stringValue ?? ""
            if isSelf { return ("✅", "You joined group \(groupName).") }
            let joined = p["joined_user_name"]?.stringValue ?? "Someone"
            return ("👋", "\(joined) joined group \(groupName).")
        case "idea_bin_item_added":
            let count = p["count"]?.intValue ?? 1
            if count == 1 {
                let title = p["titles"]?.arrayValue?.first?.stringValue ?? "an idea"
                return ("💡", "\(actorName) added \(title) to \(tripName)'s idea bin.")
            }
            return ("💡", "\(actorName) added \(count) ideas to \(tripName)'s idea bin.")
        case "event_added":
            let title = p["title"]?.stringValue ?? "an event"
            return ("➕", "\(actorName) added \(title).")
        case "event_moved":
            let title = p["title"]?.stringValue ?? "an event"
            return ("🕒", "\(actorName) rescheduled \(title).")
        case "event_removed":
            let title = p["title"]?.stringValue ?? "an event"
            let movedToBin = p["moved_to_bin"]?.boolValue ?? false
            if movedToBin { return ("🗑️", "\(actorName) moved \(title) to the idea bin.") }
            return ("🗑️", "\(actorName) removed \(title).")
        case "ripple_fired":
            let dm = p["delta_minutes"]?.intValue ?? 0
            let dir = dm >= 0 ? "pushed back" : "pulled forward"
            let mins = abs(dm)
            let shifted = p["shifted_count"]?.intValue ?? 0
            return ("🌊", "\(actorName) \(dir) \(shifted) events by \(mins)m.")
        default:
            return ("🔔", notif.type.replacingOccurrences(of: "_", with: " "))
        }
    }

    private func relativeTime(_ date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: Date())
    }

    private var tripListSection: some View {
        VStack(alignment: .leading, spacing: RoammateSpacing.sm) {
            SectionHeader(title: "My Trips")
                .tutorialAnchor("dashboard-trips")

            if tripStore.trips.isEmpty {
                EmptyState(
                    icon: "map",
                    title: "No trips yet",
                    subtitle: "Tap the sparkle button to draft one."
                )
                .roammateCard()
                .padding(.horizontal, RoammateSpacing.md)
            } else {
                VStack(spacing: RoammateSpacing.sm) {
                    ForEach(tripStore.trips.prefix(5)) { trip in
                        NavigationLink(value: trip) {
                            TripRow(trip: trip)
                        }
                        .buttonStyle(RoammateRowButtonStyle())
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
            }
        }
    }
}
