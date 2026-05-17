import Foundation
import CoreLocation

enum MapService {
    /// Convenience wrapper if/when the backend exposes a combined markers
    /// endpoint. For now, callers can build markers from Events + IdeaBinItems
    /// they already have in their store.
    static func buildMarkers(events: [Event], ideas: [IdeaBinItem]) -> [MapMarker] {
        var markers: [MapMarker] = []
        for e in events {
            guard let lat = e.lat, let lng = e.lng else { continue }
            markers.append(MapMarker(
                id: e.id, title: e.title, lat: lat, lng: lng,
                category: e.category, source: "timeline"
            ))
        }
        for i in ideas {
            guard let lat = i.lat, let lng = i.lng else { continue }
            markers.append(MapMarker(
                id: i.id, title: i.title, lat: lat, lng: lng,
                category: i.category, source: "idea_bin"
            ))
        }
        return markers
    }

    /// Local geocoding via CoreLocation. No backend call needed.
    static func geocode(_ query: String) async throws -> CLLocationCoordinate2D? {
        let placemarks = try await CLGeocoder().geocodeAddressString(query)
        return placemarks.first?.location?.coordinate
    }
}
