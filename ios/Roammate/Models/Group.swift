import Foundation

/// Roles on a Group. Backend values: "admin", "member".
enum GroupRole: String, Codable {
    case admin
    case member
}

struct TravelGroup: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let ownerId: Int
    let createdAt: Date
    let myRole: String
    let memberCount: Int
    let tripCount: Int

    enum CodingKeys: String, CodingKey {
        case id, name
        case ownerId = "owner_id"
        case createdAt = "created_at"
        case myRole = "my_role"
        case memberCount = "member_count"
        case tripCount = "trip_count"
    }
}

struct GroupDetail: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let ownerId: Int
    let createdAt: Date
    let myRole: String

    enum CodingKeys: String, CodingKey {
        case id, name
        case ownerId = "owner_id"
        case createdAt = "created_at"
        case myRole = "my_role"
    }
}

struct GroupCreate: Encodable {
    let name: String
}

struct GroupUpdate: Encodable {
    let name: String?
}

struct GroupInviteRequest: Encodable {
    let email: String
    let role: String
}

struct GroupSummary: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
}

struct GroupInviterSummary: Codable, Hashable {
    let name: String
    let email: String
}

struct GroupInvitation: Codable, Identifiable, Hashable {
    let id: Int
    let groupId: Int
    let role: String
    let group: GroupSummary
    let inviter: GroupInviterSummary?

    enum CodingKeys: String, CodingKey {
        case id, role, group, inviter
        case groupId = "group_id"
    }
}

struct GroupTripSummary: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let startDate: Date?

    enum CodingKeys: String, CodingKey {
        case id, name
        case startDate = "start_date"
    }
}

struct GroupMember: Codable, Identifiable, Hashable {
    let id: Int
    let groupId: Int
    let userId: Int
    let role: String
    let status: String
    let user: MemberUser

    enum CodingKeys: String, CodingKey {
        case id, role, status, user
        case groupId = "group_id"
        case userId = "user_id"
    }
}
