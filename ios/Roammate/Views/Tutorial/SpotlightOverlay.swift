import SwiftUI

/// Spotlight overlay used by the iOS tutorial driver. Reads the current step
/// from `TutorialStore` and resolves its anchor through `TutorialAnchorKey`.
struct SpotlightOverlay: View {
    @EnvironmentObject var tutorial: TutorialStore
    let anchors: [String: Anchor<CGRect>]
    let geometry: GeometryProxy
    let step: TutorialStep
    let isLast: Bool
    let onNext: () -> Void
    let onPrev: () -> Void
    let onSkip: () -> Void
    let onTryIt: (() -> Void)?
    let tryItLoading: Bool

    // Becomes true after a grace period so a step whose anchor never resolves
    // still shows a centred popover instead of dimming forever.
    @State private var showFallback = false
    // Gates the spotlight (cutout hole + ring + popover) so it only appears once
    // the step's page/navigation transition has settled. Until then the scrim
    // shows a flat dim — this stops the new step's spotlight from flashing over
    // the outgoing screen, which was the jank when pressing Back.
    @State private var revealed = false
    // Actual rendered height of the popover card, measured so we can place it
    // flush against the top/bottom edge without guessing.
    @State private var cardHeight: CGFloat = 240

    var body: some View {
        let rawRect = step.anchorID.flatMap { anchors[$0] }.map { geometry[$0] }
        // Some steps want the spotlight to span more than the anchored element
        // (e.g. a list header + the first couple of cards). When `spotlightHeight`
        // is set, grow the rect downward from the anchor's top edge.
        let rect: CGRect? = rawRect.map { r in
            guard let h = step.spotlightHeight else { return r }
            return CGRect(x: r.minX, y: r.minY, width: r.width, height: max(r.height, h))
        }
        let padded: CGRect? = rect.map { CGRect(
            x: $0.minX - 8, y: $0.minY - 8,
            width: $0.width + 16, height: $0.height + 16
        )}
        // Hold the popover back until the step's anchor is on screen (i.e. the
        // app has navigated to the right page/section) so it never floats over
        // the previous screen. Anchorless steps (wrap-up) fall through to the
        // centred fallback after a short delay.
        let anchored = step.anchorID != nil
        // Only show the spotlight once the transition has settled (`revealed`)
        // AND the target rect is on screen — so it lands on the destination page
        // rather than the page we're leaving.
        let showSpotlight = revealed && padded != nil
        let popoverVisible = revealed && ((anchored && padded != nil) || showFallback)
        let scrimHole = showSpotlight ? padded : nil

        return ZStack {
            // Scrim with cutout. The dim stays constant across step changes; only
            // the hole appears once the spotlight is revealed.
            cutoutScrim(padded: scrimHole)
                .allowsHitTesting(true)
                .ignoresSafeArea()

            // Spotlight ring
            if showSpotlight, let r = padded {
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .strokeBorder(Color.roammateIndigo.opacity(0.9), lineWidth: 2)
                    .frame(width: r.width, height: r.height)
                    .position(x: r.midX, y: r.midY)
                    .allowsHitTesting(false)
                    .transition(.opacity)
            }

            // Popover
            if popoverVisible {
                popover(target: padded, in: geometry.size)
            }
        }
        .animation(.spring(response: 0.35, dampingFraction: 0.85), value: rect)
        .animation(.easeInOut(duration: 0.28), value: revealed)
        .animation(.easeInOut(duration: 0.4), value: popoverVisible)
        .task(id: step.number) {
            // Hide the spotlight immediately so it doesn't linger over the
            // outgoing screen, then let the page/navigation transition settle
            // before revealing it on the destination page.
            revealed = false
            showFallback = false
            try? await Task.sleep(nanoseconds: 500_000_000)
            revealed = true
            // Anchorless steps (wrap-up) and any never-resolving anchor still get
            // a centred popover after a short grace period.
            let graceNs: UInt64 = step.anchorID == nil ? 120_000_000 : 2_200_000_000
            try? await Task.sleep(nanoseconds: graceNs)
            showFallback = true
        }
    }

    @ViewBuilder
    private func cutoutScrim(padded: CGRect?) -> some View {
        // The scrim Canvas uses `.ignoresSafeArea()`, so its origin sits at the
        // screen's top-left while `padded` is in the GeometryReader's space
        // (which starts below the status bar). Shift the cutout by the safe-area
        // insets so the bright hole lines up exactly with the indigo ring.
        let inset = geometry.safeAreaInsets
        Canvas { ctx, size in
            let rect = CGRect(origin: .zero, size: size)
            var path = Path(rect)
            if let r = padded {
                let hole = Path(
                    roundedRect: r.offsetBy(dx: inset.leading, dy: inset.top),
                    cornerRadius: 14
                )
                path = path.subtracting(hole)
            }
            ctx.fill(path, with: .color(Color.roammateInk.opacity(0.62)))
        }
    }

