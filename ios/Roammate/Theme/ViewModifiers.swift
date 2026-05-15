import SwiftUI

// MARK: - Tab bar visibility

final class TabBarVisibility: ObservableObject {
    @Published var isVisible: Bool = true
}

private struct TabBarVisibilityKey: EnvironmentKey {
    static let defaultValue: TabBarVisibility = TabBarVisibility()
}

extension EnvironmentValues {
    var tabBarVisibility: TabBarVisibility {
        get { self[TabBarVisibilityKey.self] }
        set { self[TabBarVisibilityKey.self] = newValue }
    }
}

// MARK: - Card / surface

struct RoammateCardModifier: ViewModifier {
    var radius: CGFloat = RoammateRadius.card
    var padding: CGFloat = RoammateSpacing.md

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(
                RoundedRectangle(cornerRadius: radius, style: .continuous)
                    .fill(Color.roammateSurface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: radius, style: .continuous)
                    .stroke(Color.roammateBorder, lineWidth: 1)
            )
            .shadow(
                color: RoammateShadow.card.color,
                radius: RoammateShadow.card.radius,
                x: RoammateShadow.card.x, y: RoammateShadow.card.y
            )
    }
}

extension View {
    func roammateCard(
        radius: CGFloat = RoammateRadius.card,
        padding: CGFloat = RoammateSpacing.md
    ) -> some View {
        modifier(RoammateCardModifier(radius: radius, padding: padding))
    }
}

// MARK: - Filled indigo CTA

struct RoammatePrimaryButtonStyle: ButtonStyle {
    var isLoading: Bool = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(.body, design: .rounded, weight: .semibold))
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(
                Capsule().fill(
                    isLoading
                        ? Color.roammateIndigo.opacity(0.7)
                        : (configuration.isPressed ? Color.roammateIndigoDark : Color.roammateIndigo)
                )
            )
            .shadow(
                color: RoammateShadow.indigoGlow.color,
                radius: RoammateShadow.indigoGlow.radius,
                x: 0, y: RoammateShadow.indigoGlow.y
            )
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.7), value: configuration.isPressed)
    }
}

// MARK: - Outlined secondary button

struct RoammateSecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(.body, design: .rounded, weight: .semibold))
            .foregroundStyle(Color.roammateInk)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(
                Capsule().fill(Color.roammateSurface)
            )
            .overlay(
                Capsule().stroke(Color.roammateBorder, lineWidth: 1.5)
            )
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.7), value: configuration.isPressed)
    }
}

// MARK: - Glass blur (matches web `bg-white/90 backdrop-blur-xl`)

struct GlassBlurModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(.ultraThinMaterial)
            .overlay(
                Capsule().stroke(Color.white.opacity(0.6), lineWidth: 0.5)
            )
    }
}

extension View {
    func glassBlur() -> some View { modifier(GlassBlurModifier()) }
}

// MARK: - Row press style (for NavigationLink-wrapped cards)
//
// Using a ButtonStyle (which reads `configuration.isPressed`) instead of a
// DragGesture modifier avoids consuming the tap and breaking NavigationLink.

struct RoammateRowButtonStyle: ButtonStyle {
    var scale: CGFloat = 0.97

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? scale : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.7), value: configuration.isPressed)
    }
}

// MARK: - Section header

struct SectionHeader: View {
    let title: String
    var trailing: (() -> AnyView)? = nil

    var body: some View {
        HStack {
            Text(title)
                .font(.system(.title3, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateInk)
            Spacer()
            trailing?()
        }
        .padding(.horizontal, RoammateSpacing.md)
    }
}

// MARK: - Pill / tag

struct PillLabel: View {
    let text: String
    var background: Color = .roammateIndigoTint
    var foreground: Color = .roammateIndigo

    var body: some View {
        Text(text)
            .font(.system(.caption, design: .rounded, weight: .semibold))
            .foregroundStyle(foreground)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(Capsule().fill(background))
    }
}

// MARK: - Empty state container

struct EmptyState: View {
    let icon: String
    let title: String
    let subtitle: String?

    init(icon: String, title: String, subtitle: String? = nil) {
        self.icon = icon
        self.title = title
        self.subtitle = subtitle
    }

    var body: some View {
        VStack(spacing: RoammateSpacing.sm) {
            Image(systemName: icon)
                .font(.system(size: 40, weight: .regular))
                .foregroundStyle(Color.roammateMuted)
            Text(title)
                .font(.system(.headline, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.roammateInk)
            if let subtitle {
                Text(subtitle)
                    .font(.system(.subheadline, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
                    .multilineTextAlignment(.center)
            }
        }
        .padding(RoammateSpacing.xl)
        .frame(maxWidth: .infinity)
    }
}
