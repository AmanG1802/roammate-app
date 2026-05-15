import Foundation

enum ConciergeIntent: String, Codable {
    case shiftTimeline = "shift_timeline"
    case moveEvent = "move_event"
    case addEvent = "add_event"
    case skipEvent = "skip_event"
    case explainPlan = "explain_plan"
    case findNearby = "find_nearby"
    case chatOnly = "chat_only"
}

/// A single chat turn rendered in the concierge UI.
struct ChatMessage: Identifiable, Hashable {
    let id: UUID
    let role: Role
    let text: String
    let intent: ConciergeIntent?
    let params: [String: JSONValue]
    let requiresConfirmation: Bool
    let messageType: String
    let timestamp: Date

    enum Role: String, Hashable { case user, assistant }

    init(
        id: UUID = UUID(),
        role: Role,
        text: String,
        intent: ConciergeIntent? = nil,
        params: [String: JSONValue] = [:],
        requiresConfirmation: Bool = false,
        messageType: String = "text",
        timestamp: Date = Date()
    ) {
        self.id = id
        self.role = role
        self.text = text
        self.intent = intent
        self.params = params
        self.requiresConfirmation = requiresConfirmation
        self.messageType = messageType
        self.timestamp = timestamp
    }
}

struct ConciergeChatRequest: Encodable {
    let message: String
}

struct ConciergeChatResponse: Codable {
    let intent: ConciergeIntent
    let userMessage: String
    let params: [String: JSONValue]
    let requiresConfirmation: Bool
    let messageType: String
    let enrichment: JSONValue?

    enum CodingKeys: String, CodingKey {
        case intent, params, enrichment
        case userMessage = "user_message"
        case requiresConfirmation = "requires_confirmation"
        case messageType = "message_type"
    }
}

struct ExecuteRequest: Encodable {
    let intent: String
    let params: [String: JSONValue]
}

struct ExecuteResponse: Codable {
    let success: Bool
    let message: String
    let updatedEvents: [JSONValue]?
    let newEvent: JSONValue?

    enum CodingKeys: String, CodingKey {
        case success, message
        case updatedEvents = "updated_events"
        case newEvent = "new_event"
    }
}

struct FindNearbyRequest: Encodable {
    let query: String
    let lat: Double
    let lng: Double
    let category: String?
    let limit: Int
}

struct PlaceCard: Codable, Identifiable, Hashable {
    var id: String { placeId }

    // PlaceFields (place_id, lat, lng required for search results)
    let title: String
    let description: String?
    let category: String?
    let placeId: String
    let lat: Double
    let lng: Double
    let address: String?
    let photoUrl: String?
    let rating: Double?
    let priceLevel: Int?
    let types: [String]?
    let timeCategory: String?
    let addedBy: String?

    // Travel info
    let travelTimeS: Int?
    let distanceM: Int?

    enum CodingKeys: String, CodingKey {
        case title, description, category, lat, lng, address, rating, types
        case placeId = "place_id"
        case photoUrl = "photo_url"
        case priceLevel = "price_level"
        case timeCategory = "time_category"
        case addedBy = "added_by"
        case travelTimeS = "travel_time_s"
        case distanceM = "distance_m"
    }
}

struct FindNearbyResponse: Codable {
    let places: [PlaceCard]
    let enrichment: JSONValue?
}

struct SkipEventRequest: Encodable {
    let eventId: Int

    enum CodingKeys: String, CodingKey {
        case eventId = "event_id"
    }
}

struct WhatsNextResponse: Codable {
    let currentEvent: JSONValue?
    let nextEvent: JSONValue?
    let timeUntilNext: String?
    let travelTimeToNext: Int?

    enum CodingKeys: String, CodingKey {
        case currentEvent = "current_event"
        case nextEvent = "next_event"
        case timeUntilNext = "time_until_next"
        case travelTimeToNext = "travel_time_to_next"
    }
}

struct TodaySummaryEvent: Codable, Hashable {
    let event: JSONValue
    let status: String   // "upcoming" | "ongoing" | "completed" | "skipped"
}

struct TodaySummaryResponse: Codable {
    let date: String
    let totalEvents: Int
    let completed: Int
    let upcoming: Int
    let skipped: Int
    let events: [TodaySummaryEvent]

    enum CodingKeys: String, CodingKey {
        case date, completed, upcoming, skipped, events
        case totalEvents = "total_events"
    }
}
