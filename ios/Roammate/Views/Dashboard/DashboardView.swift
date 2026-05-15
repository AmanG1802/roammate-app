import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var authManager: AuthManager
    @EnvironmentObject var tripStore: TripStore
    @EnvironmentObject var notificationStore: NotificationStore
    @EnvironmentObject var tabBarVisibility: TabBarVisibility

    @State private var showPlanTrip = false
    @State private var showNotifications = false
    @State private var path = NavigationPath()
    @State private var activeTripEvents: [Event] = []

    private var firstName: String {
        authManager.currentUser?.name
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
                .refreshable { await tripStore.load() }

                ChatFAB {
                    HapticManager.medium()
                    showPlanTrip = true
                }
                .padding(.trailing, RoammateSpacing.lg)
                .padding(.bottom, RoammateLayout.tabBarHeight + RoammateLayout.tabBarBottomInset + 12)

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
            .sheet(isPresented: $showPlanTrip) {
                PlanTripDrawer { Task { await tripStore.load() } }
                    .presentationDetents([.large])
                    .presentationDragIndicator(.visible)
            }
            .onChange(of: path) { _, newPath in
                if newPath.isEmpty {
                    withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                        tabBarVisibility.isVisible = true
                    }
                }
            }
        }
    }

    private func loadActiveTripEvents() async {
        guard let active = TodayWidget.activeTrip(from: tripStore.trips) else { return }
        let now = Date()
        guard let s = active.startDate, let e = active.endDate, s <= now && now <= e else { return }
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
            withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                showNotifications.toggle()
            }
        } label: {
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
        .buttonStyle(.plain)
    }

    // MARK: - Notifications Overlay

    private var notificationsOverlay: some View {
        ZStack(alignment: .topTrailing) {
            Color.black.opacity(0.3)
                .ignoresSafeArea()
                .onTapGesture {
                    withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                        showNotifications = false
                    }
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
                                withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                                    showNotifications = false
                                }
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
                    .frame(maxWidth: .infinity)
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
                }
            }
            .frame(maxHeight: UIScreen.main.bounds.height * 0.45)
            .frame(width: UIScreen.main.bounds.width * 0.82)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(Color.roammateSurface)
                    .shadow(color: .black.opacity(0.15), radius: 20, y: 8)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .stroke(Color.roammateBorder, lineWidth: 0.5)
            )
            .padding(.trailing, RoammateSpacing.md)
            .padding(.top, 50)
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
                let title = (p["titles"] as? [String])?.first ?? "an idea"
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
