import Foundation

struct MapMarker: Codable, Identifiable, Hashable {
    let id: Int
    let title: String
    let lat: Double
    let lng: Double
    let category: String?
    let source: String      // "timeline" | "idea_bin"
}
