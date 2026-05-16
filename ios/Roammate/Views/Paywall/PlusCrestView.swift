import SwiftUI

/// The Roammate Plus crest — the indigo→fuchsia→amber gradient square with
/// a sparkle, slowly rotating to suggest "premium." Reserved for Plus
/// surfaces only.
///
/// Honors `accessibilityReduceMotion` by freezing the shimmer angle.
struct PlusCrestView: View {
    var size: CGFloat = 64

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        ZStack {
            TimelineView(.animation(minimumInterval: 1.0 / 30.0, paused: reduceMotion)) { context in
                ShimmerLayer(date: context.date)
            }
            .blur(radius: 0.5)
            .overlay(
                // Soft highlight ring along the inside edge.
                RoundedRectangle(cornerRadius: size * 0.28, style: .continuous)
                    .stroke(Color.white.opacity(0.18), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: size * 0.28, style: .continuous))

            Image(systemName: "sparkles")
                .font(.system(size: size * 0.45, weight: .bold))
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.15), radius: 2, y: 1)
        }
        .frame(width: size, height: size)
        .shadow(
            color: Color(red: 79/255, green: 70/255, blue: 229/255).opacity(0.45),
            radius: size * 0.22,
            x: 0,
            y: size * 0.12
        )
        .accessibilityHidden(true)
    }
}


/// The "Roammate Plus" wordmark with the brand gradient as text fill.
struct PlusWordmark: View {
    var font: Font = .system(.title2, design: .rounded, weight: .black)

    var body: some View {
        Text("Roammate Plus")
            .font(font)
            .foregroundStyle(RoammateGradient.plus)
            .accessibilityLabel("Roammate Plus")
    }
}

/// One frame of the crest shimmer. Extracted so the TimelineView closure
/// returns a single concrete View (which the type inference can resolve).
private struct ShimmerLayer: View {
    let date: Date
    var body: some View {
        let seconds = date.timeIntervalSinceReferenceDate
        let angle = Angle.degrees((seconds * 45).truncatingRemainder(dividingBy: 360))
        Rectangle().fill(RoammateGradient.plusAngular(angle: angle))
    }
}
