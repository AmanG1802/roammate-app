import SwiftUI

// MARK: - Per-card model

private struct IntroCardSpec {
    let icon: String
    let accent: Color
    let headline: String
    let body: String
    let flourish: Flourish

    enum Flourish {
        case none
        case roleChips
        case planMiniCards
        case conciergeStoryboard
    }
}

// MARK: - IntroCardsView

struct IntroCardsView: View {
    let onFinish: () -> Void

    @State private var page: Int = 0
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private let cards: [IntroCardSpec] = [
        IntroCardSpec(
            icon: "airplane.circle.fill",
            accent: .roammateIndigo,
            headline: "Welcome to Roammate.",
            body: "The travel planner that travels with you. Swipe to see how.",
            flourish: .none
        ),
        IntroCardSpec(
            icon: "sparkles.rectangle.stack.fill",
            accent: .roammateViolet,
            headline: "From a thought to a plan.",
            body: "Tell our AI what you're craving. It turns loose ideas into a real list of places — with photos, ratings, and addresses ready to schedule.",
            flourish: .none
        ),
        IntroCardSpec(
            icon: "person.3.fill",
            accent: .roammateDanger,
            headline: "Everyone has a voice. One person owns the plan.",
            body: "Invite friends as Admin, Editor, Voter, or Viewer. Vote ideas up. The plan reflects the group — not the loudest chat message.",
            flourish: .roleChips
        ),
        IntroCardSpec(
            icon: "square.grid.3x1.below.line.grid.1x2",
            accent: .roammateEmerald,
            headline: "Timeline. Map. Ideas. One canvas.",
            body: "Drag an idea onto a day. Watch the route appear. Switch days with one tap. Conflicts flag themselves.",
            flourish: .planMiniCards
        ),
        IntroCardSpec(
            icon: "wand.and.sparkles",
            accent: .roammateAmber,
            headline: "Plans change. So does your day.",
            body: "Running late by 45 minutes? Tap once. Roammate reflows the day, finds a coffee near you, and pings the group. Your co-pilot during the trip — not just before it.",
            flourish: .conciergeStoryboard
        ),
        IntroCardSpec(
            icon: "person.crop.circle.badge.checkmark",
            accent: .roammateFuchsia,
            headline: "AI that knows your style.",
            body: "Foodie? Slow traveler? Cultural deep-diver? Pick a persona — the AI tailors every suggestion to you. You can change it anytime.",
            flourish: .none
        ),
    ]

    private var totalPages: Int { cards.count }
    private var isLastPage: Bool { page == totalPages - 1 }
    private var currentAccent: Color { cards[page].accent }

    var body: some View {
        ZStack(alignment: .top) {
            LinearGradient(
                colors: [Color.roammateSurface, currentAccent.opacity(0.08)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
            .animation(.easeInOut(duration: 0.35), value: page)

            VStack(spacing: 0) {
                topBar
                    .padding(.horizontal, RoammateSpacing.lg)
                    .padding(.top, RoammateSpacing.sm)

                TabView(selection: $page) {
                    ForEach(Array(cards.enumerated()), id: \.offset) { idx, spec in
                        IntroCard(spec: spec, indexLabel: "Card \(idx + 1) of \(totalPages)")
                            .tag(idx)
                            .padding(.horizontal, RoammateSpacing.lg)
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: .never))
                .animation(reduceMotion ? .easeInOut(duration: 0.2) : .spring(response: 0.35, dampingFraction: 0.85), value: page)

                pageDots
                    .padding(.vertical, RoammateSpacing.md)

                bottomCTA
                    .padding(.horizontal, RoammateSpacing.lg)
                    .padding(.bottom, RoammateSpacing.lg)
            }
        }
        .onChange(of: page) { _, _ in
            HapticManager.light()
        }
        .accessibilityValue("Page \(page + 1) of \(totalPages)")
    }

    // MARK: - Subviews

    private var topBar: some View {
        HStack {
            Spacer()
            if !isLastPage {
                Button(action: finish) {
                    Text("Skip")
                        .font(.system(size: 15, weight: .semibold, design: .rounded))
                        .foregroundStyle(Color.roammateMuted)
                }
                .accessibilityLabel("Skip intro")
            } else {
                Text(" ").font(.system(size: 15))
            }
        }
        .frame(height: 28)
    }

    private var pageDots: some View {
        HStack(spacing: 8) {
            ForEach(0..<totalPages, id: \.self) { idx in
                Capsule()
                    .fill(idx == page ? Color.roammateIndigo : Color.roammateMuted.opacity(0.3))
                    .frame(width: idx == page ? 22 : 8, height: 8)
                    .animation(.spring(response: 0.35, dampingFraction: 0.85), value: page)
            }
        }
        .accessibilityHidden(true)
    }

    private var bottomCTA: some View {
        Group {
            if isLastPage {
                Button("Get started", action: finish)
                    .buttonStyle(RoammatePrimaryButtonStyle())
            } else {
                Button(action: advance) {
                    Text("Next")
                }
                .buttonStyle(RoammateSecondaryButtonStyle())
            }
        }
    }

    private func advance() {
        guard page < totalPages - 1 else { return }
        if reduceMotion {
            page += 1
        } else {
            withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                page += 1
            }
        }
    }

    private func finish() {
        HapticManager.light()
        onFinish()
    }
}

// MARK: - Single card

private struct IntroCard: View {
    let spec: IntroCardSpec
    let indexLabel: String

