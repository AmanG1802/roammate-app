import SwiftUI

struct TodayWidget: View {
    let trips: [Trip]
    var activeTripEvents: [Event] = []

    static func activeTrip(from trips: [Trip]) -> Trip? {
        let now = Date()
        if let current = trips.first(where: { trip in
            guard let s = trip.startDate, let e = trip.endDate else { return false }
            return s <= now && now <= e
        }) { return current }

        let upcoming = trips
            .compactMap { trip -> (Trip, Date)? in
                guard let s = trip.startDate, s > now else { return nil }
                return (trip, s)
            }
            .min(by: { $0.1 < $1.1 })?.0
        if let upcoming { return upcoming }

        return trips
            .compactMap { trip -> (Trip, Date)? in
                guard let e = trip.endDate, e < now else { return nil }
                return (trip, e)
            }
            .max(by: { $0.1 < $1.1 })?.0
    }

    private enum CardKind: Hashable { case pre, current, post }

    /// Ordered: Past (left), Ongoing (center), Upcoming (right)
    private var cards: [(kind: CardKind, trip: Trip)] {
        guard !trips.isEmpty else { return [] }
        var result: [(CardKind, Trip)] = []
        let now = Date()

        if let recent = trips
            .compactMap({ trip -> (Trip, Date)? in
                guard let e = trip.endDate, e < now else { return nil }
                return (trip, e)
            })
            .max(by: { $0.1 < $1.1 })?.0 {
            result.append((.post, recent))
        }

        if let current = trips.first(where: { trip in
            guard let s = trip.startDate, let e = trip.endDate else { return false }
            return s <= now && now <= e
        }) {
            result.append((.current, current))
        }

        if let upcoming = trips
            .compactMap({ trip -> (Trip, Date)? in
                guard let s = trip.startDate, s > now else { return nil }
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
        case .current: InTripCard(trip: item.trip, events: activeTripEvents)
        case .post:    PostTripCard(trip: item.trip)
        }
    }
}
