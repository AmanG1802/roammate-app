import Foundation
import MapKit
import SwiftUI
import CryptoKit

// MARK: - Models

struct RouteOverlay: Identifiable {
    let id: Int
    let polyline: MKPolyline
    let duration: TimeInterval
    let distance: CLLocationDistance
    let fromEventId: Int
    let toEventId: Int
    let color: Color
}

struct RouteLegDTO: Codable {
    let fromEventId: String
    let toEventId: String
    let durationS: Int
    let distanceM: Int

    enum CodingKeys: String, CodingKey {
        case fromEventId = "from_event_id"
        case toEventId = "to_event_id"
        case durationS = "duration_s"
        case distanceM = "distance_m"
    }
}

struct UnroutableEventDTO: Codable {
    let eventId: String
    let reason: String

    enum CodingKeys: String, CodingKey {
        case eventId = "event_id"
        case reason
    }
}

struct RouteResponseDTO: Codable {
    let encodedPolyline: String?
    let legs: [RouteLegDTO]
    let totalDurationS: Int
    let totalDistanceM: Int
    let orderedEventIds: [String]
    let unroutable: [UnroutableEventDTO]
    let reason: String?
    let waypointFingerprint: String?
    let computedAt: Date?
    let isStale: Bool

    enum CodingKeys: String, CodingKey {
        case encodedPolyline = "encoded_polyline"
        case legs
        case totalDurationS = "total_duration_s"
        case totalDistanceM = "total_distance_m"
        case orderedEventIds = "ordered_event_ids"
        case unroutable
        case reason
        case waypointFingerprint = "waypoint_fingerprint"
        case computedAt = "computed_at"
        case isStale = "is_stale"
    }
}

struct RouteSaveRequestDTO: Codable {
    let dayDate: String
    let encodedPolyline: String?
    let legs: [RouteLegDTO]
    let totalDurationS: Int
    let totalDistanceM: Int
    let orderedEventIds: [String]
    let unroutable: [UnroutableEventDTO]
    let waypointFingerprint: String?

    enum CodingKeys: String, CodingKey {
        case dayDate = "day_date"
        case encodedPolyline = "encoded_polyline"
        case legs
        case totalDurationS = "total_duration_s"
        case totalDistanceM = "total_distance_m"
        case orderedEventIds = "ordered_event_ids"
        case unroutable
        case waypointFingerprint = "waypoint_fingerprint"
    }
}

// MARK: - Leg colors (matches web LEG_COLORS)

enum RouteLegColors {
    static let palette: [Color] = [
        Color(red: 79/255, green: 70/255, blue: 229/255),   // indigo
        Color(red: 220/255, green: 38/255, blue: 38/255),   // red
        Color(red: 5/255, green: 150/255, blue: 105/255),   // emerald
        Color(red: 217/255, green: 119/255, blue: 6/255),   // amber
        Color(red: 124/255, green: 58/255, blue: 237/255),  // violet
        Color(red: 8/255, green: 145/255, blue: 178/255),   // cyan
        Color(red: 192/255, green: 38/255, blue: 211/255),  // fuchsia
        Color(red: 37/255, green: 99/255, blue: 235/255),   // blue
    ]

    static func color(for index: Int) -> Color {
        palette[index % palette.count]
    }
}

// MARK: - RouteService

enum RouteService {

    // MARK: - Fetch stored route from backend

    static func fetchStoredRoute(tripId: Int, dayDate: String) async throws -> RouteResponseDTO? {
        let response: RouteResponseDTO? = try? await APIClient.shared.request(
            "/trips/\(tripId)/route",
            query: ["day_date": dayDate]
        )
        return response
    }

    // MARK: - Save client-computed route to backend

    static func saveRoute(tripId: Int, request: RouteSaveRequestDTO) async throws -> RouteResponseDTO {
        try await APIClient.shared.request(
            "/trips/\(tripId)/route/save",
            method: "POST",
            body: request
        )
    }

    // MARK: - Compute route via MKDirections

