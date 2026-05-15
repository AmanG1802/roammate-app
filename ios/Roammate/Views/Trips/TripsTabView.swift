import SwiftUI

private enum TripTab: String, CaseIterable {
    case upcoming = "Upcoming"
    case past = "Past"
}

struct TripsTabView: View {
    @EnvironmentObject var tripStore: TripStore
    @EnvironmentObject var tabBarVisibility: TabBarVisibility
    @State private var showCreate = false
    @State private var path = NavigationPath()
    @State private var tripToDelete: Trip?
    @State private var selectedTab: TripTab = .upcoming
    @State private var isDeleteMode = false
    @State private var selectedForDeletion: Set<Int> = []

    private var upcomingTrips: [Trip] {
        let now = Calendar.current.startOfDay(for: Date())
        return tripStore.trips.filter { trip in
            guard let end = trip.endDate else { return true }
            return end >= now
        }
    }

    private var pastTrips: [Trip] {
        let now = Calendar.current.startOfDay(for: Date())
        return tripStore.trips.filter { trip in
            guard let end = trip.endDate else { return false }
            return end < now
        }
    }

    private var displayedTrips: [Trip] {
        selectedTab == .upcoming ? upcomingTrips : pastTrips
    }

    var body: some View {
        NavigationStack(path: $path) {
            ZStack(alignment: .bottom) {
                VStack(spacing: 0) {
                    tabPill
                    tripsList
                }
                .background(Color.roammateBackground.ignoresSafeArea())

                if selectedTab == .upcoming && !isDeleteMode {
                    addTripFAB
                }
            }
            .navigationTitle("My Trips")
            .navigationBarTitleDisplayMode(.large)
            .navigationDestination(for: Trip.self) { trip in
                TripLandingView(trip: trip, popToRoot: { path.removeLast(path.count) })
            }
            .toolbar { toolbarContent }
            .refreshable { await tripStore.load() }
            .task {
                if tripStore.trips.isEmpty { await tripStore.load() }
            }
            .sheet(isPresented: $showCreate) {
                CreateTripView { Task { await tripStore.load() } }
                    .environmentObject(tripStore)
            }
            .onChange(of: path) { _, newPath in
                if newPath.isEmpty {
                    withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                        tabBarVisibility.isVisible = true
                    }
                }
            }
            .alert("Delete trip?", isPresented: .init(
                get: { tripToDelete != nil },
                set: { if !$0 { tripToDelete = nil } }
            )) {
                Button("Delete", role: .destructive) {
                    if let trip = tripToDelete {
                        Task {
                            await tripStore.delete(id: trip.id)
                            HapticManager.success()
                        }
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This will permanently delete \"\(tripToDelete?.name ?? "")\" and all its data. This cannot be undone.")
            }
            .alert("Delete \(selectedForDeletion.count) trip\(selectedForDeletion.count == 1 ? "" : "s")?", isPresented: .init(
                get: { isDeleteMode && !selectedForDeletion.isEmpty && tripToDelete == nil && showBulkDeleteConfirm },
                set: { if !$0 { showBulkDeleteConfirm = false } }
            )) {
                Button("Delete", role: .destructive) {
                    Task { await bulkDelete() }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This will permanently delete the selected trips and all their data. This cannot be undone.")
            }
        }
    }

    @State private var showBulkDeleteConfirm = false

    // MARK: - Tab Pill

    private var tabPill: some View {
        HStack(spacing: 4) {
            ForEach(TripTab.allCases, id: \.self) { tab in
                Button {
                    HapticManager.selection()
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                        selectedTab = tab
                        if isDeleteMode {
                            isDeleteMode = false
                            selectedForDeletion.removeAll()
                        }
                    }
                } label: {
                    Text(tab.rawValue)
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(selectedTab == tab ? .white : Color.roammateInk)
                        .padding(.horizontal, 20)
                        .padding(.vertical, 8)
                        .background(
                            Capsule().fill(selectedTab == tab ? Color.roammateIndigo : Color.clear)
                        )
                }
                .buttonStyle(.plain)
            }
        }
        .padding(4)
        .background(
            Capsule().fill(Color.roammateSurface)
        )
        .overlay(
            Capsule().stroke(Color.roammateBorder, lineWidth: 1)
        )
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, RoammateSpacing.sm)
    }

    // MARK: - Trips List

    private var tripsList: some View {
        ScrollView {
            LazyVStack(spacing: RoammateSpacing.sm) {
                if displayedTrips.isEmpty && !tripStore.isLoading {
                    EmptyState(
                        icon: selectedTab == .upcoming ? "map" : "clock.arrow.circlepath",
                        title: selectedTab == .upcoming ? "No upcoming trips" : "No past trips",
                        subtitle: selectedTab == .upcoming ? "Tap + to start planning" : "Completed trips will appear here"
                    )
                    .padding(.top, RoammateSpacing.xxl)
                } else {
                    ForEach(displayedTrips) { trip in
                        if isDeleteMode {
                            tripDeleteRow(trip)
                        } else {
                            NavigationLink(value: trip) {
                                TripRow(trip: trip)
                            }
                            .buttonStyle(RoammateRowButtonStyle())
                            .contextMenu {
                                Button(role: .destructive) {
                                    tripToDelete = trip
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                        }
                    }
                }
            }
            .padding(.horizontal, RoammateSpacing.md)
            .padding(.top, RoammateSpacing.sm)
            .padding(.bottom, RoammateLayout.contentBottomPadding + 60)
        }
    }

    private func tripDeleteRow(_ trip: Trip) -> some View {
        Button {
            HapticManager.selection()
            if selectedForDeletion.contains(trip.id) {
                selectedForDeletion.remove(trip.id)
            } else {
                selectedForDeletion.insert(trip.id)
            }
        } label: {
            HStack(spacing: RoammateSpacing.md) {
                Image(systemName: selectedForDeletion.contains(trip.id) ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 22))
                    .foregroundStyle(selectedForDeletion.contains(trip.id) ? Color.roammateIndigo : Color.roammateMuted)
                TripRow(trip: trip)
            }
        }
        .buttonStyle(.plain)
    }

    // MARK: - Toolbar

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .primaryAction) {
            if isDeleteMode {
                HStack(spacing: 12) {
                    Button("Cancel") {
                        HapticManager.light()
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                            isDeleteMode = false
                            selectedForDeletion.removeAll()
                        }
                    }
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateMuted)

                    Button {
                        HapticManager.warning()
                        showBulkDeleteConfirm = true
                    } label: {
                        Image(systemName: "trash.fill")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(selectedForDeletion.isEmpty ? Color.roammateMuted : Color.roammateDanger)
                    }
                    .disabled(selectedForDeletion.isEmpty)
                }
            } else {
                Menu {
                    Button {
                        HapticManager.light()
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                            isDeleteMode = true
                            selectedForDeletion.removeAll()
                        }
                    } label: {
                        Label("Delete Trips", systemImage: "trash")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(Color.roammateIndigo)
                }
            }
        }
    }

    // MARK: - Add Trip FAB

    private var addTripFAB: some View {
        Button {
            HapticManager.medium()
            showCreate = true
        } label: {
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [Color.roammateIndigo, Color.roammateIndigoDark],
                            startPoint: .topLeading, endPoint: .bottomTrailing
                        )
                    )
                    .shadow(color: Color.roammateIndigo.opacity(0.4), radius: 12, y: 4)
                Image(systemName: "plus")
                    .font(.system(size: 22, weight: .bold))
                    .foregroundStyle(.white)
            }
            .frame(width: 56, height: 56)
        }
        .buttonStyle(.plain)
        .padding(.bottom, RoammateLayout.tabBarHeight + RoammateLayout.tabBarBottomInset + 4)
    }

    // MARK: - Actions

    private func bulkDelete() async {
        let ids = Array(selectedForDeletion)
        for id in ids {
            await tripStore.delete(id: id)
        }
        HapticManager.success()
        withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
            isDeleteMode = false
            selectedForDeletion.removeAll()
        }
    }
}
