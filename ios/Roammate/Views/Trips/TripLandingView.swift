import SwiftUI

struct TripLandingView: View {
    let trip: Trip
    let popToRoot: () -> Void
    @StateObject private var store: TripDetailStore
    @State private var showInvite = false
    @State private var subPageDestination: SubPage?
    @State private var editingDate = false
    @State private var dateValue = Date()

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
        VStack(spacing: RoammateSpacing.md) {
            Spacer().frame(height: RoammateSpacing.xl)

            Text(trip.name)
                .font(.system(size: 44, design: .serif).weight(.black))
                .foregroundStyle(
                    LinearGradient(
                        colors: [.white, Color.roammateViolet.opacity(0.85), .white],
                        startPoint: .leading, endPoint: .trailing
                    )
                )
                .multilineTextAlignment(.center)
                .padding(.horizontal, RoammateSpacing.lg)

            // Start date with pencil edit
            HStack(spacing: 8) {
                Image(systemName: "calendar")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(.white.opacity(0.7))

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
                            .font(.system(size: 22))
                            .foregroundStyle(Color.roammateEmerald)
                    }
                    .buttonStyle(.plain)
                } else {
                    Text(startDateText)
                        .font(.system(.title3, design: .rounded, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.9))

                    if canInvite {
                        Button {
                            editingDate = true
                        } label: {
                            Image(systemName: "pencil")
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(.white.opacity(0.6))
                        }
                        .buttonStyle(.plain)
                    }
                }
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

            Spacer().frame(height: RoammateSpacing.md)
        }
        .frame(maxWidth: .infinity)
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

    private func sendInvite() async {
        inviteSending = true
        defer { inviteSending = false }
        await store.invite(email: inviteEmail, role: inviteRole)
        HapticManager.success()
        inviteEmail = ""
        withAnimation { showInvite = false }
    }
}
