import SwiftUI

enum SubPage: String, CaseIterable, Identifiable, Hashable {
    case plan = "Plan"
    case brainstorm = "Brainstorm"
    case concierge = "Concierge"
    case people = "People"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .plan: return "mappin.and.ellipse"
        case .brainstorm: return "lightbulb.fill"
        case .concierge: return "sparkles"
        case .people: return "person.2.fill"
        }
    }
}

struct TripSubPagesHost: View {
    let trip: Trip
    let initialPage: SubPage
    let popToRoot: () -> Void

    @EnvironmentObject var authManager: AuthManager
    @EnvironmentObject var detailStore: TripDetailStore
    @EnvironmentObject var tabBarVisibility: TabBarVisibility
    @EnvironmentObject var tripStore: TripStore
    @EnvironmentObject var subscriptionStore: SubscriptionStore
    @EnvironmentObject var tutorial: TutorialStore
    @StateObject private var brainstormStore: BrainstormStore
    @StateObject private var conciergeStore: ConciergeStore

    @State private var currentPage: SubPage
    @State private var showMenu = false
    @State private var showDeleteConfirm = false

    init(trip: Trip, initialPage: SubPage = .plan, popToRoot: @escaping () -> Void) {
        self.trip = trip
        self.initialPage = initialPage
        self.popToRoot = popToRoot
        _currentPage = State(initialValue: initialPage)
        _brainstormStore = StateObject(wrappedValue: BrainstormStore(tripId: trip.id))
        _conciergeStore = StateObject(wrappedValue: ConciergeStore(trip: trip))
    }

    /// Mirrors the web admin gate for the Concierge action surface.
    private var isConciergeAdmin: Bool {
        if trip.myRole == "admin" { return true }
        guard let uid = authManager.currentUser?.id else { return false }
        return detailStore.members.first(where: { $0.userId == uid })?.role == "admin"
    }

    var body: some View {
        ZStack {
            Color.roammateBackground.ignoresSafeArea()

            VStack(spacing: 0) {
                topBar
                pageContent
            }

            // Overlay dropdown menu
            if showMenu {
                Color.black.opacity(0.3)
                    .ignoresSafeArea()
                    .onTapGesture {
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                            showMenu = false
                        }
                    }
                    .transition(.opacity)

                VStack {
                    HStack {
                        Spacer()
                        dropdownMenu
                            .padding(.trailing, RoammateSpacing.md)
                            .padding(.top, 56)
                    }
                    Spacer()
                }
                .transition(.opacity)
            }
        }
        .animation(.spring(response: 0.3, dampingFraction: 0.85), value: showMenu)
        .navigationBarHidden(true)
        .onAppear {
            tabBarVisibility.isVisible = false
            applyTutorialPage()
        }
        .onChange(of: tutorial.currentStep) { _, _ in applyTutorialPage() }
        .alert("Delete trip?", isPresented: $showDeleteConfirm) {
            Button("Delete", role: .destructive) {
                Task {
                    try? await TripService.deleteTrip(id: trip.id)
                    tripStore.trips.removeAll { $0.id == trip.id }
                    HapticManager.success()
                    popToRoot()
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will permanently delete \"\(trip.name)\" and all its data. This cannot be undone.")
        }
        .task {
            brainstormStore.onIdeasPromoted = { promoted in
                detailStore.ideas.insert(contentsOf: promoted, at: 0)
            }
            brainstormStore.onIdeasTimeUpdated = { [weak detailStore] in
                await detailStore?.reloadIdeas()
            }
            // After a Concierge mutation (ripple / skip / add), refresh the
            // shared itinerary so the Map/Timeline destinations stay in sync.
            conciergeStore.onEventsChanged = { [weak detailStore] in
                await detailStore?.loadAll()
            }
        }
    }

    /// Tutorial: switch the visible sub-page to match the current step (the pane
    /// slider within each page is driven by Plan/BrainstormPaneView).
    private func applyTutorialPage() {
        guard tutorial.isActive else { return }
        let loc = TutorialScript.location(for: tutorial.currentStep)
        if let sp = loc.subPage, currentPage != sp {
            withAnimation(.easeInOut(duration: 0.3)) { currentPage = sp }
        }
    }

