import SwiftUI

/// 24-particle confetti burst rendered via `Canvas`. Used in the paywall
/// success state. Auto-removes after ~1.2s.
struct ConfettiBurst: View {
    @State private var t: Double = 0
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private let particles: [Particle] = (0..<24).map { i in
        let angle = (Double(i) / 24.0) * .pi * 2
        let dist = 130.0 + Double.random(in: 0...70)
        return Particle(
            angle: angle,
            distance: dist,
            color: ConfettiBurst.palette[i % ConfettiBurst.palette.count],
            rotation: Double.random(in: 0...360)
        )
    }

    private static let palette: [Color] = [
        Color(red: 79/255, green: 70/255, blue: 229/255),   // indigo
        Color(red: 217/255, green: 70/255, blue: 239/255),  // fuchsia
        Color(red: 245/255, green: 158/255, blue: 11/255),  // amber
    ]

    var body: some View {
        Canvas { ctx, size in
            let center = CGPoint(x: size.width / 2, y: size.height / 2 - 30)
            for p in particles {
                let progress = t
                let x = center.x + CGFloat(cos(p.angle) * p.distance * progress)
                let y = center.y + CGFloat(sin(p.angle) * p.distance * progress)
                let opacity = max(0, 1 - progress)
                var path = Path()
                path.addRoundedRect(
                    in: CGRect(x: -3, y: -6, width: 6, height: 12),
                    cornerSize: CGSize(width: 3, height: 3)
                )
                ctx.translateBy(x: x, y: y)
                ctx.rotate(by: .degrees(p.rotation * (1 + progress)))
                ctx.fill(path, with: .color(p.color.opacity(opacity)))
                ctx.rotate(by: .degrees(-p.rotation * (1 + progress)))
                ctx.translateBy(x: -x, y: -y)
            }
        }
        .allowsHitTesting(false)
        .onAppear {
            guard !reduceMotion else { return }
            withAnimation(.timingCurve(0.16, 1, 0.3, 1, duration: 1.2)) {
                t = 1.0
            }
        }
    }

    private struct Particle {
        let angle: Double
        let distance: Double
        let color: Color
        let rotation: Double
    }
}
