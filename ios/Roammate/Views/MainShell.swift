import SwiftUI

/// Root authenticated shell: a 5-tab experience with a floating pill nav.
/// Each tab hosts its own NavigationStack so push/pop is per-tab.
struct MainShell: View {
    @State private var selection: AppTab = .dashboard
    @StateObject private var tabBarVisibility = TabBarVisibility()
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var subscriptionStore: SubscriptionStore
    @State private var showPlusOnboarding = false
    @State private var showPaywallFromOnboarding = false

    var body: some View {
        ZStack(alignment: .bottom) {
            Color.roammateBackground.ignoresSafeArea()

            Group {
                switch selection {
                case .dashboard:   DashboardView()
                case .trips:       TripsTabView()
                case .invitations: InvitationsTabView()
                case .groups:      GroupsTabView()
                case .profile:     ProfileTabView()
                }
            }
            .transition(.opacity)
            .animation(.easeInOut(duration: 0.18), value: selection)

            if tabBarVisibility.isVisible {
                FloatingTabBar(selection: $selection)
                    .padding(.bottom, RoammateLayout.tabBarBottomInset)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .animation(.spring(response: 0.35, dampingFraction: 0.85), value: tabBarVisibility.isVisible)
        .environment(\.tabBarVisibility, tabBarVisibility)
        .environmentObject(tabBarVisibility)
        .onAppear { maybeShowOnboarding() }
        .sheet(isPresented: $showPlusOnboarding) {
            PlusOnboardingSheet(
                onClose: { showPlusOnboarding = false },
                onSeePlus: {
                    showPlusOnboarding = false
                    // Wait a beat for the sheet to dismiss before posting
                    // .needsPlus, otherwise iOS may swallow the new sheet.
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                        NotificationCenter.default.post(
                            name: .needsPlus,
                            object: nil,
                            userInfo: ["feature": PaywallFeature.concierge.rawValue]
                        )
                    }
                }
            )
        }
    }

    /// Show Plus onboarding once per user. Guarded by an AppStorage flag keyed
    /// off the user id so a sign-out → sign-in with a different account
    /// re-triggers naturally.
    private func maybeShowOnboarding() {
        guard let uid = authManager.currentUser?.id else { return }
        let key = "plus_onboarding_shown_\(uid)"
        let defaults = UserDefaults.standard
        if defaults.bool(forKey: key) { return }
        // Let the dashboard settle, then present.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
            showPlusOnboarding = true
            defaults.set(true, forKey: key)
        }
    }
}
