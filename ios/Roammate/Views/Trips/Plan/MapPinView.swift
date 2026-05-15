import SwiftUI

/// Custom map annotation view matching the web app's AdvancedMarkerElement
/// with numbered pins, category colors, and selection animation.
struct MapPinView: View {
    let index: Int
    let category: String?
    let isIdea: Bool
    let isSelected: Bool

    private var pinColor: Color {
        isIdea ? .roammateMuted : Color.categoryColor(category)
    }

    private var pinSize: CGFloat {
        isIdea ? 28 : 36
    }

    private var fontSize: CGFloat {
        isIdea ? 10 : 13
    }

    var body: some View {
        ZStack {
            // Drop shadow circle
            Circle()
                .fill(pinColor.opacity(0.3))
                .frame(width: pinSize + 8, height: pinSize + 8)

            // Main pin circle
            Circle()
                .fill(pinColor)
                .frame(width: pinSize, height: pinSize)
                .overlay(
                    Circle()
                        .strokeBorder(.white, lineWidth: 2.5)
                )

            // Number or icon
            if isIdea {
                Image(systemName: "lightbulb.fill")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(.white)
            } else {
                Text("\(index)")
                    .font(.system(size: fontSize, weight: .black, design: .rounded))
                    .foregroundStyle(.white)
            }
        }
        .scaleEffect(isSelected ? 1.35 : 1.0)
        .shadow(
            color: isSelected ? pinColor.opacity(0.5) : .clear,
            radius: isSelected ? 8 : 0
        )
        .animation(.easeOut(duration: 0.2), value: isSelected)
    }
}
