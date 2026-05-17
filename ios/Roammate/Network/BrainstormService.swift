import Foundation

enum BrainstormService {
    static func getItems(tripId: Int) async throws -> [BrainstormItemOut] {
        try await APIClient.shared.request("/trips/\(tripId)/brainstorm/items")
    }

    static func getMessages(tripId: Int) async throws -> [BrainstormMessage] {
        try await APIClient.shared.request("/trips/\(tripId)/brainstorm/messages")
    }

    static func chat(tripId: Int, message: String) async throws -> BrainstormChatResponse {
        try await APIClient.shared.request(
            "/trips/\(tripId)/brainstorm/chat",
            method: "POST",
            body: BrainstormChatRequest(message: message),
            retries: 0
        )
    }

    static func extract(tripId: Int) async throws -> BrainstormExtractResponse {
        try await APIClient.shared.request(
            "/trips/\(tripId)/brainstorm/extract",
            method: "POST",
            retries: 0
        )
    }

    static func promote(tripId: Int, itemIds: [Int]?) async throws -> [IdeaBinItem] {
        try await APIClient.shared.request(
            "/trips/\(tripId)/brainstorm/promote",
            method: "POST",
            body: BrainstormPromoteRequest(itemIds: itemIds)
        )
    }

    static func deleteItem(tripId: Int, itemId: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/trips/\(tripId)/brainstorm/items/\(itemId)", method: "DELETE"
        )
    }

    static func clearAll(tripId: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/trips/\(tripId)/brainstorm/items", method: "DELETE"
        )
    }

    /// Backfill the Plan-Trip conversation as the trip's first Brainstorm history.
    /// Idempotent on the server (returns 409 if history already exists).
    @discardableResult
    static func seedMessages(tripId: Int, messages: [BrainstormSeedMessage]) async throws -> BrainstormSeedResponse {
        try await APIClient.shared.request(
            "/trips/\(tripId)/brainstorm/messages/seed",
            method: "POST",
            body: BrainstormSeedRequest(messages: messages)
        )
    }
}

struct BrainstormSeedMessage: Encodable {
    let role: String
    let content: String
}

struct BrainstormSeedRequest: Encodable {
    let messages: [BrainstormSeedMessage]
}

struct BrainstormSeedResponse: Decodable {
    let seeded: Int
}
