import Foundation

/// One generated brainstorm idea inside a plan-trip preview.
/// Matches FastAPI `BrainstormItemBase` (PlaceFields shape).
struct BrainstormItem: Codable, Identifiable, Hashable {
    var id: String { (placeId ?? "") + title }

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

    enum CodingKeys: String, CodingKey {
        case title, description, category, lat, lng, address, rating, types
        case placeId = "place_id"
        case photoUrl = "photo_url"
        case priceLevel = "price_level"
        case timeCategory = "time_category"
        case addedBy = "added_by"
    }
}

struct PlanTripRequest: Encodable {
    let prompt: String
    let timezone: String?
}

struct PlanTripPreview: Codable {
    let tripName: String
    let startDate: Date?
    let durationDays: Int
    let items: [BrainstormItem]
    let userOutput: String?
    /// IANA timezone inferred from the destination on the backend
    /// (Google Time Zone API). nil → fall back to device tz.
    let timezone: String?

    enum CodingKeys: String, CodingKey {
        case tripName = "trip_name"
        case startDate = "start_date"
        case durationDays = "duration_days"
        case items
        case userOutput = "user_output"
        case timezone
    }
}

struct BrainstormBulkRequest: Encodable {
    let items: [BrainstormItem]
}
