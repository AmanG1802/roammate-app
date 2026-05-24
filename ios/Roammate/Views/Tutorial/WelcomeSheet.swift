import SwiftUI

struct WelcomeSheet: View {
    @EnvironmentObject var tutorial: TutorialStore
    @State private var starting = false
    var onStart: () -> Void
    var onSkip: () -> Void

    private let features: [(String, String)] = [
        ("mappin.and.ellipse", "A canned 3-day NYC trip to play with"),
        ("safari", "8 quick steps across every part of the app"),
        ("sparkles", "No quota burned, no Plus required"),
    ]

    var body: some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 6) {
                    Image(systemName: "sparkles")
                        .font(.caption.bold())
                    Text("QUICK TOUR")
                        .font(.caption2.weight(.heavy))
                        .tracking(2)
                }
                .padding(.horizontal, 10).padding(.vertical, 5)
                .background(Color.white.opacity(0.18), in: Capsule())
                .foregroundColor(.white)

                Text("Welcome to Roammate")
                    .font(.system(size: 26, weight: .semibold))
                    .foregroundColor(.white)

                Text("Two minutes, no commitment. We'll walk you through planning a real-feeling NYC trip using every part of the app.")
                    .font(.subheadline)
                    .foregroundColor(.white.opacity(0.92))
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 24).padding(.vertical, 26)
            .background(
                LinearGradient(
                    colors: [Color.roammateIndigo, Color.roammateViolet],
                    startPoint: .topLeading, endPoint: .bottomTrailing
                )
            )

            VStack(spacing: 12) {
                ForEach(features, id: \.1) { icon, label in
                    HStack(spacing: 12) {
                        ZStack {
                            RoundedRectangle(cornerRadius: 10)
                                .fill(Color.roammateIndigoTint)
                            Image(systemName: icon)
                                .font(.subheadline.weight(.semibold))
                                .foregroundColor(.roammateIndigo)
                        }
                        .frame(width: 32, height: 32)
                        Text(label)
                            .font(.subheadline)
                            .foregroundColor(.roammateInk)
                        Spacer()
                    }
                }
            }
            .padding(.horizontal, 24).padding(.top, 18).padding(.bottom, 8)

            HStack(spacing: 10) {
                Button {
                    onSkip()
                } label: {
                    Text("Skip for now")
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                }
                .foregroundColor(.roammateMuted)

                Button {
                    starting = true
                    Task {
                        onStart()
                    }
                } label: {
                    Text(starting ? "Setting up…" : "Start tour")
                        .font(.subheadline.weight(.bold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                }
                .foregroundColor(.white)
                .background(Color.roammateIndigo, in: RoundedRectangle(cornerRadius: 14))
                .disabled(starting)
            }
            .padding(.horizontal, 20).padding(.bottom, 18).padding(.top, 6)
        }
        .background(Color.roammateSurface, in: RoundedRectangle(cornerRadius: 26))
        .shadow(color: Color.black.opacity(0.22), radius: 22, y: 12)
        .padding(.horizontal, 18)
    }
}
