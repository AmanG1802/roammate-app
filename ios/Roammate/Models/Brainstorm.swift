import Foundation

struct BrainstormItemOut: Codable, Identifiable, Hashable {
    let id: Int
    let tripId: Int
    let userId: Int

    let title: String
    let description: String?
    let category: String?
    let placeId: String?
    let lat: Double?
    let lng: Double?
    let address: String?
    let photoUrl: String?
    let rating: Double?
    let priceLevel: Int?
    let types: [String]?
    let timeCategory: String?
    let addedBy: String?
    let createdAt: Date?

    enum CodingKeys: String, CodingKey {
        case id, title, description, category, lat, lng, address, rating, types
        case tripId = "trip_id"
        case userId = "user_id"
        case placeId = "place_id"
        case photoUrl = "photo_url"
        case priceLevel = "price_level"
        case timeCategory = "time_category"
        case addedBy = "added_by"
        case createdAt = "created_at"
    }
}

struct BrainstormMessage: Codable, Identifiable, Hashable {
    let id: Int
    let role: String
    let content: String
    let createdAt: Date?

    enum CodingKeys: String, CodingKey {
        case id, role, content
        case createdAt = "created_at"
    }
}

struct BrainstormChatRequest: Encodable {
    let message: String
}

struct BrainstormChatResponse: Codable {
    let assistantMessage: BrainstormMessage
    let history: [BrainstormMessage]

    enum CodingKeys: String, CodingKey {
        case assistantMessage = "assistant_message"
        case history
    }
}

struct BrainstormExtractResponse: Codable {
    let items: [BrainstormItemOut]
    let enrichment: JSONValue?
}

struct BrainstormPromoteRequest: Encodable {
    let itemIds: [Int]?

    enum CodingKeys: String, CodingKey {
        case itemIds = "item_ids"
    }
}
