import Foundation

struct User: Codable, Identifiable {
    let id: Int
    let email: String
    let name: String
    let personas: [String]?
    let avatarUrl: String?
    let homeCity: String?
    let timezone: String?
    let currency: String?
    let travelBlurb: String?
    let createdAt: Date?

    enum CodingKeys: String, CodingKey {
        case id, email, name, personas, timezone, currency
        case avatarUrl = "avatar_url"
        case homeCity = "home_city"
        case travelBlurb = "travel_blurb"
        case createdAt = "created_at"
    }

    var initials: String {
        name.split(separator: " ")
            .prefix(2)
            .compactMap { $0.first.map(String.init) }
            .joined()
            .uppercased()
    }
}
