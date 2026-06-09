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
        // A genuine free user's tier never changes from the default "free", so
        // the tier onChange above won't fire for them — re-evaluate once the
        // entitlement is actually confirmed.
        .onChange(of: subscriptionStore.isConfirmed) { _, _ in evaluateOnboarding() }
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

    /// Decide which onboarding sheet (if any) to present.
    /// Order: Tour (blocks both) → Plus pitch → Persona picker.
    private func evaluateOnboarding() {
        guard let user = authManager.currentUser else { return }

        // Tutorial gate: block persona + Plus pitches until the tour ends.
        if tutorialStore.status == .notStarted || tutorialStore.status == .inProgress {
            return
        }

        // Require a confirmed entitlement before showing anything: the optimistic
        // default is tier "free", so acting before confirmation would upsell a
        // paying user whose status hasn't loaded yet.
        guard subscriptionStore.isConfirmed else { return }

        // 1. Plus onboarding — free users see this first, once per device.
        if subscriptionStore.entitlement.tier == "free",
           !PlusOnboardingFlag.hasSeen(userId: user.id),
           !showPlusOnboarding {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                // Re-check after the delay — state may have changed.
                guard subscriptionStore.isConfirmed,
                      subscriptionStore.entitlement.tier == "free",
                      !PlusOnboardingFlag.hasSeen(userId: user.id) else { return }
                PlusOnboardingFlag.markSeen(userId: user.id)
                showPlusOnboarding = true
            }
            return
        }

        // 2. Persona picker — once per session when personas are unset/empty.
        // Only shown after the Plus sheet has been seen (or skipped for Plus users).
        guard !showPlusOnboarding else { return }
        let needsPersona = (user.personas?.isEmpty ?? true)
        if needsPersona, !personaSheetShownThisSession, !showPersonaOnboarding {
            personaSheetShownThisSession = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                showPersonaOnboarding = true
            }
        }
    }
}