    @ViewBuilder
    private func popover(target: CGRect?, in size: CGSize) -> some View {
        let cardWidth: CGFloat = min(360, size.width - 32)
        let position = popoverPosition(target: target, size: size, cardWidth: cardWidth, cardHeight: cardHeight)

        VStack(alignment: .leading, spacing: 12) {
            HStack {
                HStack(spacing: 5) {
                    Image(systemName: "sparkles")
                        .font(.caption.bold())
                    Text("Step \(step.number) of \(TutorialScript.total)")
                        .font(.caption.weight(.semibold))
                }
                .foregroundColor(.roammateIndigo)
                Spacer()
                Button(action: onSkip) {
                    Image(systemName: "xmark")
                        .font(.footnote.weight(.semibold))
                        .foregroundColor(.roammateMuted)
                }
            }
            VStack(alignment: .leading, spacing: 6) {
                Text(step.title)
                    .font(.headline)
                    .foregroundColor(.roammateInk)
                Text(step.body)
                    .font(.subheadline)
                    .foregroundColor(.roammateMuted)
                    .fixedSize(horizontal: false, vertical: true)
            }
            // Secondary outlined "Try it" chip — only for steps where the try-it
            // doesn't itself advance the tour (brainstorm/concierge sample sends).
            // When `advanceViaTryIt` is set, Try Now is the primary CTA in the
            // bottom row instead, so we don't render the chip here.
            if let label = step.tryItLabel, let onTryIt, !step.advanceViaTryIt {
                Button(action: onTryIt) {
                    HStack(spacing: 6) {
                        if tryItLoading { ProgressView().scaleEffect(0.7) }
                        Text(tryItLoading ? "Working…" : label)
                            .font(.subheadline.weight(.semibold))
                    }
                    .padding(.horizontal, 12).padding(.vertical, 7)
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(Color.roammateIndigo.opacity(0.4), lineWidth: 1)
                    )
                }
                .disabled(tryItLoading)
                .foregroundColor(.roammateIndigoDark)
            }
            stepDots
            HStack {
                Button("Skip tour") { onSkip() }
                    .font(.subheadline)
                    .foregroundColor(.roammateMuted)
                Spacer()
                if step.number > 1 {
                    Button("Back") { onPrev() }
                        .font(.subheadline.weight(.semibold))
                        .foregroundColor(.roammateInk)
                        .padding(.horizontal, 12).padding(.vertical, 7)
                }
                if step.advanceViaTryIt, let onTryIt {
                    // Try Now is this step's forward control — completing the demo
                    // advances the tour, so there's no separate "Next".
                    Button(action: onTryIt) {
                        HStack(spacing: 6) {
                            if tryItLoading {
                                ProgressView().scaleEffect(0.7).tint(.white)
                            }
                            Text(tryItLoading ? "Working…" : (step.tryItLabel ?? "Try Now"))
                                .font(.subheadline.weight(.semibold))
                                .foregroundColor(.white)
                        }
                        .padding(.horizontal, 14).padding(.vertical, 8)
                        .background(Color.roammateIndigo, in: RoundedRectangle(cornerRadius: 10))
                    }
                    .disabled(tryItLoading)
                } else {
                    Button(isLast ? "Finish" : "Next") { onNext() }
                        .font(.subheadline.weight(.semibold))
                        .foregroundColor(.white)
                        .padding(.horizontal, 14).padding(.vertical, 8)
                        .background(Color.roammateIndigo, in: RoundedRectangle(cornerRadius: 10))
                }
            }
        }
        .padding(18)
        .frame(width: cardWidth, alignment: .leading)
        .background(Color.roammateSurface, in: RoundedRectangle(cornerRadius: 20))
        .shadow(color: Color.black.opacity(0.18), radius: 18, x: 0, y: 8)
        .background(
            GeometryReader { proxy in
                Color.clear.preference(key: CardHeightKey.self, value: proxy.size.height)
            }
        )
        .onPreferenceChange(CardHeightKey.self) { h in
            if h > 0, abs(h - cardHeight) > 1 { cardHeight = h }
        }
        .position(position)
        .animation(.spring(response: 0.45, dampingFraction: 0.78), value: position)
        .transition(.opacity)
    }

    private var stepDots: some View {
        HStack(spacing: 5) {
            ForEach(0..<TutorialScript.total, id: \.self) { i in
                let active = i == step.number - 1
                let past = i < step.number - 1
                Capsule()
                    .fill(active ? Color.roammateIndigo : past ? Color.roammateIndigo.opacity(0.4) : Color.roammateBorder)
                    .frame(width: active ? 18 : 6, height: 5)
            }
        }
    }

    /// Resolve the popover centre. Honours the step's `placement`:
    /// `.top` pins the card under the nav bar (keeps the bottom — chat input and
    /// the just-sent message — visible); `.bottom` pins it to the bottom edge
    /// (keeps a highlighted element/list near the top visible). `.center` and the
    /// anchorless fallback centre the card.
    private func popoverPosition(target: CGRect?, size: CGSize, cardWidth: CGFloat, cardHeight: CGFloat) -> CGPoint {
        let topSafe: CGFloat = 80
        let bottomSafe: CGFloat = 44
        let centerX = size.width / 2
        let half = cardHeight / 2
        let topY = topSafe + half
        let bottomY = size.height - bottomSafe - half

        // Step 9 (concierge): after the sample message is sent, slide the card
        // to the bottom so the AI response is visible above it.
        let effectivePlacement: PopoverPlacement = (tutorial.conciergeSampleSent && step.id == .concierge)
            ? .bottomForced
            : step.placement

        switch effectivePlacement {
        case .center:
            return CGPoint(x: centerX, y: size.height / 2)
        case .top:
            return CGPoint(x: centerX, y: topY)
        case .bottom:
            // If the highlighted element sits in the lower half (e.g. a bottom
            // bar), fall back to the top so the card doesn't cover it.
            if let r = target, r.minY > size.height * 0.55 {
                return CGPoint(x: centerX, y: topY)
            }
            return CGPoint(x: centerX, y: bottomY)
        case .bottomForced:
            return CGPoint(x: centerX, y: bottomY)
        }
    }
}

/// Measures the popover card's rendered height so it can be pinned flush to an edge.
private struct CardHeightKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = max(value, nextValue())
    }
}
