import SwiftUI

struct TripLandingView: View {
    let trip: Trip
    let popToRoot: () -> Void
    @StateObject private var store: TripDetailStore
    @State private var showInvite = false
    @State private var subPageDestination: SubPage?
    @State private var editingDate = false
    @State private var dateValue = Date()
    @State private var editingTimezone = false
    @State private var timezoneValue: String = TimeZone.current.identifier

    private static let knownTimezones: [String] = TimeZone.knownTimeZoneIdentifiers.sorted()

    // Inline invite state
    @State private var inviteEmail = ""
    @State private var inviteRole = "view_only"
    @State private var inviteSending = false

    init(trip: Trip, popToRoot: @escaping () -> Void) {
        self.trip = trip
        self.popToRoot = popToRoot
        _store = StateObject(wrappedValue: TripDetailStore(tripId: trip.id))
    }

    private var startDateText: String {
        let f = DateFormatter()
        f.dateFormat = "MMM d, yyyy"
        return f.string(from: dateValue)
    }

    private var dateRangeText: String {
        let short = DateFormatter()
        short.dateFormat = "MMM d"
        let long = DateFormatter()
        long.dateFormat = "MMM d, yyyy"
        if let end = store.trip?.endDate ?? trip.endDate {
            return "\(short.string(from: dateValue)) → \(long.string(from: end))"
        }
        return long.string(from: dateValue)
    }

    private var durationText: String? {
        guard let end = store.trip?.endDate ?? trip.endDate else { return nil }
        let days = Calendar.current.dateComponents([.day], from: dateValue, to: end).day ?? 0
        let total = max(days + 1, 1)
        return "\(total) day\(total == 1 ? "" : "s")"
    }

    private var titleGradient: LinearGradient {
        LinearGradient(
            colors: [Color.roammateIndigo, Color.roammateViolet],
            startPoint: .leading,
            endPoint: .trailing
        )
    }

    private var styledTitle: Text {
        let words = trip.name.split(separator: " ", omittingEmptySubsequences: true).map(String.init)
        guard let last = words.last else {
            return Text(trip.name).foregroundStyle(titleGradient)
        }
        if words.count == 1 {
            return Text(last).foregroundStyle(titleGradient)
        }
        let leading = words.dropLast().joined(separator: " ") + " "
        return Text(leading).foregroundStyle(.white) + Text(last).foregroundStyle(titleGradient)
    }

    private var canInvite: Bool {
        store.members.first(where: { $0.userId == currentUserId })?.role == "admin"
    }

    @EnvironmentObject var authManager: AuthManager
    @EnvironmentObject var tabBarVisibility: TabBarVisibility
    @EnvironmentObject var tripStore: TripStore
    private var currentUserId: Int { authManager.currentUser?.id ?? -1 }

    private let roles: [(value: String, label: String)] = [
        ("admin", "Admin"),
        ("view_with_vote", "Can vote"),
        ("view_only", "View only"),
    ]

