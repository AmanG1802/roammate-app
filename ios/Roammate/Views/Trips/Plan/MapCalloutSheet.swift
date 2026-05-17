import SwiftUI

/// Detail callout shown when a map annotation is tapped.
/// Matches the web app's InfoWindow content (minus photo/rating for Apple enrichment).
struct MapCalloutSheet: View {
    let event: Event
    @Environment(\.dismiss) private var dismiss

    private var timeString: String {
        guard let start = event.startTime else { return "TBD" }
        let fmt = DateFormatter()
        fmt.dateFormat = "h:mm a"
        var str = fmt.string(from: start)
        if let end = event.endTime {
            str += " – \(fmt.string(from: end))"
        }
        return str
    }

    private var hasTime: Bool { event.startTime != nil }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            // Title
            Text(event.title)
                .font(.system(size: 16, weight: .black))
                .foregroundStyle(Color.roammateInk)
                .lineLimit(2)

            // Badges row
            HStack(spacing: 6) {
                // Time badge
                Text(timeString)
                    .font(.system(size: 11, weight: .heavy))
                    .foregroundStyle(hasTime ? Color.roammateIndigo : Color.roammateAmber)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .fill(hasTime ? Color.roammateIndigoTint : Color.roammateAmberTint)
                    )

                // Category badge
                if let category = event.category {
                    Text(category)
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(Color.roammateMuted)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(
                            RoundedRectangle(cornerRadius: 6)
                                .fill(Color.roammateBackground)
                        )
                }

                // Rating badge (may be nil for Apple-enriched items)
                if let rating = event.rating {
                    HStack(spacing: 2) {
                        Image(systemName: "star.fill")
                            .font(.system(size: 9))
                        Text(String(format: "%.1f", rating))
                            .font(.system(size: 11, weight: .bold))
                    }
                    .foregroundStyle(Color.roammateAmber)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .fill(Color.roammateAmberTint)
                    )
                }
            }

            // Address
            if let address = event.address, !address.isEmpty {
                Text(address)
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(Color.roammateMuted)
                    .lineLimit(2)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.roammateSurface)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.1), radius: 12, y: 4)
    }
}

/// Compact callout for route leg info shown when a polyline is tapped.
struct RouteLegCallout: View {
    let fromTitle: String
    let toTitle: String
    let durationSeconds: Int
    let distanceMeters: Int
    let color: Color

    private var travelIcon: String {
        let speed = distanceMeters > 0 && durationSeconds > 0
            ? Double(distanceMeters) / Double(durationSeconds)
            : 0
        return speed < 2.8 ? "figure.walk" : "car.fill"
    }

    private var formattedTime: String {
        let mins = max(1, Int(round(Double(durationSeconds) / 60.0)))
        if mins < 60 { return "\(mins) min" }
        let h = mins / 60
        let m = mins % 60
        return m == 0 ? "\(h)h" : "\(h)h \(m)m"
    }

    private var formattedDistance: String {
        if distanceMeters >= 1000 {
            return String(format: "%.1f km", Double(distanceMeters) / 1000.0)
        }
        return "\(distanceMeters) m"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 6) {
                Image(systemName: travelIcon)
                    .font(.system(size: 14))
                Text(formattedTime)
                    .font(.system(size: 15, weight: .black))
                    .foregroundStyle(color)
                Text(formattedDistance)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(Color.roammateMuted)
            }

            HStack(spacing: 4) {
                Text(fromTitle)
                    .font(.system(size: 12, weight: .heavy))
                    .foregroundStyle(Color.roammateInk)
                    .lineLimit(1)
                Image(systemName: "arrow.right")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(Color.roammateMuted)
                Text(toTitle)
                    .font(.system(size: 12, weight: .heavy))
                    .foregroundStyle(Color.roammateInk)
                    .lineLimit(1)
            }
        }
        .padding(12)
        .background(Color.roammateSurface)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.1), radius: 8, y: 2)
    }
}
