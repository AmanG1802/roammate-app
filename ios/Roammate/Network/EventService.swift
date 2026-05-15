import Foundation

enum EventService {
    /// Fetch events for a trip, optionally scoped to a single day.
    static func getEvents(tripId: Int, dayDate: Date? = nil) async throws -> [Event] {
        let dateString = dayDate.map { isoDate($0) }
        return try await APIClient.shared.request(
            "/events/",
            query: ["trip_id": String(tripId), "day_date": dateString]
        )
    }

    static func createEvent(_ event: EventCreate) async throws -> Event {
        try await APIClient.shared.request("/events/", method: "POST", body: event)
    }

    static func updateEvent(id: Int, update: EventUpdate) async throws -> Event {
        try await APIClient.shared.request("/events/\(id)", method: "PATCH", body: update)
    }

    static func deleteEvent(id: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/events/\(id)", method: "DELETE"
        )
    }

    /// Move a timeline event back to the idea bin.
    static func moveToBin(eventId: Int) async throws -> IdeaBinItem {
        try await APIClient.shared.request("/events/\(eventId)/move-to-bin", method: "POST")
    }

    /// Smart-shift the timeline by a delta (in minutes).
    static func ripple(tripId: Int, request: RippleRequest) async throws -> [Event] {
        try await APIClient.shared.request(
            "/events/ripple/\(tripId)", method: "POST", body: request
        )
    }

    // MARK: - Helpers

    private static func isoDate(_ date: Date) -> String {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .iso8601)
        f.timeZone = TimeZone(identifier: "UTC")
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: date)
    }
}
