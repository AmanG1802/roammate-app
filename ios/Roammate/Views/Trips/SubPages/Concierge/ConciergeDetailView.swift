import SwiftUI
import MapKit

// MARK: - Detail host (full-screen Map / Timeline over the chat)

/// The full-screen destination layered over the Concierge chat. Owns its own
/// top bar — a Back button (returns to chat) plus a 2-pill Map/Timeline toggle.
/// Read-only by design: the day-of itinerary is acted on from the chat.
struct ConciergeDetailView: View {
    @EnvironmentObject var store: ConciergeStore
    @EnvironmentObject var detailStore: TripDetailStore

    @State private var selection: ConciergeDetail

    init(initial: ConciergeDetail) {
        _selection = State(initialValue: initial)
    }

    var body: some View {
        VStack(spacing: 0) {
            topBar
            Group {
                switch selection {
                case .map:      ConciergeMapView()
                case .timeline: ConciergeTimelineView()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .background(Color.roammateBackground.ignoresSafeArea())
    }

    private var topBar: some View {
        HStack(spacing: 12) {
            Button {
                HapticManager.light()
                store.detail = nil
            } label: {
                Image(systemName: "chevron.left")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Color.roammateInk)
                    .frame(width: 36, height: 36)
            }
            .accessibilityLabel("Back to Concierge chat")

            Spacer(minLength: 0)

            // 2-pill segmented toggle
            HStack(spacing: 2) {
                pill(.timeline, icon: "list.bullet", label: "Timeline")
                pill(.map, icon: "map.fill", label: "Map")
            }
            .padding(3)
            .background(Color.roammateBackground, in: Capsule())
            .overlay(Capsule().stroke(Color.roammateBorder, lineWidth: 1))

            Spacer(minLength: 0)

            // Spacer to balance the back button so the toggle stays centered.
            Color.clear.frame(width: 36, height: 36)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 10)
        .background(Color.roammateSurface.ignoresSafeArea(edges: .top))
    }

    private func pill(_ target: ConciergeDetail, icon: String, label: String) -> some View {
        let isOn = selection == target
        return Button {
            HapticManager.selection()
            withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) { selection = target }
        } label: {
            HStack(spacing: 5) {
                Image(systemName: icon).font(.system(size: 12, weight: .bold))
                Text(label).font(.system(.footnote, design: .rounded, weight: .heavy))
            }
            .foregroundStyle(isOn ? .white : Color.roammateMuted)
            .padding(.horizontal, 14).padding(.vertical, 7)
            .background(isOn ? Color.roammateIndigo : Color.clear, in: Capsule())
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Read-only day-of map

struct ConciergeMapView: View {
    @EnvironmentObject var store: ConciergeStore
    @EnvironmentObject var detailStore: TripDetailStore

    @State private var cameraPosition: MapCameraPosition = .automatic
    @State private var selectedEventId: Int?

    private var todayKey: String { store.todayString }

    private var dayEvents: [Event] {
        (detailStore.eventsByDay[todayKey] ?? [])
            .sorted {
                if let a = $0.startTime, let b = $1.startTime { return a < b }
                return $0.sortOrder < $1.sortOrder
            }
    }

    private var markers: [MapMarker] {
        MapService.buildMarkers(events: dayEvents.filter { !$0.isSkipped }, ideas: [])
    }

    private var currentEventId: Int? { conciergeCurrentEvent(dayEvents, tz: tz)?.id }

    private var tz: TimeZone { TimeZone(identifier: store.trip.timezone ?? "UTC") ?? .current }

    var body: some View {
        ZStack {
            Map(position: $cameraPosition) {
                ForEach(Array(markers.enumerated()), id: \.element.id) { index, marker in
                    Annotation(marker.title, coordinate: marker.coordinate) {
                        MapPinView(
                            index: index + 1,
                            category: marker.category,
                            isIdea: false,
                            isSelected: selectedEventId == marker.id || currentEventId == marker.id
                        )
                        .onTapGesture { selectedEventId = marker.id }
                    }
                }

                // Route polylines for today
                ForEach(detailStore.routeOverlays) { overlay in
                    MapPolyline(overlay.polyline)
                        .stroke(overlay.color.opacity(0.85), lineWidth: 5)
                }

                // Nearby search results from a "View on map" hand-off
                ForEach(store.nearbyPins) { pin in
                    Annotation(pin.title, coordinate: CLLocationCoordinate2D(latitude: pin.lat, longitude: pin.lng)) {
                        NearbyPin(place: pin) {
                            HapticManager.light()
                            // Picking one result drops the other pins so the map
                            // shows only the place being added.
                            store.nearbyPins = []
                            store.selectPlace(pin)
                            store.detail = nil
                        }
                    }
                }
            }
            .mapStyle(.standard(elevation: .realistic))
            .ignoresSafeArea(edges: .bottom)
            .onTapGesture { selectedEventId = nil }

            if markers.isEmpty && store.nearbyPins.isEmpty {
                emptyState
            }

            // Refresh today's route after adding/removing stops.
            VStack {
                HStack {
                    Spacer()
                    refreshRouteButton
                }
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)

            VStack {
                Spacer()
                if let id = selectedEventId, let event = dayEvents.first(where: { $0.id == id }) {
                    MapCalloutSheet(event: event)
                        .padding(.horizontal, 16)
                        .padding(.bottom, 16)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
            .animation(.easeInOut(duration: 0.2), value: selectedEventId)
        }
        .task {
            await detailStore.loadStoredRoute(dayDate: todayKey)
            fitCamera()
        }
    }

    private var refreshRouteButton: some View {
        Button {
            HapticManager.light()
            Task { await detailStore.refreshRoute(dayDate: todayKey) }
        } label: {
            HStack(spacing: 6) {
                if detailStore.isRouteLoading {
                    ProgressView().controlSize(.small).tint(Color.roammateIndigo)
                } else {
                    Image(systemName: "arrow.triangle.2.circlepath")
                        .font(.system(size: 13, weight: .bold))
                }
                Text(detailStore.isRouteLoading ? "Updating…" : "Refresh route")
                    .font(.system(.footnote, design: .rounded, weight: .heavy))
            }
            .foregroundStyle(Color.roammateIndigo)
            .padding(.horizontal, 14).padding(.vertical, 9)
            .background(.ultraThinMaterial, in: Capsule())
            .overlay(Capsule().stroke(Color.roammateIndigo.opacity(0.25), lineWidth: 1))
            .shadow(color: .black.opacity(0.12), radius: 6, y: 2)
        }
        .buttonStyle(.plain)
        .disabled(detailStore.isRouteLoading)
        .accessibilityLabel("Refresh today's route")
    }

    private var emptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: "mappin.slash")
                .font(.system(size: 26))
                .foregroundStyle(Color.roammateIndigo.opacity(0.5))
                .frame(width: 56, height: 56)
                .background(Color.roammateIndigoTint, in: RoundedRectangle(cornerRadius: 16))
            Text("Nothing on the map today")
                .font(.system(size: 14, weight: .black))
                .foregroundStyle(Color.roammateInk)
            Text("Add stops with locations to see today's route.")
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(Color.roammateMuted)
                .multilineTextAlignment(.center)
        }
        .padding(24)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20))
        .padding(40)
    }

    private func fitCamera() {
        var coords = markers.map { CLLocationCoordinate2D(latitude: $0.lat, longitude: $0.lng) }
        coords += store.nearbyPins.map { CLLocationCoordinate2D(latitude: $0.lat, longitude: $0.lng) }
        guard !coords.isEmpty else { return }
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
}

private struct NearbyPin: View {
    let place: PlaceCard
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            ZStack {
                Circle().fill(Color.roammateAmber).frame(width: 30, height: 30)
                    .shadow(color: .black.opacity(0.2), radius: 4, y: 2)
                Image(systemName: "plus")
                    .font(.system(size: 14, weight: .black))
                    .foregroundStyle(.white)
            }
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Read-only day-of timeline

struct ConciergeTimelineView: View {
    @EnvironmentObject var store: ConciergeStore
    @EnvironmentObject var detailStore: TripDetailStore

    private var tz: TimeZone { TimeZone(identifier: store.trip.timezone ?? "UTC") ?? .current }

    private var events: [Event] {
        (detailStore.eventsByDay[store.todayString] ?? [])
            .sorted {
                if let a = $0.startTime, let b = $1.startTime { return a < b }
                return $0.sortOrder < $1.sortOrder
            }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                header

                if events.isEmpty {
                    emptyState
                } else {
                    ForEach(events) { event in
                        ConciergeTimelineRow(
                            event: event,
                            status: conciergeStatus(event, tz: tz)
                        )
                        .padding(.horizontal, RoammateSpacing.md)
                    }
                }
            }
            .padding(.vertical, RoammateSpacing.md)
        }
    }

    private var header: some View {
        let fmt = DateFormatter()
        fmt.dateFormat = "EEEE, MMM d"
        fmt.timeZone = tz
        return Text("Today · \(fmt.string(from: Date()))")
            .font(.system(.title3, design: .rounded, weight: .heavy))
            .foregroundStyle(Color.roammateInk)
            .padding(.horizontal, RoammateSpacing.md)
            .padding(.bottom, RoammateSpacing.sm)
    }

    private var emptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: "calendar")
                .font(.system(size: 26))
                .foregroundStyle(Color.roammateIndigo.opacity(0.5))
                .frame(width: 56, height: 56)
                .background(Color.roammateIndigoTint, in: RoundedRectangle(cornerRadius: 16))
            Text("No stops scheduled today")
                .font(.system(size: 14, weight: .black))
                .foregroundStyle(Color.roammateInk)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 60)
    }
}

