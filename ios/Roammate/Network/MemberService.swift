import Foundation

enum MemberService {
    // MARK: - Members of a trip

    static func getMembers(tripId: Int) async throws -> [TripMember] {
        try await APIClient.shared.request("/trips/\(tripId)/members")
    }

    static func invite(tripId: Int, email: String, role: String) async throws -> TripMember {
        try await APIClient.shared.request(
            "/trips/\(tripId)/invite",
            method: "POST",
            body: InviteRequest(email: email, role: role)
        )
    }

    static func removeMember(tripId: Int, memberId: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/trips/\(tripId)/members/\(memberId)", method: "DELETE"
        )
    }

    static func updateRole(tripId: Int, memberId: Int, role: String) async throws -> TripMember {
        try await APIClient.shared.request(
            "/trips/\(tripId)/members/\(memberId)/role",
            method: "PATCH",
            body: RoleUpdateRequest(role: role)
        )
    }

    // MARK: - Invitations

    static func getPendingInvitations() async throws -> [Invitation] {
        try await APIClient.shared.request("/trips/invitations/pending")
    }

    static func acceptInvitation(memberId: Int) async throws -> TripMember {
        try await APIClient.shared.request(
            "/trips/invitations/\(memberId)/accept", method: "POST"
        )
    }

    static func declineInvitation(memberId: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/trips/invitations/\(memberId)/decline", method: "DELETE"
        )
    }
}
