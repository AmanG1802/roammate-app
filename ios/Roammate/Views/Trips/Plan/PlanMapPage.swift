import SwiftUI
import MapKit

struct PlanMapPage: View {
    @EnvironmentObject var store: TripDetailStore

    @State private var cameraPosition: MapCameraPosition = .automatic
    @State private var drawerDetent: DrawerDetent = .fraction(0.6)
    @State private var selectedDayIndex = 0
    @State private var selectedEventId: Int?
    @State private var selectedLegIndex: Int?
    @State private var mapStyle: MapStyle = .standard(elevation: .realistic)
    @State private var mapStyleIndex = 0
    @State private var showLegCallout = false

    private var currentDayDate: String? {
        guard selectedDayIndex < store.days.count else { return nil }
        return EventService.isoDateString(from: store.days[selectedDayIndex].date)
    }

    private var dayEvents: [Event] {
        let events: [Event]
        if let day = currentDayDate {
            events = store.eventsByDay[day] ?? []
        } else {
            events = store.eventsByDay.values.flatMap { $0 }
        }
        return events.sorted {
            if let aTime = $0.startTime, let bTime = $1.startTime {
                return aTime < bTime
            }
            return $0.sortOrder < $1.sortOrder
        }
    }

    private var activeEvents: [Event] {
        dayEvents.filter { !$0.isSkipped }
    }

    private var visibleEvents: [Event] {
        activeEvents.filter { $0.lat != nil && $0.lng != nil }
    }

    private var allMarkers: [MapMarker] {
        MapService.buildMarkers(events: dayEvents.filter { !$0.isSkipped }, ideas: currentDayDate == nil ? store.ideas : [])
    }

    private var timelineMarkers: [MapMarker] {
        allMarkers.filter { $0.source == "timeline" }
    }

    private var ideaMarkers: [MapMarker] {
        allMarkers.filter { $0.source == "idea_bin" }
    }

    // Gate checks (matching web's computeGateFailures)
    private var hasMissingTimes: Bool {
        activeEvents.contains { $0.startTime == nil }
    }

    private var hasConflicts: Bool {
        let sorted = activeEvents.sorted {
            if let a = $0.startTime, let b = $1.startTime { return a < b }
            return $0.sortOrder < $1.sortOrder
        }
        guard sorted.count > 1 else { return false }
        for i in 1..<sorted.count {
            if let prevEnd = sorted[i-1].endTime, let currStart = sorted[i].startTime {
                if prevEnd > currStart { return true }
            }
        }
        return false
    }

    private var gateMessage: String? {
        if activeEvents.contains(where: { $0.lat == nil && $0.lng == nil && $0.placeId == nil }) {
            // Some events have no location — but this is soft, not a gate
        }
        if hasMissingTimes && hasConflicts {
            return "Add missing start times and resolve conflicts before generating the route."
        }
        if hasMissingTimes {
            return "Add a start time to every item before generating the route."
        }
        if hasConflicts {
            return "Resolve time conflicts before generating the route."
        }
        return nil
    }

    private var refreshDisabled: Bool {
        currentDayDate == nil || activeEvents.count < 2 || gateMessage != nil
    }

