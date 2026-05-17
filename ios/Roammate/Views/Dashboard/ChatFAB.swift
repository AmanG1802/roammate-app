import SwiftUI

struct ChatFAB: View {
    let action: () -> Void
    @State private var isPressed = false

    var body: some View {
        Button(action: {
            HapticManager.medium()
            action()
        }) {
            Image(systemName: "sparkles")
                .font(.system(size: 24, weight: .semibold))
                .foregroundStyle(.white)
                .frame(width: 60, height: 60)
                .background(
                    Circle().fill(
                        LinearGradient(
                            colors: [Color.roammateIndigo, Color.roammateIndigoDark],
                            startPoint: .topLeading, endPoint: .bottomTrailing
                        )
                    )
                )
                .shadow(
                    color: Color.roammateIndigo.opacity(isPressed ? 0.55 : 0.35),
                    radius: isPressed ? 20 : 14, x: 0, y: 6
                )
                .scaleEffect(isPressed ? 0.92 : 1.0)
        }
        .buttonStyle(.plain)
        .animation(.spring(response: 0.3, dampingFraction: 0.7), value: isPressed)
        .simultaneousGesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in isPressed = true }
                .onEnded { _ in isPressed = false }
        )
        .accessibilityLabel("Open AI Concierge")
    }
}
