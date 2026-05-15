import Foundation

/// Votes endpoints. Note these are mounted at the root (no `/votes` prefix).
enum VoteService {
    @discardableResult
    static func voteEvent(eventId: Int, value: Int) async throws -> VoteTally {
        try await APIClient.shared.request(
            "/events/\(eventId)/vote", method: "POST", body: VoteRequest(value: value)
        )
    }

    static func getEventVotes(eventId: Int) async throws -> VoteTally {
        try await APIClient.shared.request("/events/\(eventId)/votes")
    }

    static func getEventVoters(eventId: Int) async throws -> VoterList {
        try await APIClient.shared.request("/events/\(eventId)/voters")
    }

    @discardableResult
    static func voteIdea(ideaId: Int, value: Int) async throws -> VoteTally {
        try await APIClient.shared.request(
            "/ideas/\(ideaId)/vote", method: "POST", body: VoteRequest(value: value)
        )
    }

    static func getIdeaVotes(ideaId: Int) async throws -> VoteTally {
        try await APIClient.shared.request("/ideas/\(ideaId)/votes")
    }

    static func getIdeaVoters(ideaId: Int) async throws -> VoterList {
        try await APIClient.shared.request("/ideas/\(ideaId)/voters")
    }
}
