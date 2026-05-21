import SwiftUI

// MARK: - Helpers

private func daysBetween(_ from: Date, _ to: Date) -> Int {
    let cal = Calendar.current
    let f = cal.startOfDay(for: from)
    let t = cal.startOfDay(for: to)
    return cal.dateComponents([.day], from: f, to: t).day ?? 0
}

private func detailedDate(_ date: Date) -> String {
    let f = DateFormatter()
    f.dateFormat = "EEEE, MMM d"
    return f.string(from: date)
}

private func formattedDate(_ date: Date) -> String {
    let f = DateFormatter()
    f.dateFormat = "MMM d"
    return f.string(from: date)
}

private func shortTime(_ date: Date) -> String {
    let f = DateFormatter()
    f.dateFormat = "h:mm a"
    return f.string(from: date)
}

private func shortTime(_ tod: TimeOfDay) -> String {
    let suffix = tod.hour < 12 ? "AM" : "PM"
    let h12 = tod.hour == 0 ? 12 : (tod.hour > 12 ? tod.hour - 12 : tod.hour)
    return String(format: "%d:%02d %@", h12, tod.minute, suffix)
}

private func parseDayDate(_ s: String) -> Date? {
    let f = DateFormatter()
    f.calendar = Calendar(identifier: .gregorian)
    f.timeZone = TimeZone(identifier: "UTC")
    f.dateFormat = "yyyy-MM-dd"
    return f.date(from: s)
}

// MARK: - Shared HeroShell

private struct HeroShell<Content: View>: View {
    let badge: String
    let badgeIcon: String
    let toneGradient: [Color]
    let toneColor: Color
    let content: Content

    init(
        badge: String,
        badgeIcon: String,
        toneGradient: [Color],
        toneColor: Color,
        @ViewBuilder content: () -> Content
    ) {
        self.badge = badge
        self.badgeIcon = badgeIcon
        self.toneGradient = toneGradient
        self.toneColor = toneColor
        self.content = content()
    }

    var body: some View {
        ZStack {
            LinearGradient(
                colors: toneGradient,
                startPoint: .topLeading, endPoint: .bottomTrailing
            )

            VStack(alignment: .leading, spacing: RoammateSpacing.sm) {
                HStack(spacing: 4) {
                    Image(systemName: badgeIcon)
                        .font(.system(size: 10, weight: .black))
                    Text(badge.uppercased())
                        .font(.system(size: 10, weight: .black, design: .rounded))
                        .tracking(1.5)
                }
                .foregroundStyle(toneColor)

                content
            }
            .padding(RoammateSpacing.lg)
        }
        .overlay(
            RoundedRectangle(cornerRadius: RoammateRadius.widget, style: .continuous)
                .stroke(Color.roammateBorder.opacity(0.6), lineWidth: 0.5)
        )
    }
}

// MARK: - Pre-trip (upcoming)

struct PreTripCard: View {
    let trip: Trip

    private var daysUntil: Int {
        guard let start = trip.startDate else { return 0 }
        return max(0, daysBetween(Date(), start))
    }

    var body: some View {
        HeroShell(
            badge: daysUntil <= 0 ? "Trip Day" : "\(daysUntil) day\(daysUntil == 1 ? "" : "s") to go",
            badgeIcon: "airplane",
            toneGradient: [Color.roammateIndigoTint, .white],
            toneColor: Color.roammateIndigo
        ) {
            VStack(alignment: .leading, spacing: 4) {
                Text(trip.name)
                    .font(.system(.title2, design: .rounded, weight: .black))
                    .foregroundStyle(Color.roammateInk)
                    .lineLimit(2)

                if let start = trip.startDate {
                    HStack(spacing: 6) {
                        Image(systemName: "calendar")
                            .font(.system(size: 13, weight: .medium))
                        Text(detailedDate(start))
                            .font(.system(.subheadline, design: .rounded, weight: .medium))
                    }
                    .foregroundStyle(Color.roammateMuted)
                }
            }

            Spacer()

            HStack(alignment: .lastTextBaseline, spacing: 6) {
                Text("\(daysUntil)")
                    .font(.system(size: 48, design: .rounded).weight(.black))
                    .foregroundStyle(Color.roammateInk)
                Text(daysUntil == 1 ? "day to go" : "days to go")
                    .font(.system(.body, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateMuted)

                Spacer()

                HStack(spacing: 4) {
                    Text("Plan Itinerary")
                        .font(.system(.caption, design: .rounded, weight: .black))
                    Image(systemName: "chevron.right")
                        .font(.system(size: 10, weight: .bold))
                }
                .foregroundStyle(.white)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(
                    Capsule().fill(Color.roammateIndigo)
                )
            }
        }
    }
}

// MARK: - In-trip (active)

struct InTripCard: View {
    let trip: Trip
    var events: [Event] = []

