import SwiftUI

// MARK: - Per-card background

/// Drives both the full-bleed background (in the shell) and the adaptive
/// text/chrome colors (in the scaffold). Mirrors the web landing: most
/// sections are light with a tint, Concierge is dark, Ready-to-Roam is indigo.
enum IntroBackground: Equatable {
    case lightTint(Color)   // associated value = the section accent used for the soft gradient
    case dark               // slate-900 (roammateInk) — Concierge
    case indigo             // full indigo — Ready to Roam finale
    case conciergeLight     // solid indigo-50 — Concierge (matches web `bg-indigo-50` section)

    var isDark: Bool {
        switch self {
        case .lightTint, .conciergeLight: return false
        case .dark, .indigo:              return true
        }
    }

    /// The full-screen fill, drawn behind every card by the shell.
    @ViewBuilder
    func fill() -> some View {
        switch self {
        case .lightTint(let accent):
            LinearGradient(
                colors: [Color.roammateSurface, accent.opacity(0.10)],
                startPoint: .top,
                endPoint: .bottom
            )
        case .dark:
            Color.roammateInk
        case .indigo:
            LinearGradient(
                colors: [Color.roammateIndigo, Color.roammateIndigoDark],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        case .conciergeLight:
            Color.roammateIndigoTint
        }
    }

    /// Primary text color (headline lead, etc.).
    var ink: Color { isDark ? .white : .roammateInk }

    /// Secondary text color (body copy).
    var secondary: Color {
        switch self {
        case .lightTint:    return .roammateMuted
        case .dark:         return .white.opacity(0.72)
        case .indigo:        return .white.opacity(0.88)
        case .conciergeLight: return .roammateMuted
        }
    }

    /// Eyebrow pill background.
    func eyebrowBackground(_ tint: Color) -> Color {
        switch self {
        // Deeper indigo pill so it reads against the solid indigo-50 fill (matches web `bg-indigo-100`).
        case .conciergeLight: return Color.roammateIndigo.opacity(0.12)
        default:              return isDark ? Color.white.opacity(0.14) : tint
        }
    }
}

// MARK: - Mockup selector

enum IntroMockup {
    case welcome
    case brainstorm
    case ideaBin
    case planMode
    case concierge
    case personas
    case plus
    case ready
}

// MARK: - Card spec

struct IntroCardSpec: Identifiable {
    let id = UUID()
    var eyebrow: String? = nil
    var eyebrowIcon: String? = nil
    /// Accent color for the eyebrow text + the highlighted headline phrase.
    var accent: Color
    /// Eyebrow pill background on light cards.
    var accentTint: Color = .clear
    var headlineLead: String
    var headlineAccent: String
    var accentItalic: Bool = false
    var body: String? = nil
    var subtitle: String? = nil
    var background: IntroBackground
    var mockup: IntroMockup
    var headlineSize: CGFloat = 30
    /// Center the headline/body (Welcome + Ready-to-Roam).
    var centered: Bool = false
    /// When true, renders airplane icon + "Roammate" above the headline instead of the eyebrow pill.
    var showLogoLockup: Bool = false
    /// When false, skips IntroMockupView entirely (Welcome, Ready-to-Roam).
    var showMockup: Bool = true

    var accessibilityText: String {
        [eyebrow, "\(headlineLead)\(headlineAccent)", subtitle, body]
            .compactMap { $0 }
            .joined(separator: ". ")
    }
}

// MARK: - Card scaffold

/// Lays out a single intro card: eyebrow/logo → headline → subtitle → body → mockup,
/// with a staggered entrance when the card becomes the active page.
struct IntroCardView: View {
    let spec: IntroCardSpec
    let index: Int
    let total: Int
    let isActive: Bool

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var revealed = false

