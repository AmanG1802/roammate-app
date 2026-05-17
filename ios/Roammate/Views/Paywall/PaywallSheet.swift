import SwiftUI

/// Contextual paywall sheet. Driven by a `PaywallFeature` so the copy, icon,
/// and CTA stay relevant to whatever the user was trying to do.
///
/// v1.1 adds a Monthly / One-time plan picker and an inline coupon input.
/// Three checkout paths:
///   - Monthly (with optional Apple Promotional Offer when a code applies)
///   - One-time non-renewing IAP (₹200 / 30 days)
///   - Backend free grant when coupon zeroes the price (EARLYACCESS)
struct PaywallSheet: View {
    let feature: PaywallFeature
    let preferredPlan: PaywallPreferredPlan
    let onDismiss: (Bool) -> Void   // true = subscribed, false = dismissed

    init(feature: PaywallFeature,
         preferredPlan: PaywallPreferredPlan = .monthly,
         onDismiss: @escaping (Bool) -> Void) {
        self.feature = feature
        self.preferredPlan = preferredPlan
        self.onDismiss = onDismiss
        _plan = State(initialValue: preferredPlan == .oneTime ? .oneTime : .monthly)
    }

    @EnvironmentObject private var subscriptionStore: SubscriptionStore
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isSubscribing = false
    @State private var showSuccess = false
    @State private var errorMessage: String?
    @State private var plan: PlanChoice
    @State private var coupon: CouponQuote?

    private enum PlanChoice: String, Hashable { case monthly, oneTime }

    var body: some View {
        ZStack {
            if showSuccess {
                successContent
                    .transition(.opacity)
            } else {
                paywallContent
                    .transition(.opacity)
            }
            if showSuccess {
                ConfettiBurst()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .allowsHitTesting(false)
            }
        }
        .animation(.spring(response: 0.45, dampingFraction: 0.85), value: showSuccess)
        .background(Color.roammateSurface)
        .presentationDetents([.fraction(0.85), .large])
        .presentationDragIndicator(.visible)
        .interactiveDismissDisabled(isSubscribing)
    }

    // MARK: - Paywall content

    private var paywallContent: some View {
        ScrollView {
            VStack(spacing: RoammateSpacing.md) {
                PlusCrestView(size: 64)
                    .padding(.top, RoammateSpacing.lg)

                VStack(spacing: 6) {
                    Text(copy.title)
                        .font(.system(.title2, design: .rounded, weight: .black))
                        .foregroundStyle(Color.roammateInk)
                        .multilineTextAlignment(.center)
                    Text(copy.subtitle)
                        .font(.subheadline)
                        .foregroundStyle(Color.roammateMuted)
                        .multilineTextAlignment(.center)
                }
                .padding(.horizontal, RoammateSpacing.lg)

                planPicker.padding(.horizontal, RoammateSpacing.lg)

                VStack(spacing: RoammateSpacing.sm) {
                    bullet("infinity", text: "Unlimited AI concierge & brainstorms")
                    bullet("map.fill", text: "Offline maps & pins for the road")
                    bullet("calendar.badge.plus", text: "Plan as many trips as you want")
                }
                .padding(.horizontal, RoammateSpacing.xl)

                priceCard

                CouponInputView(
                    target: plan == .monthly ? "subscription" : "one_time",
                    initialCode: nil
                ) { quote in
                    coupon = quote
                }
                .padding(.horizontal, RoammateSpacing.lg)

                if let errorMessage {
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundStyle(Color.roammateDanger)
                        .padding(.horizontal, RoammateSpacing.lg)
                }

                VStack(spacing: 6) {
                    Button(action: subscribe) {
                        HStack(spacing: 8) {
                            if isSubscribing {
                                ProgressView().tint(.white)
                            } else {
                                Image(systemName: "sparkles")
                                    .font(.system(size: 14, weight: .bold))
                            }
                            Text(ctaLabel)
                                .font(.system(.body, design: .rounded, weight: .bold))
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(Capsule().fill(Color.roammateIndigo))
                        .foregroundStyle(.white)
                        .shadow(
                            color: RoammateShadow.indigoGlow.color,
                            radius: RoammateShadow.indigoGlow.radius,
                            x: RoammateShadow.indigoGlow.x,
                            y: RoammateShadow.indigoGlow.y
                        )
                    }
                    .buttonStyle(.plain)
                    .disabled(isSubscribing)
                    .padding(.horizontal, RoammateSpacing.lg)

                    Button("Maybe later") { onDismiss(false) }
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.roammateMuted)
                        .padding(.vertical, 4)
                }

                VStack(spacing: 2) {
                    Text(plan == .monthly
                         ? "Subscriptions auto-renew. Cancel anytime in Settings → Apple ID."
                         : "One charge for \(subscriptionStore.entitlement.onetimeDurationDays) days. No auto-renewal.")
                    Text("Manage from Profile → Subscription")
                }
                .font(.caption2)
                .foregroundStyle(Color.roammateMuted.opacity(0.7))
                .multilineTextAlignment(.center)
                .padding(.horizontal, RoammateSpacing.lg)
                .padding(.bottom, RoammateSpacing.md)
            }
        }
    }