    var body: some View {
        ZStack {
            // Map
            Map(position: $cameraPosition) {
                // Timeline event markers (numbered)
                ForEach(Array(timelineMarkers.enumerated()), id: \.element.id) { index, marker in
                    Annotation(
                        marker.title,
                        coordinate: CLLocationCoordinate2D(latitude: marker.lat, longitude: marker.lng)
                    ) {
                        MapPinView(
                            index: index + 1,
                            category: marker.category,
                            isIdea: false,
                            isSelected: selectedEventId == marker.id
                        )
                        .onTapGesture {
                            selectedEventId = marker.id
                            selectedLegIndex = nil
                        }
                    }
                }

                // Idea markers
                ForEach(ideaMarkers) { marker in
                    Annotation(
                        marker.title,
                        coordinate: CLLocationCoordinate2D(latitude: marker.lat, longitude: marker.lng)
                    ) {
                        MapPinView(
                            index: 0,
                            category: marker.category,
                            isIdea: true,
                            isSelected: false
                        )
                    }
                }

                // Route polylines
                ForEach(store.routeOverlays) { overlay in
                    MapPolyline(overlay.polyline)
                        .stroke(
                            overlay.color.opacity(selectedLegIndex == nil ? 0.85 : (selectedLegIndex == overlay.id ? 1.0 : 0.25)),
                            lineWidth: selectedLegIndex == overlay.id ? 7 : 5
                        )
                }
            }
            .mapStyle(mapStyle)
            .ignoresSafeArea(edges: .top)
            .onTapGesture {
                selectedEventId = nil
                selectedLegIndex = nil
                showLegCallout = false
            }

            // Empty state overlay
            if visibleEvents.isEmpty && store.ideas.filter({ $0.lat != nil && $0.lng != nil }).isEmpty {
                emptyStateOverlay
            }

            // Map overlay controls
            VStack(spacing: 0) {
                // Top row: day badge (leading) + refresh button (centered/trailing) + map controls (trailing)
                HStack(alignment: .top, spacing: 8) {
                    dayBadge
                    Spacer(minLength: 8)
                    refreshRouteButton
                    Spacer(minLength: 8)
                    mapControls
                }
                .padding(.horizontal, 16)
                .padding(.top, 12)

                // Route context message (stale / gated) — lives on its own row
                // beneath the top controls so it doesn't crowd the day badge.
                if let msg = refreshContextMessage, !store.isRouteLoading {
                    HStack {
                        Spacer()
                        Text(msg)
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(gateMessage != nil ? Color.roammateDanger : Color.roammateAmber)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 4)
                            .background(
                                Capsule().fill(
                                    gateMessage != nil
                                        ? Color.roammateDanger.opacity(0.1)
                                        : Color.roammateAmber.opacity(0.1)
                                )
                            )
                            .lineLimit(1)
                            .transition(.opacity)
                        Spacer()
                    }
                    .padding(.top, 6)
                    .padding(.horizontal, 16)
                }

                Spacer()

                // Selected event callout
                if let eventId = selectedEventId,
                   let event = dayEvents.first(where: { $0.id == eventId }) {
                    MapCalloutSheet(event: event)
                        .padding(.horizontal, 16)
                        .padding(.bottom, 8)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }

                // Selected leg callout
                if let legIdx = selectedLegIndex,
                   legIdx < store.routeOverlays.count {
                    let overlay = store.routeOverlays[legIdx]
                    let fromTitle = dayEvents.first(where: { $0.id == overlay.fromEventId })?.title ?? "Start"
                    let toTitle = dayEvents.first(where: { $0.id == overlay.toEventId })?.title ?? "End"
                    RouteLegCallout(
                        fromTitle: fromTitle,
                        toTitle: toTitle,
                        durationSeconds: Int(overlay.duration),
                        distanceMeters: Int(overlay.distance),
                        color: overlay.color
                    )
                    .padding(.horizontal, 16)
                    .padding(.bottom, 8)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
            .animation(.easeInOut(duration: 0.2), value: selectedEventId)
            .animation(.easeInOut(duration: 0.2), value: selectedLegIndex)

            // Bottom drawer
            BottomDrawer(
                detents: [.minimised(140), .fraction(0.6), .fraction(0.9)],
                current: $drawerDetent,
                panelAnchorID: "timeline-day-1"
            ) {
                TimelineDrawerContent(selectedDayIndex: $selectedDayIndex)
                    .environmentObject(store)
            }
        }
        .onAppear {
            fitCamera()
            loadRouteForCurrentDay()
        }
        .onChange(of: selectedDayIndex) { _, _ in
            fitCamera()
            store.clearRoute()
            loadRouteForCurrentDay()
        }
        .onChange(of: store.eventsByDay) { _, _ in
            if let day = currentDayDate {
                store.checkRouteStaleness(dayDate: day)
            }
        }
    }

    // MARK: - Subviews

    private var dayBadge: some View {
        HStack(spacing: 4) {
            Image(systemName: "calendar")
                .font(.system(size: 11, weight: .bold))
                .foregroundStyle(Color.roammateMuted)
            Text(dayBadgeText)
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(Color.roammateMuted)
                .textCase(.uppercase)
                .lineLimit(1)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .shadow(color: .black.opacity(0.08), radius: 8, y: 2)
    }

    private var dayBadgeText: String {
        guard let day = currentDayDate else { return "All Days" }
        let fmt = DateFormatter()
        fmt.dateFormat = "yyyy-MM-dd"
        if let date = fmt.date(from: day) {
            let display = DateFormatter()
            display.dateFormat = "EEE, MMM d"
            return "Day \u{00B7} \(display.string(from: date))"
        }
        return day
    }

    private var mapControls: some View {
        VStack(spacing: 8) {
            // Fit all markers
            mapControlButton(icon: "location.viewfinder", title: "Fit all") {
                fitCamera()
            }
            // Map style toggle
            mapControlButton(icon: "map", title: "Map style") {
                cycleMapStyle()
            }
        }
    }

    private func mapControlButton(icon: String, title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(Color.roammateMuted)
                .frame(width: 38, height: 38)
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .shadow(color: .black.opacity(0.08), radius: 8, y: 2)
        }
        .accessibilityLabel(title)
    }

    private var refreshRouteButton: some View {
        Button {
            Task {
                guard let day = currentDayDate else { return }
                await store.refreshRoute(dayDate: day)
            }
        } label: {
            HStack(spacing: 5) {
                if store.isRouteStale && !refreshDisabled && !store.isRouteLoading {
                    Circle()
                        .fill(Color.roammateAmber)
                        .frame(width: 5, height: 5)
                }

                if store.isRouteLoading {
                    ProgressView()
                        .scaleEffect(0.6)
                        .tint(Color.roammateIndigo)
                } else {
                    Image(systemName: "arrow.trianglehead.2.clockwise")
                        .font(.system(size: 11, weight: .bold))
                }

                Text(store.isRouteLoading ? "Routing\u{2026}" : "Refresh Route")
                    .font(.system(size: 10, weight: .black))
                    .textCase(.uppercase)
                    .tracking(0.6)
            }
            .foregroundStyle(buttonForeground)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.ultraThinMaterial)
            .clipShape(Capsule())
            .overlay(
                Capsule().strokeBorder(buttonBorder, lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.08), radius: 8, y: 2)
        }
        .disabled(refreshDisabled || store.isRouteLoading)
        .opacity(refreshDisabled ? 0.5 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: store.isRouteStale)
        .animation(.easeInOut(duration: 0.2), value: store.isRouteLoading)
    }

