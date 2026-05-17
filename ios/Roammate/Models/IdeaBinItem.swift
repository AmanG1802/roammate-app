import Foundation

struct IdeaBinItem: Codable, Identifiable, Hashable {
    let id: Int
    let tripId: Int

    // Place fields
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

    // Optional scheduling hints
    let startTime: Date?
    let endTime: Date?

    // Vote tallies
    let up: Int
    let down: Int
    let myVote: Int

    enum CodingKeys: String, CodingKey {
        case id, title, description, category, lat, lng, address, rating, types, up, down
        case tripId = "trip_id"
        case placeId = "place_id"
        case photoUrl = "photo_url"
        case priceLevel = "price_level"
        case timeCategory = "time_category"
        case addedBy = "added_by"
        case startTime = "start_time"
        case endTime = "end_time"
        case myVote = "my_vote"
    }
}

struct IdeaUpdate: Encodable {
    let title: String?
    let startTime: Date?
    let endTime: Date?
    let timeCategory: String?

    enum CodingKeys: String, CodingKey {
        case title
        case startTime = "start_time"
        case endTime = "end_time"
        case timeCategory = "time_category"
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(title, forKey: .title)
        try container.encodeIfPresent(startTime, forKey: .startTime)
        try container.encodeIfPresent(endTime, forKey: .endTime)
        try container.encodeIfPresent(timeCategory, forKey: .timeCategory)
    }
}

struct IngestRequest: Encodable {
    let text: String
    let sourceUrl: String?

    enum CodingKeys: String, CodingKey {
        case text
        case sourceUrl = "source_url"
    }
}
