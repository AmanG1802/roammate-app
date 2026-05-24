import SwiftUI

/// Root authenticated shell: a 5-tab experience with a floating pill nav.
/// Each tab hosts its own NavigationStack so push/pop is per-tab.
struct MainShell: View {
    @State private var selection: AppTab = .dashboard
    @StateObject private var tabBarVisibility = TabBarVisibility()
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var subscriptionStore: SubscriptionStore
    @StateObject private var tutorialStore = TutorialStore()
    @State private var showPersonaOnboarding = false
    @State private var personaSheetShownThisSession = false
    @State private var showPlusOnboarding = false
    @State private var previousTier: String?

    var body: some View {
        TutorialCoordinator {
            shellBody
        }
        .environmentObject(tutorialStore)
    }

    private var shellBody: some View {
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
        .onAppear {
            previousTier = subscriptionStore.entitlement.tier
            evaluateOnboarding()
        }
        .onChange(of: authManager.currentUser?.id) { _, _ in evaluateOnboarding() }
        // The guided tour runs on the Dashboard tab — jump there when it starts
        // so steps 1–2 (and the trip we push) land on the right screen.
        .onChange(of: tutorialStore.status) { _, newStatus in
            if newStatus == .inProgress { selection = .dashboard }
        }
        .onChange(of: subscriptionStore.entitlement.tier) { _, newTier in
            // Detect plus → free downgrade; clear the seen flag so the pitch
            // can re-appear on the next free launch.
            if previousTier == "plus", newTier == "free", let uid = authManager.currentUser?.id {
                PlusOnboardingFlag.clear(userId: uid)
            }
            previousTier = newTier
            evaluateOnboarding()
        }
        .sheet(isPresented: $showPersonaOnboarding) {
            OnboardingPersonasSheet(
                onComplete: { _ in
                    showPersonaOnboarding = false
                    // Allow the sheet to dismiss before stacking Plus.
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                        evaluateOnboarding()
                    }
                },
                onSkip: {
                    Task {
                        // Persist empty array so we don't keep prompting next session.
                        try? await AuthService.updatePersonas([])
                        authManager.currentUser = try? await AuthService.getMe()
                    }
                    showPersonaOnboarding = false
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                        evaluateOnboarding()
                    }
                }
            )
        }
        .sheet(isPresented: $showPlusOnboarding) {
            PlusOnboardingSheet(
                onClose: { showPlusOnboarding = false },
                onSeePlus: {
                    showPlusOnboarding = false
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

    /// Decide which onboarding sheet (if any) to present. Persona picker takes
    /// precedence; the Plus pitch waits until the persona flow is done.
    private func evaluateOnboarding() {
        guard let user = authManager.currentUser else { return }

        // Tutorial gate: block persona + Plus pitches until the tour ends.
        if tutorialStore.status == .notStarted || tutorialStore.status == .inProgress {
            return
        }

        // 1. Persona picker — once per session when personas are unset/empty.
        let needsPersona = (user.personas?.isEmpty ?? true)
        if needsPersona, !personaSheetShownThisSession, !showPersonaOnboarding {
            personaSheetShownThisSession = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                showPersonaOnboarding = true
            }
            return
        }

        // 2. Plus onboarding — only for free users, once per device. Defer if
        // the persona sheet is currently open.
        guard !showPersonaOnboarding else { return }
        guard subscriptionStore.entitlement.tier == "free" else { return }
        guard !PlusOnboardingFlag.hasSeen(userId: user.id) else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
            // Re-check after the delay — the user's state may have changed.
            guard subscriptionStore.entitlement.tier == "free",
                  !PlusOnboardingFlag.hasSeen(userId: user.id) else { return }
            PlusOnboardingFlag.markSeen(userId: user.id)
            showPlusOnboarding = true
        }
    }
}
