import SwiftUI

struct SubscriptionView: View {
    var body: some View {
        ZStack {
            Color.roammateBackground.ignoresSafeArea()

            VStack(spacing: RoammateSpacing.md) {
                Spacer()

                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                colors: [Color.roammateIndigoTint, Color.roammateIndigo.opacity(0.15)],
                                startPoint: .topLeading, endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 120, height: 120)
                    Image(systemName: "sparkles.rectangle.stack.fill")
                        .font(.system(size: 50))
                        .foregroundStyle(Color.roammateIndigo)
                }

                VStack(spacing: 6) {
                    Text("Roammate Plus")
                        .font(.system(.title2, design: .rounded, weight: .black))
                        .foregroundStyle(Color.roammateInk)
                    Text("Coming soon")
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.roammateIndigo)
                }

                Text("Unlimited concierge chats, smarter itinerary ripples, and group spending insights are on the way.")
                    .font(.system(.subheadline, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, RoammateSpacing.xl)

                Spacer()
            }
        }
        .navigationTitle("Subscription")
        .navigationBarTitleDisplayMode(.inline)
    }
}