    private var alignment: HorizontalAlignment { spec.centered ? .center : .leading }
    private var textAlignment: TextAlignment { spec.centered ? .center : .leading }

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: alignment, spacing: RoammateSpacing.lg) {
                Spacer(minLength: RoammateSpacing.md)

                if spec.showLogoLockup {
                    logoLockup
                        .modifier(Reveal(revealed: revealed, order: 0, reduceMotion: reduceMotion))
                } else if let eyebrow = spec.eyebrow {
                    eyebrowPill(eyebrow)
                        .modifier(Reveal(revealed: revealed, order: 0, reduceMotion: reduceMotion))
                }

                headline
                    .modifier(Reveal(revealed: revealed, order: 1, reduceMotion: reduceMotion))

                if let subtitle = spec.subtitle {
                    Text(subtitle)
                        .font(.system(.body, design: .rounded))
                        .foregroundStyle(spec.background.secondary)
                        .multilineTextAlignment(textAlignment)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: spec.centered ? 360 : .infinity,
                               alignment: spec.centered ? .center : .leading)
                        .modifier(Reveal(revealed: revealed, order: 2, reduceMotion: reduceMotion))
                }

                if let body = spec.body {
                    Text(body)
                        .font(.system(size: 16, design: .rounded))
                        .foregroundStyle(spec.background.secondary)
                        .multilineTextAlignment(textAlignment)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: spec.centered ? 360 : .infinity,
                               alignment: spec.centered ? .center : .leading)
                        .modifier(Reveal(revealed: revealed, order: 3, reduceMotion: reduceMotion))
                }

                if spec.showMockup {
                    IntroMockupView(mockup: spec.mockup, accent: spec.accent)
                        .frame(maxWidth: .infinity)
                        .padding(.top, RoammateSpacing.xs)
                        .modifier(Reveal(revealed: revealed, order: 4, reduceMotion: reduceMotion))
                }

                Spacer(minLength: RoammateSpacing.md)
            }
            .frame(maxWidth: .infinity, alignment: spec.centered ? .center : .leading)
            .frame(minHeight: scrollMinHeight)
        }
        .scrollBounceBehavior(.basedOnSize)
        .onChange(of: isActive) { _, active in
            if active { triggerReveal() } else { revealed = false }
        }
        .onAppear { if isActive { triggerReveal() } }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Card \(index + 1) of \(total). \(spec.accessibilityText)")
    }

    private var scrollMinHeight: CGFloat { 460 }

    private func triggerReveal() {
        if reduceMotion {
            revealed = true
        } else {
            withAnimation(.spring(response: 0.5, dampingFraction: 0.85)) {
                revealed = true
            }
        }
    }

    // MARK: Logo lockup (Card 1)

    private var logoLockup: some View {
        HStack(spacing: 12) {
            Image(systemName: "airplane.circle.fill")
                .font(.system(size: 44))
                .foregroundStyle(Color.roammateIndigo)
            Text("Roammate")
                .font(.system(.largeTitle, design: .rounded, weight: .black))
                .foregroundStyle(Color.roammateInk)
        }
    }

    // MARK: Eyebrow

    private func eyebrowPill(_ text: String) -> some View {
        HStack(spacing: 6) {
            if let icon = spec.eyebrowIcon {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .bold))
            }
            Text(text.uppercased())
                .font(.system(size: 12, weight: .bold))
                .tracking(1.4)
        }
        .foregroundStyle(spec.accent)
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Capsule().fill(spec.background.eyebrowBackground(spec.accentTint)))
    }

    // MARK: Headline

    private var headline: some View {
        let accentText = spec.accentItalic
            ? Text(spec.headlineAccent).italic()
            : Text(spec.headlineAccent)
        return (
            Text(spec.headlineLead).foregroundColor(spec.background.ink)
            + accentText.foregroundColor(spec.accent)
        )
        .font(.system(size: spec.headlineSize, weight: .black))
        .tracking(-0.5)
        .multilineTextAlignment(textAlignment)
        .lineSpacing(2)
        .fixedSize(horizontal: false, vertical: true)
        .minimumScaleFactor(0.8)
        .frame(maxWidth: .infinity, alignment: spec.centered ? .center : .leading)
    }
}

// MARK: - Staggered reveal modifier

private struct Reveal: ViewModifier {
    let revealed: Bool
    let order: Int
    let reduceMotion: Bool

    func body(content: Content) -> some View {
        content
            .opacity(revealed ? 1 : 0)
            .offset(y: (revealed || reduceMotion) ? 0 : 14)
            .animation(
                reduceMotion
                    ? .easeOut(duration: 0.2)
                    : .spring(response: 0.5, dampingFraction: 0.85).delay(Double(order) * 0.06),
                value: revealed
            )
    }
}
