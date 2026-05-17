import Foundation

struct Trip: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let startDate: Date?
    let endDate: Date?
    let timezone: String?
    let createdAt: Date?
    let createdById: Int?
    /// Present when the server returns `TripWithRole` (e.g. `GET /trips`).
    let myRole: String?

    enum CodingKeys: String, CodingKey {
        case id, name, timezone
        case startDate = "start_date"
        case endDate = "end_date"
        case createdAt = "created_at"
        case createdById = "created_by_id"
        case myRole = "my_role"
    }

    var dateRangeText: String {
        let fmt = DateFormatter()
        fmt.dateStyle = .medium
        fmt.timeStyle = .none
        let start = startDate.map { fmt.string(from: $0) } ?? "?"
        let end = endDate.map { fmt.string(from: $0) } ?? "?"
        return "\(start) – \(end)"
    }
}

struct TripCreate: Encodable {
    let name: String
    let startDate: Date?
    let endDate: Date?
    let timezone: String

    enum CodingKeys: String, CodingKey {
        case name, timezone
        case startDate = "start_date"
        case endDate = "end_date"
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(name, forKey: .name)
        try container.encode(timezone, forKey: .timezone)
        if let startDate {
            try container.encode(Self.dateOnlyString(startDate), forKey: .startDate)
        }
        if let endDate {
            try container.encode(Self.dateOnlyString(endDate), forKey: .endDate)
        }
    }

    private static func dateOnlyString(_ date: Date) -> String {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .iso8601)
        f.timeZone = .current
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: date)
    }
}

struct TripUpdate: Encodable {
    let name: String?
    let startDate: Date?
    let endDate: Date?
    let timezone: String?

    enum CodingKeys: String, CodingKey {
        case name, timezone
        case startDate = "start_date"
        case endDate = "end_date"
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(name, forKey: .name)
        try container.encodeIfPresent(timezone, forKey: .timezone)
        if let startDate {
            try container.encode(Self.dateTimeString(startDate), forKey: .startDate)
        }
        if let endDate {
            try container.encode(Self.dateTimeString(endDate), forKey: .endDate)
        }
    }

    private static func dateTimeString(_ date: Date) -> String {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .iso8601)
        f.timeZone = TimeZone(identifier: "UTC")
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return f.string(from: date)
    }
}

struct TripSummary: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let startDate: Date?

    enum CodingKeys: String, CodingKey {
        case id, name
        case startDate = "start_date"
    }
}