    private var tripCalendar: Calendar {
        var cal = Calendar(identifier: .iso8601)
        cal.timeZone = TimeZone(identifier: trip.timezone ?? "") ?? .current
        return cal
    }

    private var dayNumber: Int {
        guard let start = trip.startDate else { return 1 }
        let cal = tripCalendar
        let s = cal.startOfDay(for: start)
        let t = cal.startOfDay(for: Date())
        return max(1, (cal.dateComponents([.day], from: s, to: t).day ?? 0) + 1)
    }

    private var totalDays: Int {
        guard let start = trip.startDate, let end = trip.endDate else { return 1 }
        let cal = tripCalendar
        let s = cal.startOfDay(for: start)
        let e = cal.startOfDay(for: end)
        return max(1, (cal.dateComponents([.day], from: s, to: e).day ?? 0) + 1)
    }

    private var todayEvents: [Event] {
        let tz = TimeZone(identifier: trip.timezone ?? "") ?? .current
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .iso8601)
        f.timeZone = tz
        f.dateFormat = "yyyy-MM-dd"
        let todayStr = f.string(from: Date())
        return events
            .filter { $0.dayDate == todayStr }
            .sorted { $0.sortOrder < $1.sortOrder }
    }

    private var scheduledItems: [(label: String, name: String, time: String)] {
        let now = Date()
        let tz = TimeZone(identifier: trip.timezone ?? "UTC") ?? .current
        let sorted = todayEvents

        var ongoing: Event?
        var upcoming: [Event] = []

        for event in sorted {
            guard let dayStr = event.dayDate,
                  let day = parseDayDate(dayStr) else { continue }
            // Combine wall-clock TIME with the day in the trip's tz to get
            // absolute instants, then compare to `now`.
            let startInstant = event.startTime?.combine(day: day, tz: tz)
            let endInstant = event.endTime?.combine(day: day, tz: tz)

            if let start = startInstant, let end = endInstant, start <= now && now <= end {
                ongoing = event
            } else if let start = startInstant, start > now {
                upcoming.append(event)
            }
        }

        var result: [(String, String, String)] = []

        if let ongoing {
            result.append(("Now", ongoing.title, ongoing.startTime.map { shortTime($0) } ?? ""))
        }

        let maxUpcoming = ongoing != nil ? 2 : 3
        for (i, event) in upcoming.prefix(maxUpcoming).enumerated() {
            let label = i == 0 ? "Up Next" : "Next"
            result.append((label, event.title, event.startTime.map { shortTime($0) } ?? ""))
        }

        return result
    }

    let onOpenTrip: () -> Void