    static func computeRoute(events: [Event]) async -> (overlays: [RouteOverlay], response: RouteSaveRequestDTO?) {
        let routable = events
            .filter { !$0.isSkipped && $0.lat != nil && $0.lng != nil }
            .sorted { a, b in
                if let at = a.startTime, let bt = b.startTime {
                    return at < bt
                }
                return a.sortOrder < b.sortOrder
            }

        guard routable.count >= 2 else { return ([], nil) }

        var overlays: [RouteOverlay] = []
        var legs: [RouteLegDTO] = []
        var allCoords: [CLLocationCoordinate2D] = []
        var totalDuration = 0
        var totalDistance = 0

        for i in 0..<(routable.count - 1) {
            let from = routable[i]
            let to = routable[i + 1]

            guard let fromLat = from.lat, let fromLng = from.lng,
                  let toLat = to.lat, let toLng = to.lng else { continue }

            let source = MKMapItem(placemark: MKPlacemark(
                coordinate: CLLocationCoordinate2D(latitude: fromLat, longitude: fromLng)
            ))
            let destination = MKMapItem(placemark: MKPlacemark(
                coordinate: CLLocationCoordinate2D(latitude: toLat, longitude: toLng)
            ))

            let request = MKDirections.Request()
            request.source = source
            request.destination = destination
            request.transportType = .automobile

            do {
                let directions = MKDirections(request: request)
                let response = try await directions.calculate()

                if let route = response.routes.first {
                    let color = RouteLegColors.color(for: i)
                    let overlay = RouteOverlay(
                        id: i,
                        polyline: route.polyline,
                        duration: route.expectedTravelTime,
                        distance: route.distance,
                        fromEventId: from.id,
                        toEventId: to.id,
                        color: color
                    )
                    overlays.append(overlay)

                    let leg = RouteLegDTO(
                        fromEventId: String(from.id),
                        toEventId: String(to.id),
                        durationS: Int(route.expectedTravelTime),
                        distanceM: Int(route.distance)
                    )
                    legs.append(leg)

                    totalDuration += Int(route.expectedTravelTime)
                    totalDistance += Int(route.distance)

                    // Collect coordinates for polyline encoding
                    let points = route.polyline.points()
                    let count = route.polyline.pointCount
                    for j in 0..<count {
                        allCoords.append(points[j].coordinate)
                    }
                }
            } catch {
                // Skip this leg if MKDirections fails
                continue
            }
        }

        let encodedPolyline = encodePolyline(allCoords)
        let orderedIds = routable.map { String($0.id) }

        let unroutable = events
            .filter { !$0.isSkipped && ($0.lat == nil || $0.lng == nil) }
            .map { UnroutableEventDTO(eventId: String($0.id), reason: "no_location") }

        let saveRequest = RouteSaveRequestDTO(
            dayDate: routable.first?.dayDate ?? "",
            encodedPolyline: encodedPolyline,
            legs: legs,
            totalDurationS: totalDuration,
            totalDistanceM: totalDistance,
            orderedEventIds: orderedIds,
            unroutable: unroutable,
            waypointFingerprint: nil
        )

        return (overlays, saveRequest)
    }

    // MARK: - Decode stored polyline into MKPolyline segments

    static func decodeStoredRoute(response: RouteResponseDTO, events: [Event]) -> [RouteOverlay] {
        guard let encoded = response.encodedPolyline, !encoded.isEmpty else { return [] }

        let coords = decodePolyline(encoded)
        guard coords.count >= 2 else { return [] }

        // If only one leg or no legs, render the whole polyline as one overlay
        if response.legs.count <= 1 {
            let polyline = MKPolyline(coordinates: coords, count: coords.count)
            let leg = response.legs.first
            return [RouteOverlay(
                id: 0,
                polyline: polyline,
                duration: TimeInterval(leg?.durationS ?? 0),
                distance: CLLocationDistance(leg?.distanceM ?? 0),
                fromEventId: Int(leg?.fromEventId ?? "0") ?? 0,
                toEventId: Int(leg?.toEventId ?? "0") ?? 0,
                color: RouteLegColors.color(for: 0)
            )]
        }

        // Build event position lookup
        let posById = Dictionary(
            uniqueKeysWithValues: events
                .filter { $0.lat != nil && $0.lng != nil }
                .map { ($0.id, CLLocationCoordinate2D(latitude: $0.lat!, longitude: $0.lng!)) }
        )

        // Build waypoint list from legs
        var waypointIds: [Int] = []
        if let first = response.legs.first {
            waypointIds.append(Int(first.fromEventId) ?? 0)
        }
        for leg in response.legs {
            waypointIds.append(Int(leg.toEventId) ?? 0)
        }

        let waypoints = waypointIds.compactMap { posById[$0] }
        guard waypoints.count >= 2 else { return [] }

        // Find nearest polyline point to each waypoint
        func findNearest(target: CLLocationCoordinate2D, startFrom: Int) -> Int {
            var bestIdx = startFrom
            var bestDist = Double.infinity
            for j in startFrom..<coords.count {
                let d = pow(coords[j].latitude - target.latitude, 2) +
                         pow(coords[j].longitude - target.longitude, 2)
                if d < bestDist { bestDist = d; bestIdx = j }
            }
            return bestIdx
        }

        var splitIndices = [0]
        var searchFrom = 0
        for w in 1..<(waypoints.count - 1) {
            let idx = findNearest(target: waypoints[w], startFrom: searchFrom)
            splitIndices.append(idx)
            searchFrom = idx
        }
        splitIndices.append(coords.count - 1)

        var overlays: [RouteOverlay] = []
        for (i, leg) in response.legs.enumerated() {
            guard i < splitIndices.count - 1 else { break }
            let segStart = splitIndices[i]
            let segEnd = splitIndices[i + 1]
            guard segEnd > segStart else { continue }

            let segCoords = Array(coords[segStart...segEnd])
            let polyline = MKPolyline(coordinates: segCoords, count: segCoords.count)

            overlays.append(RouteOverlay(
                id: i,
                polyline: polyline,
                duration: TimeInterval(leg.durationS),
                distance: CLLocationDistance(leg.distanceM),
                fromEventId: Int(leg.fromEventId) ?? 0,
                toEventId: Int(leg.toEventId) ?? 0,
                color: RouteLegColors.color(for: i)
            ))
        }

        return overlays
    }

