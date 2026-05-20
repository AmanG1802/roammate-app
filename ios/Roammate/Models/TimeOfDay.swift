import Foundation

/// A naive (no-date, no-tz) wall-clock time-of-day. Replaces `Date?` for
/// event/idea time fields after the backend schema split (see docs/[27]).
///
/// Wire format: `"HH:mm:ss"` strings — what the backend's `Time` columns and
/// pinned Pydantic serializer produce. Fractional seconds are not accepted on
/// decode and are not produced on encode, matching the backend contract.
///
/// The owning record carries a separate `dayDate` (a calendar date) and the
/// trip carries the IANA timezone. To get an absolute instant (e.g. for
/// "is this happening now?" comparisons), use `combine(day:tz:)`.
struct TimeOfDay: Codable, Hashable, Comparable {
    let hour: Int
    let minute: Int
    let second: Int

    init(hour: Int, minute: Int, second: Int = 0) {
        self.hour = hour
        self.minute = minute
        self.second = second
    }

    /// Parse `"HH:mm:ss"` or `"HH:mm"`.
    init?(_ wire: String) {
        let parts = wire.split(separator: ":")
        guard parts.count == 2 || parts.count == 3,
              let h = Int(parts[0]), (0..<24).contains(h),
              let m = Int(parts[1]), (0..<60).contains(m) else {
            return nil
        }
        let s = parts.count == 3 ? (Int(parts[2]) ?? 0) : 0
        guard (0..<60).contains(s) else { return nil }
        self.init(hour: h, minute: m, second: s)
    }

    /// Pull from a `Date` produced by a `DatePicker(.hourAndMinute)`. The
    /// picker anchors on `Date()`'s day; we just extract H:M:S in the
    /// supplied calendar (defaults to current).
    init(date: Date, calendar: Calendar = .current) {
        let comps = calendar.dateComponents([.hour, .minute, .second], from: date)
        self.init(
            hour: comps.hour ?? 0,
            minute: comps.minute ?? 0,
            second: comps.second ?? 0,
        )
    }

    /// `"HH:mm:ss"` — the canonical wire form. Stable lexicographic sort.
    var wireString: String {
        String(format: "%02d:%02d:%02d", hour, minute, second)
    }

    /// Combine this time-of-day with a calendar date in *tz*, returning an
    /// absolute instant. Used for "is this event happening right now?"
    /// comparisons against `Date()`.
    func combine(day: Date, tz: TimeZone) -> Date? {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = tz
        var comps = cal.dateComponents([.year, .month, .day], from: day)
        comps.hour = hour
        comps.minute = minute
        comps.second = second
        return cal.date(from: comps)
    }

    /// Round-trip a Date back through the picker. Anchors on today's calendar
    /// date so the picker shows the right time component.
    func asPickerDate(calendar: Calendar = .current) -> Date {
        var comps = calendar.dateComponents([.year, .month, .day], from: Date())
        comps.hour = hour
        comps.minute = minute
        comps.second = second
        return calendar.date(from: comps) ?? Date()
    }

    // MARK: - Codable

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let raw = try container.decode(String.self)
        guard let parsed = TimeOfDay(raw) else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "TimeOfDay expected \"HH:mm:ss\", got \(raw)"
            )
        }
        self = parsed
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(wireString)
    }

    // MARK: - Comparable

    static func < (lhs: TimeOfDay, rhs: TimeOfDay) -> Bool {
        if lhs.hour != rhs.hour { return lhs.hour < rhs.hour }
        if lhs.minute != rhs.minute { return lhs.minute < rhs.minute }
        return lhs.second < rhs.second
    }
}