    private var planPicker: some View {
        Picker("Plan", selection: $plan) {
            Text("Monthly · ₹\(subscriptionStore.entitlement.priceInr)").tag(PlanChoice.monthly)
            Text("One-time · ₹\(subscriptionStore.entitlement.onetimePriceInr)").tag(PlanChoice.oneTime)
        }
        .pickerStyle(.segmented)
    }

    private var displayPrice: (final: Int, base: Int, showDiscount: Bool, isFree: Bool) {
        let base = plan == .monthly
            ? subscriptionStore.entitlement.priceInr
            : subscriptionStore.entitlement.onetimePriceInr
        guard let coupon else { return (base, base, false, false) }
        let appliesHere = (plan == .monthly && (coupon.appliesTo == "subscription_first_cycle" || coupon.appliesTo == "any"))
            || (plan == .oneTime && (coupon.appliesTo == "one_time" || coupon.appliesTo == "any"))
        guard appliesHere else { return (base, base, false, false) }
        let final = coupon.finalAmountPaise / 100
        return (final, base, true, final == 0)
    }

    private var ctaLabel: String {
        if isSubscribing { return "Opening App Store…" }
        let p = displayPrice
        if p.isFree { return "Claim 30 free days" }
        if plan == .monthly {
            return p.showDiscount
                ? "Start at ₹\(p.final), then ₹\(p.base)/mo"
                : "Subscribe for ₹\(p.base)/mo"
        }
        return p.showDiscount
            ? "Pay ₹\(p.final) · 30 days"
            : "Pay ₹\(p.base) · 30 days"
    }

    private var priceCard: some View {
        let p = displayPrice
        return HStack(alignment: .firstTextBaseline, spacing: 6) {
            if p.showDiscount && !p.isFree {
                Text("₹\(p.base)")
                    .font(.system(.subheadline, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.roammateMuted)
                    .strikethrough()
            }
            Text(p.isFree ? "Free" : "₹\(p.final)")
                .font(.system(.title, design: .rounded, weight: .black))
                .foregroundStyle(p.isFree ? Color.roammateSuccess : Color.roammateInk)
            Text(plan == .monthly ? "/ month" : "/ 30 days")
                .font(.system(.subheadline, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.roammateMuted)
            Spacer()
            Text(plan == .monthly ? "RENEWS MONTHLY" : "NO RENEWAL")
                .font(.caption2.weight(.black))
                .foregroundStyle(Color.roammateMuted)
                .tracking(0.5)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, RoammateSpacing.md)
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                .fill(Color.roammateBackground)
                .overlay(
                    RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                        .stroke(Color.roammateBorder, lineWidth: 1)
                )
        )
        .padding(.horizontal, RoammateSpacing.lg)
    }

    private func bullet(_ icon: String, text: String) -> some View {
        HStack(spacing: 10) {
            ZStack {
                Circle().fill(Color.roammateIndigoTint).frame(width: 24, height: 24)
                Image(systemName: icon)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color.roammateIndigo)
            }
            Text(text)
                .font(.system(.subheadline, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.roammateInk)
            Spacer(minLength: 0)
        }
    }

    // MARK: - Success content

    private var successContent: some View {
        VStack(spacing: RoammateSpacing.md) {
            PlusCrestView(size: 88)
                .padding(.top, RoammateSpacing.xl)
            (Text("Welcome to ").foregroundStyle(Color.roammateInk)
                + Text("Roammate Plus").foregroundStyle(RoammateGradient.plus))
                .font(.system(.title2, design: .rounded, weight: .black))
                .multilineTextAlignment(.center)
            Text("Everything just unlocked.")
                .font(.subheadline)
                .foregroundStyle(Color.roammateMuted)
            Spacer()
        }
        .padding(RoammateSpacing.lg)
    }

    // MARK: - Actions

    private func subscribe() {
        isSubscribing = true
        errorMessage = nil
        let couponCode = coupon?.code
        Task {
            do {
                let purchased: Bool
                if plan == .monthly {
                    purchased = try await subscriptionStore.purchaseMonthly(couponCode: couponCode)
                } else {
                    purchased = try await subscriptionStore.purchaseOneTime(couponCode: couponCode)
                }
                isSubscribing = false
                if purchased {
                    showSuccess = true
                    try? await Task.sleep(nanoseconds: 2_200_000_000)
                    onDismiss(true)
                }
            } catch {
                isSubscribing = false
                errorMessage = (error as? LocalizedError)?.errorDescription
                    ?? error.localizedDescription
            }
        }
    }

    // MARK: - Copy

    private struct Copy {
        let title: String
        let subtitle: String
    }

    private var copy: Copy {
        switch feature {
        case .concierge:
            return Copy(
                title: "Meet your trip concierge",
                subtitle: "Always-on AI travel companion — included with Plus."
            )
        case .brainstormQuota:
            return Copy(
                title: "You've used 15 brainstorms this month",
                subtitle: "Go unlimited with Plus, or wait until next month."
            )
        case .activeTrips:
            return Copy(
                title: "You're planning 2 trips already",
                subtitle: "Plus lifts the cap so you can dream as wide as you travel."
            )
        case .offlineMaps:
            return Copy(
                title: "Take your maps off-grid",
                subtitle: "Offline tiles + saved pins for when signal disappears."
            )
        }
    }
}