private struct ConciergeTimelineRow: View {
    let event: Event
    let status: String

    private var dotColor: Color {
        switch status {
        case "completed": return .roammateSuccess
        case "ongoing":   return .roammateIndigo
        case "skipped":   return .roammateMuted
        default:          return Color.categoryColor(event.category)
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(spacing: 0) {
                Circle().fill(dotColor).frame(width: 12, height: 12)
                Rectangle().fill(Color.roammateBorder).frame(width: 2)
            }
            .frame(width: 12)

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 8) {
                    Text(event.title)
                        .font(.system(.subheadline, design: .rounded, weight: .bold))
                        .foregroundStyle(status == "skipped" ? Color.roammateMuted : Color.roammateInk)
                        .strikethrough(status == "skipped")
                    if status == "ongoing" {
                        Text("NOW")
                            .font(.system(size: 9, weight: .black))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 6).padding(.vertical, 2)
                            .background(Color.roammateIndigo, in: Capsule())
                    }
                }
                HStack(spacing: 8) {
                    Text(eventTimeShort(event))
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(event.startTime == nil ? Color.roammateAmber : Color.roammateMuted)
                    if let category = event.category {
                        Text(category)
                            .font(.system(size: 11, weight: .bold))
                            .foregroundStyle(Color.categoryColor(category))
                    }
                }
                if let address = event.address, !address.isEmpty {
                    Text(address)
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(Color.roammateMuted)
                        .lineLimit(1)
                }
            }
            .padding(.bottom, RoammateSpacing.md)

            Spacer(minLength: 0)
        }
        .opacity(status == "skipped" ? 0.55 : 1)
    }
}

// MARK: - Shared day-of helpers

/// The event currently in progress today (start ≤ now ≤ end), if any.
func conciergeCurrentEvent(_ events: [Event], tz: TimeZone) -> Event? {
    let now = Date()
    for e in events where !e.isSkipped {
        guard let start = e.startTime?.combine(day: now, tz: tz) else { continue }
        let end = e.endTime?.combine(day: now, tz: tz) ?? start.addingTimeInterval(3600)
        if start <= now && now <= end { return e }
    }
    return nil
}

/// Status bucket for a day-of event: completed / ongoing / upcoming / skipped.
func conciergeStatus(_ event: Event, tz: TimeZone) -> String {
    if event.isSkipped { return "skipped" }
    let now = Date()
    let start = event.startTime?.combine(day: now, tz: tz)
    let end = event.endTime?.combine(day: now, tz: tz) ?? start?.addingTimeInterval(3600)
    if let end, end <= now { return "completed" }
    if let start, start <= now { return "ongoing" }
    return "upcoming"
}

private extension MapMarker {
    var coordinate: CLLocationCoordinate2D { CLLocationCoordinate2D(latitude: lat, longitude: lng) }
}
