import SwiftUI
import MapKit

struct PlanMapPage: View {
    @EnvironmentObject var store: TripDetailStore

    @State private var cameraPosition: MapCameraPosition = .automatic
    @State private var drawerDetent: DrawerDetent = .fraction(0.6)
    @State private var selectedDayIndex = 0

    private var allEvents: [Event] {
        store.eventsByDay.values.flatMap { $0 }
    }

    private var markers: [MapMarker] {
        MapService.buildMarkers(events: allEvents, ideas: store.ideas)
    }

    var body: some View {
        ZStack {
            Map(position: $cameraPosition) {
                ForEach(markers) { marker in
                    Marker(
                        marker.title,
                        systemImage: Color.categoryIcon(marker.category),
                        coordinate: CLLocationCoordinate2D(
                            latitude: marker.lat,
                            longitude: marker.lng
                        )
                    )
                    .tint(marker.source == "timeline"
                          ? Color.categoryColor(marker.category)
                          : Color.roammateMuted)
                }
            }
            .mapStyle(.standard(elevation: .realistic))
            .ignoresSafeArea(edges: .top)

            BottomDrawer(
                detents: [.minimised(140), .fraction(0.6), .fraction(0.9)],
                current: $drawerDetent
            ) {
                TimelineDrawerContent(selectedDayIndex: $selectedDayIndex)
                    .environmentObject(store)
            }
        }
        .onAppear {
            fitCamera()
        }
    }

    private func fitCamera() {
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
}
