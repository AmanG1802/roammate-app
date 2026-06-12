import Foundation

/// Wire format for /api/tutorial/* — see backend/app/api/endpoints/tutorial.py.
struct TutorialState: Decodable {
    let status: String         // not_started | in_progress | completed | skipped
    let step: Int
    let tripId: Int?
    let platform: String       // "ios" | "web"

    enum CodingKeys: String, CodingKey {
        case status, step, platform
        case tripId = "trip_id"
    }
}

private struct StepBody: Encodable { let step: Int }

enum TutorialService {
    static func status() async throws -> TutorialState {
        try await APIClient.shared.request("/tutorial/status")
    }

    static func start() async throws -> TutorialState {
        try await APIClient.shared.request("/tutorial/start", method: "POST")
    }

    static func setStep(_ step: Int) async throws -> TutorialState {
        try await APIClient.shared.request(
            "/tutorial/step", method: "PATCH", body: StepBody(step: step)
        )
    }

    static func skip() async throws -> TutorialState {
        try await APIClient.shared.request("/tutorial/skip", method: "POST")
    }

    static func complete() async throws -> TutorialState {
        try await APIClient.shared.request("/tutorial/complete", method: "POST")
    }

    static func replay() async throws -> TutorialState {
        try await APIClient.shared.request("/tutorial/replay", method: "POST")
    }

    // Resets to not_started (deletes trip, clears progress) so the Welcome
    // banner shows again on iOS. The next /start seeds a fresh tutorial trip.
    static func reset() async throws -> TutorialState {
        try await APIClient.shared.request("/tutorial/reset", method: "POST")
    }

    static func deleteTrip() async throws -> TutorialState {
        try await APIClient.shared.request("/tutorial/trip", method: "DELETE")
    }
}
