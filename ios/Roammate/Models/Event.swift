import Foundation

/// A scheduled timeline event on a trip. Replaces the prior `TimelineItem`
/// model and now matches the FastAPI `Event` Pydantic schema 1:1.
struct Event: Codable, Identifiable, Hashable {
    let id: Int
    let tripId: Int

    // Place fields (PlaceFields mixin)
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

    // Event-specific
    let locationName: String?
    let dayDate: String?       // "YYYY-MM-DD" — plain ISO date string
    let startTime: Date?       // full ISO-8601 datetime in UTC
    let endTime: Date?
    let isLocked: Bool
    let eventType: String?
    let sortOrder: Int
    let isSkipped: Bool

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
        case locationName = "location_name"
        case dayDate = "day_date"
        case startTime = "start_time"
        case endTime = "end_time"
        case isLocked = "is_locked"
        case eventType = "event_type"
        case sortOrder = "sort_order"
        case isSkipped = "is_skipped"
        case myVote = "my_vote"
    }
}

struct EventCreate: Encodable {
    let tripId: Int
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
    let locationName: String?
    let dayDate: String?
    let startTime: Date?
    let endTime: Date?
    let isLocked: Bool
    let eventType: String?
    let sortOrder: Int
    let isSkipped: Bool
    let sourceIdeaId: Int?

    enum CodingKeys: String, CodingKey {
        case title, description, category, lat, lng, address, rating, types
        case tripId = "trip_id"
        case placeId = "place_id"
        case photoUrl = "photo_url"
        case priceLevel = "price_level"
        case timeCategory = "time_category"
        case addedBy = "added_by"
        case locationName = "location_name"
        case dayDate = "day_date"
        case startTime = "start_time"
        case endTime = "end_time"
        case isLocked = "is_locked"
        case eventType = "event_type"
        case sortOrder = "sort_order"
        case isSkipped = "is_skipped"
        case sourceIdeaId = "source_idea_id"
    }
}

struct EventUpdate: Encodable {
    let title: String?
    let dayDate: String?
    let startTime: Date?
    let endTime: Date?
    let sortOrder: Int?
    let timeCategory: String?
    let isSkipped: Bool?

    enum CodingKeys: String, CodingKey {
        case title
        case dayDate = "day_date"
        case startTime = "start_time"
        case endTime = "end_time"
        case sortOrder = "sort_order"
        case timeCategory = "time_category"
        case isSkipped = "is_skipped"
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(title, forKey: .title)
        try container.encodeIfPresent(dayDate, forKey: .dayDate)
        try container.encodeIfPresent(startTime, forKey: .startTime)
        try container.encodeIfPresent(endTime, forKey: .endTime)
        try container.encodeIfPresent(sortOrder, forKey: .sortOrder)
        try container.encodeIfPresent(timeCategory, forKey: .timeCategory)
        try container.encodeIfPresent(isSkipped, forKey: .isSkipped)
    }
}

struct RippleRequest: Encodable {
    let deltaMinutes: Int
    let startFromTime: Date?

    enum CodingKeys: String, CodingKey {
        case deltaMinutes = "delta_minutes"
        case startFromTime = "start_from_time"
    }
}
