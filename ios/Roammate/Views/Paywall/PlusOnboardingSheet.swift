import SwiftUI

/// Two-step onboarding sheet that follows the persona picker:
///   A. "Here's what you can do free"  — sets free-tier expectations
///   B. "Want the full Roammate?"      — soft Plus pitch (skippable)
///
/// One-time per user. Triggered from the home tab after sign-up; guarded by
/// `@AppStorage("plus_onboarding_shown_<userId>")` so it never re-shows.
struct PlusOnboardingSheet: View {
    let onClose: () -> Void
    let onSeePlus: () -> Void

    @State private var step: Step = .free
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    enum Step { case free, plus }

    var body: some View {
        VStack(spacing: 0) {
            // Drag-grabber-style header with skip
            HStack {
                Spacer()
                Button { onClose() } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color.roammateMuted)
                        .frame(width: 28, height: 28)
                        .background(Circle().fill(Color.roammateBackground))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, RoammateSpacing.md)
            .padding(.top, RoammateSpacing.md)

            ZStack {
                if step == .free {
                    freeContent
                        .transition(.asymmetric(
                            insertion: .move(edge: .trailing).combined(with: .opacity),
                            removal: .move(edge: .leading).combined(with: .opacity)
                        ))
                } else {
                    plusContent
                        .transition(.asymmetric(
                            insertion: .move(edge: .trailing).combined(with: .opacity),
                            removal: .move(edge: .leading).combined(with: .opacity)
                        ))
                }
            }
            .animation(.spring(response: 0.35, dampingFraction: 0.85), value: step)
        }
        .background(Color.roammateSurface)
        .presentationDetents([.fraction(0.75), .large])
        .presentationDragIndicator(.visible)
    }

    // MARK: - Step A: free explainer

    private var freeContent: some View {
        VStack(spacing: RoammateSpacing.md) {
            HStack {
                Text("YOU'RE IN")
                    .font(.caption2.weight(.black))
                    .tracking(1)
                    .foregroundStyle(Color.roammateEmerald)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(Color.roammateEmeraldTint))
                Spacer()
            }
            .padding(.horizontal, RoammateSpacing.lg)
            .padding(.top, RoammateSpacing.xs)

            Text("Here's what you can do — free.")
                .font(.system(.title2, design: .rounded, weight: .black))
                .foregroundStyle(Color.roammateInk)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, RoammateSpacing.lg)

            Text("No card, no clock. Plan, brainstorm, and explore on us.")
                .font(.subheadline)
                .foregroundStyle(Color.roammateMuted)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, RoammateSpacing.lg)
                .padding(.bottom, RoammateSpacing.sm)

            VStack(spacing: 10) {
                freeFeatureRow(icon: "calendar",
                               title: "Plan 2 trips at a time",
                               sub: "Past trips stay forever — read-only history.")
                freeFeatureRow(icon: "sparkles",
                               title: "15 AI brainstorms each month",
                               sub: "More than enough to scope your next adventure.")
                freeFeatureRow(icon: "map.fill",
                               title: "Visual map planning",
                               sub: "Drag, drop, and route — across every trip.")
            }
            .padding(.horizontal, RoammateSpacing.lg)

            Spacer(minLength: RoammateSpacing.md)

            Button {
                step = .plus
            } label: {
                HStack(spacing: 6) {
                    Text("Start planning")
                    Image(systemName: "arrow.right")
                        .font(.system(size: 13, weight: .bold))
                }
                .font(.system(.body, design: .rounded, weight: .bold))
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(Capsule().fill(Color.roammateInk))
                .foregroundStyle(.white)
            }
            .buttonStyle(.plain)
            .padding(.horizontal, RoammateSpacing.lg)
            .padding(.bottom, RoammateSpacing.lg)
        }
    }

    // MARK: - Step B: Plus tease

    private var plusContent: some View {
        VStack(spacing: RoammateSpacing.md) {
            HStack {
                PlusCrestView(size: 56)
                Spacer()
            }
            .padding(.horizontal, RoammateSpacing.lg)
            .padding(.top, RoammateSpacing.xs)

            Text("Want the full Roammate?")
                .font(.system(.title2, design: .rounded, weight: .black))
                .foregroundStyle(Color.roammateInk)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, RoammateSpacing.lg)

            (Text("Roammate Plus").foregroundStyle(RoammateGradient.plus)
                + Text(" unlocks the concierge, unlimited brainstorms, and offline maps.")
                    .foregroundStyle(Color.roammateMuted))
                .font(.system(.subheadline, design: .rounded))
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, RoammateSpacing.lg)
                .padding(.bottom, RoammateSpacing.sm)

            VStack(spacing: 12) {
                plusBullet("Unlimited AI brainstorms")
                plusBullet("Always-on AI concierge")
                plusBullet("Offline maps & pins")
            }
            .padding(.horizontal, RoammateSpacing.lg)

            Spacer(minLength: RoammateSpacing.md)

            VStack(spacing: 4) {
                Button { onSeePlus() } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "sparkles")
                            .font(.system(size: 13, weight: .bold))
                        Text("See Plus — ₹149/mo")
                    }
                    .font(.system(.body, design: .rounded, weight: .bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(Capsule().fill(RoammateGradient.plus))
                    .foregroundStyle(.white)
                    .shadow(color: Color.roammateIndigo.opacity(0.4), radius: 12, y: 6)
                }
                .buttonStyle(.plain)

                Button { onClose() } label: {
                    Text("Maybe later")
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.roammateMuted)
                        .padding(.vertical, 8)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, RoammateSpacing.lg)
            .padding(.bottom, RoammateSpacing.lg)
        }
    }

    private func freeFeatureRow(icon: String, title: String, sub: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(Color.roammateSurface)
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(Color.roammateBorder, lineWidth: 1)
                    )
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(Color.roammateIndigo)
            }
            .frame(width: 40, height: 40)

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(.subheadline, design: .rounded, weight: .black))
                    .foregroundStyle(Color.roammateInk)
                Text(sub)
                    .font(.caption)
                    .foregroundStyle(Color.roammateMuted)
            }
            Spacer()
        }
        .padding(RoammateSpacing.md)
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                .fill(Color.roammateBackground)
        )
    }

    private func plusBullet(_ text: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 16))
                .foregroundStyle(Color.roammateEmerald)
            Text(text)
                .font(.system(.subheadline, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.roammateInk)
            Spacer()
        }
    }
}
