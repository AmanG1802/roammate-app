import Foundation

/// Roles on a Trip. Backend values: "admin", "view_only", "view_with_vote".
enum TripRole: String, Codable {
    case admin
    case viewOnly = "view_only"
    case viewWithVote = "view_with_vote"
}

struct MemberUser: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let email: String
    let avatarUrl: String?

    enum CodingKeys: String, CodingKey {
        case id, name, email
        case avatarUrl = "avatar_url"
    }
}

struct TripMember: Codable, Identifiable, Hashable {
    let id: Int
    let tripId: Int
    let userId: Int
    let role: String          // "admin" | "view_only" | "view_with_vote"
    let status: String        // "accepted" | "invited"
    let user: MemberUser

    enum CodingKeys: String, CodingKey {
        case id, role, status, user
        case tripId = "trip_id"
        case userId = "user_id"
    }

    var roleEnum: TripRole? { TripRole(rawValue: role) }
}

struct InviteRequest: Encodable {
    let email: String
    let role: String
}

struct RoleUpdateRequest: Encodable {
    let role: String
}
