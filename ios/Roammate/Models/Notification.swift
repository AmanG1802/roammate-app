import Foundation

struct ActorSummary: Codable, Hashable {
    let id: Int
    let name: String?
    let email: String?
}

/// In-app notification record. Named `AppNotification` so it doesn't shadow
/// Foundation's `Notification` (used by NotificationCenter).
struct AppNotification: Codable, Identifiable, Hashable {
    let id: Int
    let type: String
    let payload: [String: JSONValue]
    let tripId: Int?
    let groupId: Int?
    let actor: ActorSummary?
    let readAt: Date?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, type, payload, actor
        case tripId = "trip_id"
        case groupId = "group_id"
        case readAt = "read_at"
        case createdAt = "created_at"
    }

    var isRead: Bool { readAt != nil }
}

struct UnreadCount: Codable {
    let unread: Int
}
