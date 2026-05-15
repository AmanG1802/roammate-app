import Foundation

struct TripDay: Codable, Identifiable, Hashable {
    let id: Int
    let tripId: Int
    let date: Date
    let dayNumber: Int

    enum CodingKeys: String, CodingKey {
        case id, date
        case tripId = "trip_id"
        case dayNumber = "day_number"
    }
}