    /// Mirrors the legacy `contextMessage` computed property; lifted out so the
    /// top-row HStack can render it on its own line beneath the controls.
    private var refreshContextMessage: String? { contextMessage }

    private var buttonForeground: Color {
        if gateMessage != nil { return Color.roammateDanger.opacity(0.6) }
        if store.isRouteStale && !refreshDisabled { return Color.roammateAmber }
        if refreshDisabled { return Color.roammateMuted.opacity(0.5) }
        return Color.roammateIndigo
    }

    private var buttonBorder: Color {
        if gateMessage != nil { return Color.roammateDanger.opacity(0.3) }
        if store.isRouteStale && !refreshDisabled { return Color.roammateAmber.opacity(0.4) }
        if refreshDisabled { return Color.roammateBorder }
        return Color.roammateIndigo.opacity(0.3)
    }

    private var contextMessage: String? {
        if let gate = gateMessage { return gate }
        if store.isRouteStale { return "Timeline changed \u{2014} refresh to update route" }
        return nil
    }

    private var emptyStateOverlay: some View {
        VStack(spacing: 12) {
            Image(systemName: "mappin.slash")
                .font(.system(size: 28))
                .foregroundStyle(Color.roammateIndigo.opacity(0.5))
                .frame(width: 56, height: 56)
                .background(Color.roammateIndigoTint)
                .clipShape(RoundedRectangle(cornerRadius: 16))

            Text("No locations yet")
                .font(.system(size: 14, weight: .black))
                .foregroundStyle(Color.roammateInk)

            Text("Add events with addresses to see them on the map.")
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(Color.roammateMuted)
                .multilineTextAlignment(.center)
        }
        .padding(24)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 20))
        .shadow(color: .black.opacity(0.08), radius: 16, y: 4)
        .padding(40)
    }

    // MARK: - Helpers

    private func fitCamera() {
        let markers = allMarkers
        guard !markers.isEmpty else { return }
        let coords = markers.map {
            CLLocationCoordinate2D(latitude: $0.lat, longitude: $0.lng)
        }
        let lats = coords.map(\.latitude)
        let lngs = coords.map(\.longitude)
        let center = CLLocationCoordinate2D(
            latitude: (lats.min()! + lats.max()!) / 2,
            longitude: (lngs.min()! + lngs.max()!) / 2
        )
        let span = MKCoordinateSpan(
            latitudeDelta: max((lats.max()! - lats.min()!) * 1.4, 0.02),
            longitudeDelta: max((lngs.max()! - lngs.min()!) * 1.4, 0.02)
        )
        cameraPosition = .region(MKCoordinateRegion(center: center, span: span))
    }

    private func cycleMapStyle() {
        mapStyleIndex = (mapStyleIndex + 1) % 3
        switch mapStyleIndex {
        case 0: mapStyle = .standard(elevation: .realistic)
        case 1: mapStyle = .imagery(elevation: .realistic)
        case 2: mapStyle = .hybrid(elevation: .realistic)
        default: break
        }
    }

    private func loadRouteForCurrentDay() {
        guard let day = currentDayDate else { return }
        Task {
            await store.loadStoredRoute(dayDate: day)
        }
    }
}