    var body: some View {
        HeroShell(
            badge: "Day \(dayNumber) of \(totalDays)",
            badgeIcon: "sparkles",
            toneGradient: [Color.roammateAmberTint, .white],
            toneColor: Color.roammateAmber
        ) {
            VStack(alignment: .leading, spacing: 4) {
                Text(trip.name)
                    .font(.system(.title2, design: .rounded, weight: .black))
                    .foregroundStyle(Color.roammateInk)
                    .lineLimit(2)

                if let start = trip.startDate {
                    Text("Started \(formattedDate(start))")
                        .font(.system(.subheadline, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.roammateMuted)
                }
            }

            Divider().opacity(0.4)

            if scheduledItems.isEmpty {
                let dayWrappedUp = !todayEvents.isEmpty
                VStack(spacing: 6) {
                    Text(dayWrappedUp ? "DAY COMPLETE" : "NOTHING ON TODAY")
                        .font(.system(.caption2, design: .rounded, weight: .black))
                        .tracking(2)
                        .foregroundStyle(Color.roammateEmerald)
                    Text("That's all — nothing else planned for today.")
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.roammateInk)
                        .multilineTextAlignment(.center)
                    if dayWrappedUp {
                        Text("\(todayEvents.count) event\(todayEvents.count == 1 ? "" : "s") wrapped.")
                            .font(.system(.caption, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.roammateMuted)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
            } else {
                VStack(spacing: 8) {
                    ForEach(Array(scheduledItems.enumerated()), id: \.offset) { _, item in
                        HStack(spacing: 8) {
                            Text(item.label)
                                .font(.system(.caption, design: .rounded, weight: .black))
                                .foregroundStyle(item.label == "Now" ? Color.roammateAmber : item.label == "Up Next" ? Color.roammateIndigo : Color.roammateMuted)
                                .frame(width: 56, alignment: .leading)
                            Text(item.name)
                                .font(.system(.subheadline, design: .rounded, weight: .semibold))
                                .foregroundStyle(Color.roammateInk)
                                .lineLimit(1)
                            Spacer()
                            HStack(spacing: 3) {
                                Image(systemName: "clock")
                                    .font(.system(size: 10))
                                Text(item.time)
                                    .font(.system(.caption, design: .rounded, weight: .medium))
                            }
                            .foregroundStyle(Color.roammateMuted)
                        }
                    }
                }
                .padding(.vertical, 4)
            }

            Spacer()

            HStack {
                Spacer()

                Button {
                    onOpenTrip()
                } label: {
                    HStack(spacing: 4) {
                        Text("Open Trip")
                            .font(.system(.caption, design: .rounded, weight: .black))
                        Image(systemName: "chevron.right")
                            .font(.system(size: 10, weight: .bold))
                    }
                    .foregroundStyle(.white)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 8)
                    .background(
                        Capsule().fill(Color.roammateInk)
                    )
                }
                .buttonStyle(.plain)
            }
        }
    }
}

// MARK: - Post-trip (recap)

struct PostTripCard: View {
    let trip: Trip

    private static let roseTint = Color(red: 255/255, green: 241/255, blue: 242/255)
    private static let roseColor = Color(red: 225/255, green: 29/255, blue: 72/255)

    private var daysSince: Int {
        guard let end = trip.endDate else { return 0 }
        return max(0, daysBetween(end, Date()))
    }

    private var totalDays: Int {
        guard let start = trip.startDate, let end = trip.endDate else { return 0 }
        return max(1, daysBetween(start, end) + 1)
    }

    var body: some View {
        HeroShell(
            badge: "Wrapped \(daysSince) day\(daysSince == 1 ? "" : "s") ago",
            badgeIcon: "clock.arrow.circlepath",
            toneGradient: [Self.roseTint, .white],
            toneColor: Self.roseColor
        ) {
            VStack(alignment: .leading, spacing: 4) {
                Text(trip.name)
                    .font(.system(.title2, design: .rounded, weight: .black))
                    .foregroundStyle(Color.roammateInk)
                    .lineLimit(2)

                HStack(spacing: 12) {
                    if totalDays > 0 {
                        HStack(spacing: 4) {
                            Image(systemName: "calendar")
                                .font(.system(size: 12))
                            Text("\(totalDays) days")
                                .font(.system(.caption, design: .rounded, weight: .semibold))
                        }
                        .foregroundStyle(Color.roammateMuted)
                    }
                    HStack(spacing: 4) {
                        Image(systemName: "clock")
                            .font(.system(size: 12))
                        Text("\(daysSince) \(daysSince == 1 ? "day" : "days") ago")
                            .font(.system(.caption, design: .rounded, weight: .semibold))
                    }
                    .foregroundStyle(Color.roammateMuted)
                }
            }

            Spacer()

            HStack {
                Spacer()
                HStack(spacing: 4) {
                    Text("See Recap")
                        .font(.system(.caption, design: .rounded, weight: .black))
                    Image(systemName: "chevron.right")
                        .font(.system(size: 10, weight: .bold))
                }
                .foregroundStyle(.white)
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
                .background(
                    Capsule().fill(Self.roseColor)
                )
            }
        }
    }
}

// MARK: - No trips state

struct NoTripsCard: View {
    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color.roammateIndigoTint, Color.roammateBackground],
                startPoint: .topLeading, endPoint: .bottomTrailing
            )

            VStack(spacing: RoammateSpacing.sm) {
                Image(systemName: "map.fill")
                    .font(.system(size: 40))
                    .foregroundStyle(Color.roammateIndigo)
                Text("Plan your first trip")
                    .font(.system(.title3, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.roammateInk)
                Text("Tap the sparkle button to start")
                    .font(.system(.subheadline, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
                    .multilineTextAlignment(.center)
            }
            .padding(RoammateSpacing.lg)
        }
    }
}
