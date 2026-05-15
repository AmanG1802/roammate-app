import Foundation

struct InviterSummary: Codable, Hashable {
    let name: String
    let email: String
}

struct Invitation: Codable, Identifiable, Hashable {
    let id: Int
    let tripId: Int
    let role: String
    let trip: TripSummary
    let inviter: InviterSummary?

    enum CodingKeys: String, CodingKey {
        case id, role, trip, inviter
        case tripId = "trip_id"
    }
}