    var body: some View {
        VStack(spacing: RoammateSpacing.xl) {
            Spacer(minLength: 0)

            // Icon orb
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [spec.accent.opacity(0.85), spec.accent.opacity(0.55)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 120, height: 120)
                    .shadow(
                        color: spec.accent.opacity(0.35),
                        radius: 16, x: 0, y: 4
                    )
                Image(systemName: spec.icon)
                    .font(.system(size: 56, weight: .semibold))
                    .foregroundStyle(.white)
            }

            VStack(spacing: RoammateSpacing.md) {
                Text(spec.headline)
                    .font(.system(size: 28, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color.roammateInk)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)

                Text(spec.body)
                    .font(.system(size: 17, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(.horizontal, RoammateSpacing.sm)

            flourishView
                .padding(.top, RoammateSpacing.sm)

            Spacer(minLength: 0)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(indexLabel). \(spec.headline). \(spec.body)")
    }

    @ViewBuilder
    private var flourishView: some View {
        switch spec.flourish {
        case .none:
            EmptyView()
        case .roleChips:
            roleChips
        case .planMiniCards:
            planMiniCards
        case .conciergeStoryboard:
            conciergeStoryboard
        }
    }

    private var roleChips: some View {
        HStack(spacing: 8) {
            ForEach(["Admin", "Editor", "Voter", "Viewer"], id: \.self) { role in
                Text(role)
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(spec.accent)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Capsule().fill(spec.accent.opacity(0.12)))
                    .overlay(Capsule().stroke(spec.accent.opacity(0.25), lineWidth: 1))
            }
        }
    }

    private var planMiniCards: some View {
        VStack(spacing: 8) {
            ForEach(0..<3, id: \.self) { i in
                HStack(spacing: 10) {
                    Circle()
                        .fill(spec.accent.opacity(0.85))
                        .frame(width: 8, height: 8)
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.roammateMuted.opacity(0.25))
                        .frame(width: 80 + CGFloat(i * 20), height: 8)
                    Spacer()
                    Text(["09:00", "11:30", "14:00"][i])
                        .font(.system(size: 11, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.roammateMuted)
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 14)
                        .fill(Color.roammateSurface)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Color.roammateBorder, lineWidth: 1)
                )
            }
        }
        .frame(maxWidth: 280)
    }

    private var conciergeStoryboard: some View {
        HStack(spacing: 8) {
            storyboardFrame(icon: "clock.badge.exclamationmark", label: "+45 min")
            Image(systemName: "arrow.right")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(Color.roammateMuted.opacity(0.6))
            storyboardFrame(icon: "arrow.up.arrow.down", label: "Reflow")
            Image(systemName: "arrow.right")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(Color.roammateMuted.opacity(0.6))
            storyboardFrame(icon: "bell.fill", label: "Pinged")
        }
    }

    private func storyboardFrame(icon: String, label: String) -> some View {
        VStack(spacing: 6) {
            ZStack {
                RoundedRectangle(cornerRadius: 14)
                    .fill(spec.accent.opacity(0.15))
                Image(systemName: icon)
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundStyle(spec.accent)
            }
            .frame(width: 64, height: 64)
            Text(label)
                .font(.system(size: 11, weight: .medium, design: .rounded))
                .foregroundStyle(Color.roammateMuted)
        }
    }
}

#Preview {
    IntroCardsView(onFinish: {})
}
