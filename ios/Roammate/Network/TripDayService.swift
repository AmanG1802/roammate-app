import Foundation

private struct TripDayCreatePayload: Encodable {
    let date: String
}

enum TripDayService {
    static func getDays(tripId: Int) async throws -> [TripDay] {
        try await APIClient.shared.request("/trips/\(tripId)/days")
    }

    static func addDay(tripId: Int, date: Date) async throws -> TripDay {
        try await APIClient.shared.request(
            "/trips/\(tripId)/days",
            method: "POST",
            body: TripDayCreatePayload(date: isoDate(date))
        )
    }

    /// `itemsAction` is "bin" (restore events to idea bin) or "delete" (permanent).
    static func deleteDay(tripId: Int, dayId: Int, itemsAction: String = "bin") async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/trips/\(tripId)/days/\(dayId)",
            method: "DELETE",
            query: ["items_action": itemsAction]
        )
    }

    private static func isoDate(_ date: Date) -> String {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .iso8601)
        f.timeZone = TimeZone(identifier: "UTC")
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: date)
    }
}