    private var topBar: some View {
        HStack(spacing: 8) {
            Button {
                HapticManager.light()
                popToRoot()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Color.roammateInk)
            }

            Spacer(minLength: 4)

            Text(trip.name)
                .font(.system(.title3, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.roammateInk)
                .lineLimit(1)

            Spacer(minLength: 4)

            if currentPage == .brainstorm {
                BrainstormQuotaPill()
            }

            if currentPage == .concierge && isConciergeAdmin {
                conciergeNavIcon("mappin.and.ellipse", .map, label: "Open map")
                conciergeNavIcon("list.bullet.rectangle", .timeline, label: "Open timeline")
            }

            Button {
                HapticManager.light()
                withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                    showMenu.toggle()
                }
            } label: {
                Image(systemName: showMenu ? "xmark" : "line.3.horizontal")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(Color.roammateInk)
                    .frame(width: 36, height: 36)
                    .background(
                        Circle().fill(Color.roammateSurface)
                    )
                    .overlay(Circle().stroke(Color.roammateBorder, lineWidth: 0.5))
            }
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 12)
        .background(Color.roammateSurface.ignoresSafeArea(edges: .top))
        .zIndex(1)
    }

    /// Concierge-only top-bar icon that opens a full-screen Map / Timeline.
    private func conciergeNavIcon(_ icon: String, _ target: ConciergeDetail, label: String) -> some View {
        Button {
            HapticManager.light()
            conciergeStore.detail = target
        } label: {
            Image(systemName: icon)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(Color.roammateInk)
                .frame(width: 36, height: 36)
                .background(Circle().fill(Color.roammateSurface))
                .overlay(Circle().stroke(Color.roammateBorder, lineWidth: 0.5))
        }
        .accessibilityLabel(label)
    }

    // MARK: - Dropdown Menu

    private var dropdownMenu: some View {
        VStack(spacing: 0) {
            ForEach(SubPage.allCases) { page in
                Button {
                    HapticManager.selection()
                    currentPage = page
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                        showMenu = false
                    }
                } label: {
                    HStack(spacing: 12) {
                        Image(systemName: page.icon)
                            .font(.system(size: 16, weight: .medium))
                            .frame(width: 24)
                            .foregroundStyle(
                                page == currentPage ? Color.roammateIndigo : Color.roammateMuted
                            )

                        Text(page.rawValue)
                            .font(.system(.body, design: .rounded, weight: .medium))
                            .foregroundStyle(
                                page == currentPage ? Color.roammateIndigo : Color.roammateInk
                            )

                        Spacer()

                        if page == currentPage {
                            Image(systemName: "checkmark")
                                .font(.system(size: 13, weight: .bold))
                                .foregroundStyle(Color.roammateIndigo)
                        }
                    }
                    .padding(.horizontal, RoammateSpacing.md)
                    .padding(.vertical, 14)
                    .background(
                        page == currentPage
                            ? Color.roammateIndigoTint
                            : Color.clear
                    )
                }
                .buttonStyle(.plain)

                if page != SubPage.allCases.last {
                    Divider().padding(.horizontal, RoammateSpacing.md)
                }
            }

            Divider().padding(.horizontal, RoammateSpacing.md)

            Button {
                withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                    showMenu = false
                }
                showDeleteConfirm = true
            } label: {
                HStack(spacing: 12) {
                    Image(systemName: "trash")
                        .font(.system(size: 16, weight: .medium))
                        .frame(width: 24)
                        .foregroundStyle(Color.roammateDanger)

                    Text("Delete Trip")
                        .font(.system(.body, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.roammateDanger)

                    Spacer()
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.vertical, 14)
            }
            .buttonStyle(.plain)
        }
        .frame(width: 220)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color.roammateSurface)
                .shadow(color: .black.opacity(0.15), radius: 20, y: 8)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Color.roammateBorder, lineWidth: 0.5)
        )
    }

    @ViewBuilder
    private var pageContent: some View {
        Group {
            switch currentPage {
            case .plan:
                PlanPaneView()
            case .brainstorm:
                BrainstormPaneView()
            case .concierge:
                TripConciergeView(trip: trip)
            case .people:
                PeoplePaneView()
            }
        }
        .transition(.opacity.animation(.easeInOut(duration: 0.3)))
        .id(currentPage)
        .environmentObject(detailStore)
        .environmentObject(brainstormStore)
        .environmentObject(conciergeStore)
    }
}
