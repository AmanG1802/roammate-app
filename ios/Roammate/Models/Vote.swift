import Foundation

struct VoteRequest: Encodable {
    /// -1 (down), 0 (clear), or 1 (up).
    let value: Int
}

struct VoteTally: Codable {
    let up: Int
    let down: Int
    let myVote: Int

    enum CodingKeys: String, CodingKey {
        case up, down
        case myVote = "my_vote"
    }
}

struct VoterInfo: Codable, Hashable {
    let name: String
    let avatarUrl: String?

    enum CodingKeys: String, CodingKey {
        case name
        case avatarUrl = "avatar_url"
    }
}

struct VoterList: Codable {
    let upVoters: [VoterInfo]
    let downVoters: [VoterInfo]

    enum CodingKeys: String, CodingKey {
        case upVoters = "up_voters"
        case downVoters = "down_voters"
    }
}
