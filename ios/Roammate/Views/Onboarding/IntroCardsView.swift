import SwiftUI

// MARK: - IntroCardsView
//
// Once-per-install onboarding carousel. Mirrors the web landing page:
// Welcome → Brainstorm → Idea Bin → Plan Mode → Concierge → Personas →
// Roammate Plus → Ready to Roam. Each card has a web-matched eyebrow,
// heavy tracking-tight headline with a colored accent phrase, body copy,
// and a high-fidelity mini-mockup.

struct IntroCardsView: View {
    let onFinish: () -> Void
    var onAnimatedFinish: (() -> Void)? = nil
    var safeAreaTop: CGFloat = 0
    var safeAreaBottom: CGFloat = 0

    @State private var page: Int = 0
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private let cards: [IntroCardSpec] = [
        // Card 1 — Welcome
        IntroCardSpec(
            accent: .roammateIndigo,
            accentTint: .roammateIndigoTint,
            headlineLead: "The travel planner that ",
            headlineAccent: "travels with you.",
            background: .lightTint(.roammateIndigo),
            mockup: .welcome,
            headlineSize: 36,
            centered: true,
            showLogoLockup: true,
            showMockup: false
        ),
        // Card 2 — Brainstorm
        IntroCardSpec(
            eyebrow: "Brainstorm", eyebrowIcon: "sparkles",
            accent: .roammateViolet, accentTint: .roammateVioletTint,
            headlineLead: "Turn loose ideas into ",
            headlineAccent: "a real plan.",
            body: "Tell our AI what you're craving. It comes back with real places.",
            background: .lightTint(.roammateViolet),
            mockup: .brainstorm,
            headlineSize: 36
        ),
        // Card 3 — Idea Bin
        IntroCardSpec(
            eyebrow: "Idea Bin + Voting",
            accent: .roammateIndigo, accentTint: .roammateIndigoTint,
            headlineLead: "Group input without ",
            headlineAccent: "group chat chaos.",
            body: "Everyone's ideas land in one shared bin. Vote them up — or down. The plan reflects the group, not the loudest voice on WhatsApp.",
            background: .lightTint(.roammateIndigo),
            mockup: .ideaBin
        ),
        // Card 4 — Plan Mode
        IntroCardSpec(
            eyebrow: "Plan Mode", eyebrowIcon: "square.stack.3d.up.fill",
            accent: .roammateIndigo, accentTint: .roammateIndigoTint,
            headlineLead: "Timeline. Map. Ideas. ",
            headlineAccent: "One canvas.",
            body: "Drag an idea onto a day. Pick a time. The route emerges on the map. That's it.",
            background: .lightTint(.roammateIndigo),
            mockup: .planMode
        ),
        // Card 5 — Concierge
        IntroCardSpec(
            eyebrow: "Concierge", eyebrowIcon: "wand.and.sparkles",
            accent: .roammateIndigo, accentTint: .roammateIndigoTint,
            headlineLead: "Plans change. So does ",
            headlineAccent: "your day.",
            subtitle: "Your co-pilot during the trip.",
            background: .conciergeLight,
            mockup: .concierge,
            headlineSize: 36
        ),
        // Card 6 — Personas
        IntroCardSpec(
            eyebrow: "Personas", eyebrowIcon: "sparkles",
            accent: .roammateFuchsia, accentTint: .roammateFuchsiaTint,
            headlineLead: "AI that knows ",
            headlineAccent: "your style.",
            body: "Foodie, cultural deep-diver, slow traveler — pick a persona and every suggestion tilts to match. Same prompt, different answer.",
            background: .lightTint(.roammateFuchsia),
            mockup: .personas
        ),
        // Card 7 — Roammate Plus
        IntroCardSpec(
            eyebrow: "Roammate Plus", eyebrowIcon: "sparkles",
            accent: .roammateIndigo, accentTint: .roammateIndigoTint,
            headlineLead: "Free to start. ",
            headlineAccent: "Plus when you outgrow it.",
            body: "Every core feature works for free. Plus removes the limits.",
            background: .lightTint(.roammateIndigo),
            mockup: .plus
        ),
        // Card 8 — Ready to Roam
        IntroCardSpec(
            accent: .roammateIndigo200,
            headlineLead: "Ready to ",
            headlineAccent: "Roam?",
            accentItalic: true,
            background: .indigo,
            mockup: .ready,
            headlineSize: 64,
            centered: true,
            showMockup: false
        ),
    ]

    private var totalPages: Int { cards.count }
    private var isLastPage: Bool { page == totalPages - 1 }
    private var currentBackground: IntroBackground { cards[page].background }
    private var isDark: Bool { currentBackground.isDark }

