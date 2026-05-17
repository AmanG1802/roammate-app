import SwiftUI

/// View modifier that listens for `.needsPlus` notifications (posted by
/// `APIClient` on 402 responses) and presents the `PaywallSheet` once.
///
/// Mount once on the root view: `ContentView().observePaywall()`.
struct PaywallObserverModifier: ViewModifier {
    @State private var pending: PendingPaywall?

    private struct PendingPaywall: Identifiable {
        let id = UUID()
        let feature: PaywallFeature
        let preferredPlan: PaywallPreferredPlan
    }

    func body(content: Content) -> some View {
        content
            .onReceive(NotificationCenter.default.publisher(for: .needsPlus)) { note in
                let code = note.userInfo?["feature"] as? String
                let feature = PaywallFeature(rawValue: code ?? "concierge") ?? .concierge
                let planRaw = note.userInfo?["preferredPlan"] as? String
                let plan = PaywallPreferredPlan(rawValue: planRaw ?? "monthly") ?? .monthly
                pending = PendingPaywall(feature: feature, preferredPlan: plan)
            }
            .sheet(item: $pending) { p in
                PaywallSheet(feature: p.feature, preferredPlan: p.preferredPlan) { _ in
                    pending = nil
                }
            }
    }
}

extension PaywallFeature: Identifiable {
    public var id: String { rawValue }
}

extension View {
    /// Auto-present the paywall sheet on `.needsPlus` notifications.
    func observePaywall() -> some View {
        modifier(PaywallObserverModifier())
    }
}
