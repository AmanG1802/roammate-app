import SwiftUI

private enum TransitionState { case idle, introExiting, loginExiting }

struct ContentView: View {
    @EnvironmentObject var authManager: AuthManager
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var introSeen: Bool = IntroCardsFlag.hasSeen()
    @State private var transitionState: TransitionState = .idle
    @State private var foregroundSlideY: CGFloat = 0
    @State private var airplaneY: CGFloat = -80
    @State private var airplaneVisible: Bool = false

    var body: some View {
        Group {
            if authManager.isAuthenticated {
                MainShell()
            } else {
                // NOTE: the GeometryReader must NOT ignore the safe area, or
                // `geo.safeAreaInsets` collapses to .zero. We read the real insets,
                // then re-expand to a full-screen size for the full-bleed layers
                // (which ignore the safe area themselves and inset manually).
                GeometryReader { geo in
                    let insets = geo.safeAreaInsets
                    let fullSize = CGSize(
                        width: geo.size.width + insets.leading + insets.trailing,
                        height: geo.size.height + insets.top + insets.bottom
                    )
                    ZStack {
                        // Layer 1 — Login
                        // Visible when: user has seen intro (idle), or login is flying out (loginExiting)
                        if introSeen || transitionState == .introExiting {
                            LoginView(onReplayIntro: { triggerAirplaneEnter(size: fullSize) },
                                      safeAreaTop: insets.top)
                                .frame(width: fullSize.width, height: fullSize.height)
                                .offset(y: transitionState == .loginExiting ? foregroundSlideY : 0)
                                .zIndex(transitionState == .loginExiting ? 1 : 0)
                        }

                        // Layer 2 — Intro cards
                        // Visible when: first run (idle), or intro is flying out (introExiting)
                        if !introSeen || transitionState == .loginExiting {
                            IntroCardsView(
                                onFinish: {
                                    IntroCardsFlag.markSeen()
                                    introSeen = true
                                },
                                onAnimatedFinish: { triggerAirplaneExit(size: fullSize) },
                                safeAreaTop: insets.top,
                                safeAreaBottom: insets.bottom
                            )
                            .frame(width: fullSize.width, height: fullSize.height)
                            .offset(y: transitionState == .introExiting ? foregroundSlideY : 0)
                            .zIndex(transitionState == .loginExiting ? 0 : 1)
                        }

                        // Layer 3 — Blur scrim + airplane (only during transition)
                        if airplaneVisible {
                            // Scrim: blurs the static background layer so the plane reads clearly.
                            // Only needed when flying from the light login page (loginExiting),
                            // since the indigo last-card already provides enough contrast.
                            if transitionState == .loginExiting {
                                Rectangle()
                                    .fill(.ultraThinMaterial)
                                    .ignoresSafeArea()
                                    .zIndex(1.5)
                            }

                            airplaneView(size: fullSize)
                                .zIndex(2)
                        }
                    }
                    .frame(width: fullSize.width, height: fullSize.height)
                    .ignoresSafeArea()
                }
            }
        }
        .animation(.easeInOut(duration: 0.25), value: authManager.isAuthenticated)
        .observePaywall()
    }

    // MARK: - Airplane view

    private func airplaneView(size: CGSize) -> some View {
        // White on the dark indigo last card; indigo on the light login page (with blur scrim behind)
        let color: Color = transitionState == .introExiting ? .white : .roammateIndigo
        return Image(systemName: "airplane")
            .font(.system(size: 56, weight: .bold))
            .foregroundStyle(color)
            .rotationEffect(.degrees(90))
            .shadow(color: color.opacity(0.5), radius: 20, y: 8)
            .position(x: size.width / 2, y: airplaneY)
    }

    // MARK: - Intro → Login

    private func triggerAirplaneExit(size: CGSize) {
        guard transitionState == .idle else { return }

        if reduceMotion {
            HapticManager.light()
            IntroCardsFlag.markSeen()
            introSeen = true
            return
        }

        transitionState = .introExiting
        airplaneY = -80
        airplaneVisible = true

        // Phase 1: airplane swoops into view from above
        withAnimation(.easeOut(duration: 0.35)) {
            airplaneY = size.height * 0.3
        }

        // Phase 2: airplane + intro card fly off bottom together
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            withAnimation(.easeIn(duration: 1.4)) {
                airplaneY = size.height + 100
                foregroundSlideY = size.height + 80
            }
        }

        // Completion: swap to login, clean up
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.7) {
            HapticManager.light()
            IntroCardsFlag.markSeen()
            introSeen = true
            transitionState = .idle
            foregroundSlideY = 0
            airplaneVisible = false
            airplaneY = -80
        }
    }

    // MARK: - Login → Intro

    private func triggerAirplaneEnter(size: CGSize) {
        guard transitionState == .idle else { return }

        if reduceMotion {
            HapticManager.light()
            introSeen = false
            return
        }

        // Intro cards appear in ZStack behind login (loginExiting gives login zIndex 1)
        introSeen = false
        transitionState = .loginExiting
        airplaneY = -80
        airplaneVisible = true

        // Phase 1: airplane swoops into view from above
        withAnimation(.easeOut(duration: 0.35)) {
            airplaneY = size.height * 0.3
        }

        // Phase 2: airplane + login fly off bottom together
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            withAnimation(.easeIn(duration: 1.4)) {
                airplaneY = size.height + 100
                foregroundSlideY = size.height + 80
            }
        }

        // Completion: swap to intro, clean up
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.7) {
            HapticManager.light()
            transitionState = .idle
            foregroundSlideY = 0
            airplaneVisible = false
            airplaneY = -80
        }
    }
}