    // MARK: - Google-format polyline encoding

    static func encodePolyline(_ coordinates: [CLLocationCoordinate2D]) -> String {
        var result = ""
        var prevLat = 0
        var prevLng = 0

        for coord in coordinates {
            let iLat = Int(round(coord.latitude * 1e5))
            let iLng = Int(round(coord.longitude * 1e5))
            result += encodeValue(iLat - prevLat)
            result += encodeValue(iLng - prevLng)
            prevLat = iLat
            prevLng = iLng
        }
        return result
    }

    private static func encodeValue(_ value: Int) -> String {
        var v = value < 0 ? ~(value << 1) : (value << 1)
        var result = ""
        while v >= 0x20 {
            result.append(Character(UnicodeScalar((0x20 | (v & 0x1F)) + 63)!))
            v >>= 5
        }
        result.append(Character(UnicodeScalar(v + 63)!))
        return result
    }

    // MARK: - Google-format polyline decoding

    static func decodePolyline(_ encoded: String) -> [CLLocationCoordinate2D] {
        var coords: [CLLocationCoordinate2D] = []
        let chars = Array(encoded.unicodeScalars)
        var index = 0
        var lat = 0
        var lng = 0

        while index < chars.count {
            var result = 0
            var shift = 0
            var b: Int
            repeat {
                b = Int(chars[index].value) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
            } while b >= 0x20

            let dLat = (result & 1) != 0 ? ~(result >> 1) : (result >> 1)
            lat += dLat

            result = 0
            shift = 0
            repeat {
                b = Int(chars[index].value) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
            } while b >= 0x20

            let dLng = (result & 1) != 0 ? ~(result >> 1) : (result >> 1)
            lng += dLng

            coords.append(CLLocationCoordinate2D(
                latitude: Double(lat) / 1e5,
                longitude: Double(lng) / 1e5
            ))
        }
        return coords
    }

    // MARK: - Fingerprint (matches backend compute_waypoint_fingerprint)

    static func computeFingerprint(events: [Event]) -> String {
        let routable = events
            .filter { !$0.isSkipped && ($0.placeId != nil || ($0.lat != nil && $0.lng != nil)) }
            .sorted { a, b in
                if let at = a.startTime, let bt = b.startTime { return at < bt }
                return a.sortOrder < b.sortOrder
            }

        var parts: [[String]] = []
        let isoFmt = ISO8601DateFormatter()
        for e in routable {
            parts.append([
                String(e.id),
                e.placeId ?? "",
                e.lat.map { String(format: "%.5f", $0) } ?? "",
                e.lng.map { String(format: "%.5f", $0) } ?? "",
                e.startTime.map { isoFmt.string(from: $0) } ?? "",
                e.endTime.map { isoFmt.string(from: $0) } ?? "",
            ])
        }

        guard let data = try? JSONSerialization.data(withJSONObject: parts) else {
            return "empty"
        }
        return data.sha256Prefix(length: 16)
    }
}

// MARK: - SHA-256 helper

private extension Data {
    func sha256Prefix(length: Int) -> String {
        let hash = SHA256.hash(data: self)
        return hash.prefix(length / 2).map { String(format: "%02x", $0) }.joined()
    }
}