    var body: some View {
        ZStack {
            darkBackground

            ScrollView {
                VStack(spacing: 0) {
                    heroSection
                    navButtons
                }
                .padding(.bottom, RoammateLayout.contentBottomPadding)
            }

            if showInvite {
                inviteOverlay
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .principal) {
                HStack(spacing: 6) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 10, weight: .black))
                    Text("TRIP OVERVIEW")
                        .font(.system(size: 10, weight: .black))
                        .tracking(3)
                }
                .foregroundStyle(Color.roammateIndigo)
                .padding(.horizontal, 12)
                .padding(.vertical, 7)
                .background(
                    Capsule().fill(Color.roammateIndigo.opacity(0.10))
                )
                .overlay(
                    Capsule().stroke(Color.roammateIndigo.opacity(0.25), lineWidth: 1)
                )
            }
        }
        .navigationDestination(item: $subPageDestination) { page in
            TripSubPagesHost(trip: trip, initialPage: page, popToRoot: popToRoot)
                .environmentObject(store)
        }
        .task { await store.loadAll() }
        .refreshable { await store.loadAll() }
        .onAppear {
            if let s = store.trip?.startDate {
                dateValue = s
            } else if let s = trip.startDate {
                dateValue = s
            }
            if let tz = store.trip?.timezone, !tz.isEmpty {
                timezoneValue = tz
            } else if let tz = trip.timezone, !tz.isEmpty {
                timezoneValue = tz
            }
            withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                tabBarVisibility.isVisible = false
            }
        }
    }

    // MARK: - Dark Background

    private var darkBackground: some View {
        ZStack {
            Color(red: 15/255, green: 23/255, blue: 42/255)
                .ignoresSafeArea()

            Circle()
                .fill(Color.roammateIndigo.opacity(0.12))
                .frame(width: 400, height: 400)
                .blur(radius: 120)
                .offset(x: -100, y: -150)

            Circle()
                .fill(Color.roammateViolet.opacity(0.10))
                .frame(width: 350, height: 350)
                .blur(radius: 100)
                .offset(x: 120, y: 100)
        }
    }

    // MARK: - Hero Section

    private var heroSection: some View {
        VStack(alignment: .leading, spacing: RoammateSpacing.md) {
            // Title
            styledTitle
                .font(.system(size: 56, weight: .black, design: .default))
                .tracking(-2)
                .lineSpacing(-8)
                .multilineTextAlignment(.leading)
                .minimumScaleFactor(0.7)
                .frame(maxWidth: .infinity, alignment: .leading)

            // Date + duration + timezone pills
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 8) {
                    datePill
                    if let duration = durationText, !editingDate {
                        durationPill(duration)
                    }
                }
                timezonePill
            }

            // Travellers in rounded rectangle
            if !store.members.isEmpty {
                HStack {
                    TravellersStrip(
                        members: store.members,
                        canInvite: canInvite,
                        onInvite: { showInvite = true },
                        darkBackground: true
                    )
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 20, style: .continuous)
                        .fill(Color.white.opacity(0.08))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 20, style: .continuous)
                        .stroke(Color.white.opacity(0.12), lineWidth: 1)
                )
            }

            Spacer().frame(height: RoammateSpacing.sm)
        }
        .padding(.horizontal, RoammateSpacing.lg)
        .padding(.top, RoammateSpacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    // MARK: - Pills

    private var datePill: some View {
        HStack(spacing: 8) {
            Image(systemName: "calendar")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(Color.roammateIndigo)

            if editingDate {
                DatePicker("", selection: $dateValue, displayedComponents: .date)
                    .datePickerStyle(.compact)
                    .labelsHidden()
                    .colorScheme(.dark)

                Button {
                    Task { await saveDate() }
                    editingDate = false
                } label: {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 18))
                        .foregroundStyle(Color.roammateEmerald)
                }
                .buttonStyle(.plain)
            } else {
                Text(dateRangeText)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(.white.opacity(0.9))

                if canInvite {
                    Button {
                        editingDate = true
                    } label: {
                        Image(systemName: "pencil")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(.white.opacity(0.5))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .pillBackground()
    }

    private func durationPill(_ text: String) -> some View {
        HStack(spacing: 6) {
            Image(systemName: "clock")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(Color.roammateViolet)
            Text(text)
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(.white.opacity(0.85))
        }
        .pillBackground()
    }

    private var timezonePill: some View {
        HStack(spacing: 8) {
            Image(systemName: "globe")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(Color.roammateSky)

            if editingTimezone {
                Picker("Timezone", selection: $timezoneValue) {
                    ForEach(Self.knownTimezones, id: \.self) { tz in
                        Text(tz).tag(tz)
                    }
                }
                .pickerStyle(.menu)
                .tint(.white)
                .colorScheme(.dark)

                Button {
                    Task { await saveTimezone() }
                    editingTimezone = false
                } label: {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 18))
                        .foregroundStyle(Color.roammateEmerald)
                }
                .buttonStyle(.plain)
            } else {
                Text(timezoneValue)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(.white.opacity(0.85))

                if canInvite {
                    Button {
                        editingTimezone = true
                    } label: {
                        Image(systemName: "pencil")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(.white.opacity(0.5))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .pillBackground()
    }

    // MARK: - Navigation Buttons

    private var navButtons: some View {
        VStack(spacing: RoammateSpacing.sm) {
            sectionButton(icon: "mappin.and.ellipse", title: "Plan", page: .plan, color: Color.roammateEmerald)
            sectionButton(icon: "lightbulb.fill", title: "Brainstorm", page: .brainstorm, color: Color.roammateAmber)
            sectionButton(icon: "sparkles", title: "Concierge", page: .concierge, color: Color.roammateViolet)
            sectionButton(icon: "person.2.fill", title: "People", page: .people, color: Color.roammateSky)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.top, RoammateSpacing.sm)
    }

    private func sectionButton(icon: String, title: String, page: SubPage, color: Color) -> some View {
        Button {
            subPageDestination = page
        } label: {
            HStack(spacing: RoammateSpacing.md) {
                ZStack {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(color.opacity(0.15))
                    Image(systemName: icon)
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(color)
                }
                .frame(width: 44, height: 44)

                Text(title)
                    .font(.system(.body, design: .rounded, weight: .semibold))
                    .foregroundStyle(.white)

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.4))
            }
            .padding(.horizontal, RoammateSpacing.md)
            .padding(.vertical, 16)
            .background(
                RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                    .fill(Color.white.opacity(0.06))
            )
            .overlay(
                RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                    .stroke(Color.white.opacity(0.1), lineWidth: 1)
            )
        }
        .buttonStyle(RoammateRowButtonStyle())
    }

    // MARK: - Inline Invite Overlay

    private var inviteOverlay: some View {
        ZStack {
            Color.black.opacity(0.5)
                .ignoresSafeArea()
                .onTapGesture {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                        showInvite = false
                    }
                }

            VStack(spacing: RoammateSpacing.md) {
                HStack {
                    Text("Invite traveller")
                        .font(.system(.headline, design: .rounded, weight: .bold))
                        .foregroundStyle(.white)
                    Spacer()
                    Button {
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                            showInvite = false
                        }
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 22))
                            .foregroundStyle(.white.opacity(0.5))
                    }
                    .buttonStyle(.plain)
                }

                TextField("Email address", text: $inviteEmail)
                    .keyboardType(.emailAddress)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                    .font(.system(.body, design: .rounded))
                    .foregroundStyle(.white)
                    .padding(12)
                    .background(
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .fill(Color.white.opacity(0.1))
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .stroke(Color.white.opacity(0.2), lineWidth: 1)
                    )

                VStack(alignment: .leading, spacing: 6) {
                    Text("Role")
                        .font(.system(.caption, design: .rounded, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.6))
                    HStack(spacing: 8) {
                        ForEach(roles, id: \.value) { r in
                            Button {
                                inviteRole = r.value
                            } label: {
                                Text(r.label)
                                    .font(.system(.caption, design: .rounded, weight: .semibold))
                                    .foregroundStyle(inviteRole == r.value ? .white : .white.opacity(0.7))
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 8)
                                    .background(
                                        Capsule().fill(inviteRole == r.value ? Color.roammateIndigo : Color.white.opacity(0.1))
                                    )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }

                Button {
                    Task { await sendInvite() }
                } label: {
                    if inviteSending {
                        ProgressView().tint(.white)
                    } else {
                        Text("Send Invite")
                    }
                }
                .buttonStyle(RoammatePrimaryButtonStyle(isLoading: inviteSending))
                .disabled(inviteEmail.isEmpty || inviteSending)
            }
            .padding(RoammateSpacing.lg)
            .background(
                RoundedRectangle(cornerRadius: RoammateRadius.card, style: .continuous)
                    .fill(Color(red: 30/255, green: 30/255, blue: 60/255))
            )
            .shadow(color: .black.opacity(0.2), radius: 30, y: 10)
            .padding(.horizontal, RoammateSpacing.lg)
            .transition(.scale(scale: 0.9).combined(with: .opacity))
        }
        .animation(.spring(response: 0.3, dampingFraction: 0.85), value: showInvite)
    }

    // MARK: - Actions

    private func saveDate() async {
        let _ = try? await TripService.updateTrip(
            id: trip.id,
            update: TripUpdate(name: nil, startDate: dateValue, endDate: nil, timezone: nil)
        )
        await store.loadAll()
        await tripStore.load()
    }

    private func saveTimezone() async {
        let _ = try? await TripService.updateTrip(
            id: trip.id,
            update: TripUpdate(name: nil, startDate: nil, endDate: nil, timezone: timezoneValue)
        )
        await store.loadAll()
        await tripStore.load()
    }

    private func sendInvite() async {
        inviteSending = true
        defer { inviteSending = false }
        await store.invite(email: inviteEmail, role: inviteRole)
        HapticManager.success()
        inviteEmail = ""
        withAnimation { showInvite = false }
    }
}

private extension View {
    func pillBackground() -> some View {
        self
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(
                Capsule(style: .continuous).fill(Color.white.opacity(0.06))
            )
            .overlay(
                Capsule(style: .continuous).stroke(Color.white.opacity(0.10), lineWidth: 1)
            )
    }
}
