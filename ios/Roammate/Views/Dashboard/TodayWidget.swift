import SwiftUI

struct TodayWidget: View {
    let trips: [Trip]
    var activeTripEvents: [Event] = []
    var onOpenTrip: ((Trip) -> Void)?

    static func activeTrip(from trips: [Trip]) -> Trip? {
        let now = Date()
        if let current = trips.first(where: { isTripActive($0, now: now) }) {
            return current
        }

        let upcoming = trips
            .compactMap { trip -> (Trip, Date)? in
                guard let s = tripLocalStart(trip), s > now else { return nil }
                return (trip, s)
            }
            .min(by: { $0.1 < $1.1 })?.0
        if let upcoming { return upcoming }

        return trips
            .compactMap { trip -> (Trip, Date)? in
                guard let e = tripLocalEnd(trip), e < now else { return nil }
                return (trip, e)
            }
            .max(by: { $0.1 < $1.1 })?.0
    }

    /// Check if a trip is active by comparing today's date in the trip's
    /// timezone against the trip's date range (treating dates as full calendar days).
    private static func isTripActive(_ trip: Trip, now: Date) -> Bool {
        guard let s = trip.startDate, let e = trip.endDate else { return false }
        let tz = TimeZone(identifier: trip.timezone ?? "") ?? .current
        var cal = Calendar(identifier: .iso8601)
        cal.timeZone = tz
        let todayInTripTZ = cal.startOfDay(for: now)
        let startDay = cal.startOfDay(for: s)
        let endDay = cal.startOfDay(for: e)
        return startDay <= todayInTripTZ && todayInTripTZ <= endDay
    }

    /// Start-of-day in trip timezone for the trip's start date.
    private static func tripLocalStart(_ trip: Trip) -> Date? {
        guard let s = trip.startDate else { return nil }
        let tz = TimeZone(identifier: trip.timezone ?? "") ?? .current
        var cal = Calendar(identifier: .iso8601)
        cal.timeZone = tz
        return cal.startOfDay(for: s)
    }

    /// End-of-day in trip timezone for the trip's end date.
    private static func tripLocalEnd(_ trip: Trip) -> Date? {
        guard let e = trip.endDate else { return nil }
        let tz = TimeZone(identifier: trip.timezone ?? "") ?? .current
        var cal = Calendar(identifier: .iso8601)
        cal.timeZone = tz
        return cal.date(byAdding: .day, value: 1, to: cal.startOfDay(for: e))
    }

    private enum CardKind: Hashable { case pre, current, post }

    /// Ordered: Past (left), Ongoing (center), Upcoming (right)
    private var cards: [(kind: CardKind, trip: Trip)] {
        guard !trips.isEmpty else { return [] }
        var result: [(CardKind, Trip)] = []
        let now = Date()

        if let recent = trips
            .compactMap({ trip -> (Trip, Date)? in
                guard let e = Self.tripLocalEnd(trip), e < now else { return nil }
                return (trip, e)
            })
            .max(by: { $0.1 < $1.1 })?.0 {
            result.append((.post, recent))
        }

        if let current = trips.first(where: { Self.isTripActive($0, now: now) }) {
            result.append((.current, current))
        }

        if let upcoming = trips
            .compactMap({ trip -> (Trip, Date)? in
                guard let s = Self.tripLocalStart(trip), s > now else { return nil }
                return (trip, s)
            })
            .min(by: { $0.1 < $1.1 })?.0 {
            result.append((.pre, upcoming))
        }

        return result.isEmpty ? [(.pre, trips[0])] : result
    }

    @State private var selection: Int = 0

    var body: some View {
        Group {
            if cards.isEmpty {
                NoTripsCard()
            } else {
                TabView(selection: $selection) {
                    ForEach(Array(cards.enumerated()), id: \.offset) { idx, item in
                        cardView(for: item).tag(idx)
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: .always))
                .indexViewStyle(.page(backgroundDisplayMode: .interactive))
            }
        }
        .aspectRatio(1.0 / 0.85, contentMode: .fit)
        .clipShape(RoundedRectangle(cornerRadius: RoammateRadius.widget, style: .continuous))
        .shadow(
            color: RoammateShadow.card.color,
            radius: RoammateShadow.card.radius,
            x: 0, y: RoammateShadow.card.y
        )
        .onAppear {
            UIPageControl.appearance().currentPageIndicatorTintColor = UIColor(Color.roammateIndigo)
            UIPageControl.appearance().pageIndicatorTintColor = UIColor(Color.roammateMuted.opacity(0.35))

            if let activeIdx = cards.firstIndex(where: { $0.kind == .current }) {
                selection = activeIdx
            }
        }
    }

    @ViewBuilder
    private func cardView(for item: (kind: CardKind, trip: Trip)) -> some View {
        switch item.kind {
        case .pre:     PreTripCard(trip: item.trip)
        case .current: InTripCard(trip: item.trip, events: activeTripEvents, onOpenTrip: { onOpenTrip?(item.trip) })
        case .post:    PostTripCard(trip: item.trip)
        }
    }
}
