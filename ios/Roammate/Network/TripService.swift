import Foundation

enum TripService {
    // MARK: - Trip CRUD

    static func getTrips() async throws -> [Trip] {
        try await APIClient.shared.request("/trips/")
    }

    static func getTrip(id: Int) async throws -> Trip {
        try await APIClient.shared.request("/trips/\(id)")
    }

    static func createTrip(_ trip: TripCreate) async throws -> Trip {
        try await APIClient.shared.request("/trips/", method: "POST", body: trip)
    }

    static func updateTrip(id: Int, update: TripUpdate) async throws -> Trip {
        try await APIClient.shared.request("/trips/\(id)", method: "PATCH", body: update)
    }

    static func deleteTrip(id: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/trips/\(id)", method: "DELETE"
        )
    }
}
