import Foundation

enum ConciergeService {
    static func chat(tripId: Int, message: String) async throws -> ConciergeChatResponse {
        try await APIClient.shared.request(
            "/concierge/\(tripId)/chat",
            method: "POST",
            body: ConciergeChatRequest(message: message)
        )
    }

    static func execute(tripId: Int, intent: String, params: [String: JSONValue]) async throws -> ExecuteResponse {
        try await APIClient.shared.request(
            "/concierge/\(tripId)/execute",
            method: "POST",
            body: ExecuteRequest(intent: intent, params: params)
        )
    }

    static func findNearby(tripId: Int, request: FindNearbyRequest) async throws -> FindNearbyResponse {
        try await APIClient.shared.request(
            "/concierge/\(tripId)/find-nearby", method: "POST", body: request
        )
    }

    static func skipEvent(tripId: Int, eventId: Int) async throws -> ExecuteResponse {
        try await APIClient.shared.request(
            "/concierge/\(tripId)/skip-event",
            method: "POST",
            body: SkipEventRequest(eventId: eventId)
        )
    }

    static func whatsNext(tripId: Int) async throws -> WhatsNextResponse {
        try await APIClient.shared.request("/concierge/\(tripId)/whats-next")
    }

    static func todaySummary(tripId: Int) async throws -> TodaySummaryResponse {
        try await APIClient.shared.request("/concierge/\(tripId)/today-summary")
    }

    /// 3.1: the shared, trip-wide thread (all members read; `canWrite` gates posting).
    static func messages(tripId: Int) async throws -> ConciergeThreadResponse {
        try await APIClient.shared.request("/concierge/\(tripId)/messages")
    }

    /// 3.8: revert the most recent not-yet-undone action.
    static func undo(tripId: Int) async throws -> UndoResponse {
        try await APIClient.shared.request("/concierge/\(tripId)/undo", method: "POST")
    }
}
