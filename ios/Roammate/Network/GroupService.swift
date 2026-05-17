import Foundation

enum GroupService {
    // MARK: - Group CRUD

    static func getGroups() async throws -> [TravelGroup] {
        try await APIClient.shared.request("/groups/")
    }

    static func createGroup(name: String) async throws -> GroupDetail {
        try await APIClient.shared.request(
            "/groups/", method: "POST", body: GroupCreate(name: name)
        )
    }

    static func getGroup(id: Int) async throws -> GroupDetail {
        try await APIClient.shared.request("/groups/\(id)")
    }

    static func updateGroup(id: Int, name: String?) async throws -> GroupDetail {
        try await APIClient.shared.request(
            "/groups/\(id)", method: "PATCH", body: GroupUpdate(name: name)
        )
    }

    static func deleteGroup(id: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/groups/\(id)", method: "DELETE"
        )
    }

    // MARK: - Members

    static func getGroupMembers(groupId: Int) async throws -> [GroupMember] {
        try await APIClient.shared.request("/groups/\(groupId)/members")
    }

    static func inviteToGroup(groupId: Int, email: String, role: String) async throws -> GroupMember {
        try await APIClient.shared.request(
            "/groups/\(groupId)/invite",
            method: "POST",
            body: GroupInviteRequest(email: email, role: role)
        )
    }

    static func updateGroupRole(groupId: Int, memberId: Int, role: String) async throws -> GroupMember {
        try await APIClient.shared.request(
            "/groups/\(groupId)/members/\(memberId)/role",
            method: "PATCH",
            body: RoleUpdateRequest(role: role)
        )
    }

    static func removeGroupMember(groupId: Int, memberId: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/groups/\(groupId)/members/\(memberId)", method: "DELETE"
        )
    }

    // MARK: - Invitations

    static func getPendingGroupInvitations() async throws -> [GroupInvitation] {
        try await APIClient.shared.request("/groups/invitations/pending")
    }

    static func acceptGroupInvitation(memberId: Int) async throws -> GroupMember {
        try await APIClient.shared.request(
            "/groups/invitations/\(memberId)/accept", method: "POST"
        )
    }

    static func declineGroupInvitation(memberId: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/groups/invitations/\(memberId)/decline", method: "DELETE"
        )
    }

    // MARK: - Trips and ideas attached to groups

    static func getGroupTrips(groupId: Int) async throws -> [GroupTripSummary] {
        try await APIClient.shared.request("/groups/\(groupId)/trips")
    }

    static func attachTripToGroup(groupId: Int, tripId: Int) async throws -> GroupTripSummary {
        try await APIClient.shared.request(
            "/groups/\(groupId)/trips/\(tripId)", method: "POST"
        )
    }

    static func detachTripFromGroup(groupId: Int, tripId: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/groups/\(groupId)/trips/\(tripId)", method: "DELETE"
        )
    }

    /// The group's "library" of ideas aggregated from member trips.
    static func getGroupIdeas(groupId: Int) async throws -> [IdeaBinItem] {
        try await APIClient.shared.request("/groups/\(groupId)/ideas")
    }
}
