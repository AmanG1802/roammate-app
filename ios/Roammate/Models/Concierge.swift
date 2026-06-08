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

/// How a confirmable action card is currently rendered.
enum ActionStatus: String { case pending, confirmed, cancelled }

/// The rich payload a chat turn renders. `.text` is a plain bubble; the rest
/// drive the inline cards (place carousel, day summary, what's-next, ripple
/// result, error). Mirrors the web `MessageType` union.
enum ConciergeCard {
    case text
    case actionCard
    case placeCards([PlaceCard])
    case summary(TodaySummaryResponse)
    case whatsNext(WhatsNextResponse)
    case rippleResult(shifted: Int, minutes: Int)
    case error(retryQuery: String?)
}

/// A single chat turn rendered in the concierge UI.
struct ChatMessage: Identifiable {
    let id: UUID
    let role: Role
    let text: String
    let card: ConciergeCard
    var status: ActionStatus?
    let intent: ConciergeIntent?
    let params: [String: JSONValue]
    let timestamp: Date

    enum Role: String { case user, assistant }

    init(
        id: UUID = UUID(),
        role: Role,
        text: String = "",
        card: ConciergeCard = .text,
        status: ActionStatus? = nil,
        intent: ConciergeIntent? = nil,
        params: [String: JSONValue] = [:],
        timestamp: Date = Date()
    ) {
        self.id = id
        self.role = role
        self.text = text
        self.card = card
        self.status = status
        self.intent = intent
        self.params = params
        self.timestamp = timestamp
    }
}

/// Which full-screen destination the Concierge is showing over the chat.
/// `Identifiable` so it can drive `.fullScreenCover(item:)`.
enum ConciergeDetail: String, Identifiable, Hashable {
    case map, timeline
    var id: String { rawValue }
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

// MARK: - JSONValue helpers (concierge event payloads)

extension JSONValue {
    var doubleValue: Double? {
        switch self {
        case .double(let d): return d
        case .int(let i): return Double(i)
        case .string(let s): return Double(s)
        default: return nil
        }
    }

    var stringArray: [String]? { arrayValue?.compactMap { $0.stringValue } }
}

extension Event {
    /// Build an `Event` from a backend concierge event dict (the shape returned
    /// by `whats-next` / `today-summary` / `execute.updated_events`, produced by
    /// `_event_dict_for_response`). Those payloads omit vote tallies, so we
    /// default `up`/`down`/`myVote` to 0.
    init?(conciergeJSON j: JSONValue) {
        guard let id = j["id"]?.intValue,
              let title = j["title"]?.stringValue else { return nil }
        self.init(
            id: id,
            tripId: j["trip_id"]?.intValue ?? 0,
            title: title,
            description: j["description"]?.stringValue,
            category: j["category"]?.stringValue,
            placeId: j["place_id"]?.stringValue,
            lat: j["lat"]?.doubleValue,
            lng: j["lng"]?.doubleValue,
            address: j["address"]?.stringValue,
            photoUrl: j["photo_url"]?.stringValue,
            rating: j["rating"]?.doubleValue,
            priceLevel: j["price_level"]?.intValue,
            types: j["types"]?.stringArray,
            timeCategory: j["time_category"]?.stringValue,
            addedBy: j["added_by"]?.stringValue,
            locationName: j["location_name"]?.stringValue,
            dayDate: j["day_date"]?.stringValue,
            startTime: (j["start_time"]?.stringValue).flatMap { TimeOfDay($0) },
            endTime: (j["end_time"]?.stringValue).flatMap { TimeOfDay($0) },
            isLocked: j["is_locked"]?.boolValue ?? false,
            eventType: j["event_type"]?.stringValue,
            sortOrder: j["sort_order"]?.intValue ?? 0,
            isSkipped: j["is_skipped"]?.boolValue ?? false,
            up: 0, down: 0, myVote: 0
        )
    }
}