    var body: some View {
        ZStack {
            currentBackground.fill()
                .ignoresSafeArea()
                .transition(.opacity)
                .id(page)

            VStack(spacing: 0) {
                topBar
                    .padding(.horizontal, RoammateSpacing.lg)
                    .padding(.top, safeAreaTop + RoammateSpacing.sm)

                TabView(selection: $page) {
                    ForEach(Array(cards.enumerated()), id: \.offset) { idx, spec in
                        IntroCardView(spec: spec, index: idx, total: totalPages, isActive: page == idx)
                            .tag(idx)
                            .padding(.horizontal, RoammateSpacing.lg)
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: .never))
                .animation(reduceMotion ? .easeInOut(duration: 0.2) : .spring(response: 0.4, dampingFraction: 0.85), value: page)

                pageDots
                    .padding(.vertical, RoammateSpacing.md)

                bottomCTA
                    .padding(.horizontal, RoammateSpacing.lg)
                    .padding(.bottom, max(safeAreaBottom, RoammateSpacing.lg) + RoammateSpacing.lg)
            }
        }
        .animation(.easeInOut(duration: 0.4), value: page)
        .onChange(of: page) { _, _ in HapticManager.light() }
        .accessibilityValue("Page \(page + 1) of \(totalPages)")
    }

    // MARK: - Top bar (Skip)

    private var topBar: some View {
        HStack {
            Spacer()
            if !isLastPage {
                Button(action: finish) {
                    Text("Skip")
                        .font(.system(size: 15, weight: .semibold, design: .rounded))
                        .foregroundStyle(isDark ? Color.white.opacity(0.85) : Color.roammateMuted)
                }
                .accessibilityLabel("Skip intro")
            } else {
                Text(" ").font(.system(size: 15))
            }
        }
        .frame(height: 28)
        .animation(.easeInOut(duration: 0.3), value: isDark)
    }

    // MARK: - Page dots

    private var pageDots: some View {
        HStack(spacing: 8) {
            ForEach(0..<totalPages, id: \.self) { idx in
                Capsule()
                    .fill(dotColor(active: idx == page))
                    .frame(width: idx == page ? 22 : 8, height: 8)
                    .animation(.spring(response: 0.35, dampingFraction: 0.85), value: page)
            }
        }
        .accessibilityHidden(true)
    }

    private func dotColor(active: Bool) -> Color {
        if active { return isDark ? .white : .roammateIndigo }
        return (isDark ? Color.white : Color.roammateMuted).opacity(0.3)
    }

    // MARK: - Bottom CTA

    private var bottomCTA: some View {
        Group {
            if isLastPage {
                Button(action: handleFinish) {
                    HStack(spacing: 8) {
                        Text("Start Your First Trip")
                        Image(systemName: "safari")
                    }
                }
                .buttonStyle(IntroFinishButtonStyle())
            } else {
                Button("Next", action: advance)
                    .buttonStyle(IntroNextButtonStyle(isDark: isDark))
            }
        }
    }

    // MARK: - Actions

    private func advance() {
        guard page < totalPages - 1 else { return }
        if reduceMotion {
            page += 1
        } else {
            withAnimation(.spring(response: 0.4, dampingFraction: 0.85)) { page += 1 }
        }
    }

    private func finish() {
        HapticManager.light()
        onFinish()
    }

    private func handleFinish() {
        HapticManager.light()
        if let animated = onAnimatedFinish {
            animated()
        } else {
            onFinish()
        }
    }
}

// MARK: - Adaptive button styles

/// "Next" button — outlined; adapts to light vs dark (Concierge) backgrounds.
private struct IntroNextButtonStyle: ButtonStyle {
    let isDark: Bool

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(.body, design: .rounded, weight: .semibold))
            .foregroundStyle(isDark ? Color.white : Color.roammateInk)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(Capsule().fill(isDark ? Color.white.opacity(0.12) : Color.roammateSurface))
            .overlay(Capsule().stroke(isDark ? Color.white.opacity(0.4) : Color.roammateBorder, lineWidth: 1.5))
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.7), value: configuration.isPressed)
    }
}

/// Final CTA on the indigo finale — white fill, indigo text (matches web).
private struct IntroFinishButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(.body, design: .rounded, weight: .bold))
            .foregroundStyle(configuration.isPressed ? Color.roammateIndigoDark : Color.roammateIndigo)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(Capsule().fill(Color.white))
            .shadow(color: Color.black.opacity(0.18), radius: 14, y: 6)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.7), value: configuration.isPressed)
    }
}

#Preview {
    IntroCardsView(onFinish: {})
}
