import SwiftUI

struct TripRow: View {
    let trip: Trip

    private static let tripIcons = [
        "airplane", "map.fill", "globe.americas.fill", "mountain.2.fill",
        "beach.umbrella.fill", "building.2.fill", "tent.fill", "sailboat.fill"
    ]

    private var iconName: String {
        Self.tripIcons[abs(trip.id) % Self.tripIcons.count]
    }

    var body: some View {
        HStack(spacing: RoammateSpacing.md) {
            ZStack {
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(Color.roammateIndigoTint)
                Image(systemName: iconName)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Color.roammateIndigo)
            }
            .frame(width: 44, height: 44)

            VStack(alignment: .leading, spacing: 2) {
                Text(trip.name)
                    .font(.system(.body, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateInk)
                    .lineLimit(1)
                Text(trip.dateRangeText)
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(Color.roammateMuted)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 12)
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                .fill(Color.roammateSurface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                .stroke(Color.roammateBorder, lineWidth: 1)
        )
    }
}
