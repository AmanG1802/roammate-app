import SwiftUI

/// Top-of-screen dunning banner: shown when `entitlement.status == "past_due"`.
/// Tapping deep-links to Apple ID subscription management (StoreKit-managed)
/// or the in-app subscription page (Razorpay-managed users).
struct PastDueBanner: View {
    @EnvironmentObject private var subscriptionStore: SubscriptionStore
    @State private var isVisible: Bool = true

    var body: some View {
        if subscriptionStore.entitlement.status == "past_due" && isVisible {
            HStack(spacing: 10) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(Color.roammateDanger)
                Text("Last Plus payment failed — update payment to keep Plus.")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(Color.roammateDanger)
                    .lineLimit(2)
                Spacer(minLength: 6)
                Button {
                    if let url = URL(string: "itms-apps://apps.apple.com/account/subscriptions") {
                        UIApplication.shared.open(url)
                    }
                } label: {
                    Text("UPDATE")
                        .font(.caption2.weight(.black))
                        .tracking(0.5)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(Capsule().fill(Color.roammateDanger))
                        .foregroundStyle(.white)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(red: 254/255, green: 226/255, blue: 226/255))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .stroke(Color.roammateDanger.opacity(0.25), lineWidth: 1)
                    )
            )
            .transition(.move(edge: .top).combined(with: .opacity))
        }
    }
}


/// Amber expiry warning shown to one-time Plus users in the final 5 days
/// of their 30-day window. Tapping opens the paywall in monthly mode so they
/// can keep going.
struct OneTimeExpiryBanner: View {
    @EnvironmentObject private var subscriptionStore: SubscriptionStore

    var body: some View {
        let ent = subscriptionStore.entitlement
        if ent.status == "one_time", let end = ent.periodEnd {
            let secondsLeft = end.timeIntervalSinceNow
            let days = max(0, Int(ceil(secondsLeft / 86_400)))
            if days <= 5 {
                Button {
                    NotificationCenter.default.post(
                        name: .needsPlus, object: nil,
                        userInfo: ["feature": PaywallFeature.concierge.rawValue]
                    )
                } label: {
                    HStack(spacing: 10) {
                        Image(systemName: "clock.badge.exclamationmark.fill")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(Color.roammateAmber)
                        Text(days == 0
                             ? "Plus ends today — switch to monthly to keep going."
                             : "Plus ends in \(days) day\(days == 1 ? "" : "s") — switch to monthly for ₹\(ent.priceInr)/mo.")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(Color.roammateAmber)
                            .multilineTextAlignment(.leading)
                            .lineLimit(2)
                        Spacer(minLength: 6)
                        Text("SWITCH")
                            .font(.caption2.weight(.black))
                            .tracking(0.5)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 5)
                            .background(Capsule().fill(Color.roammateAmber))
                            .foregroundStyle(.white)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(Color(red: 254/255, green: 243/255, blue: 199/255))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14, style: .continuous)
                                    .stroke(Color.roammateAmber.opacity(0.3), lineWidth: 1)
                            )
                    )
                }
                .buttonStyle(.plain)
            }
        }
    }
}


/// Compact usage strip for free users: "X / 15 brainstorms · Y / 2 active trips"
/// with a gradient crest dot. Tap to open the paywall. Hidden for Plus.
struct FreeUsageStrip: View {
    @EnvironmentObject private var subscriptionStore: SubscriptionStore

    var body: some View {
        let ent = subscriptionStore.entitlement
        if ent.tier == "free",
           let bsCap = ent.brainstormCap,
           let tripCap = ent.activeTripCap {
            let bsLeft = ent.brainstormRemaining ?? bsCap
            let bsUsed = max(bsCap - bsLeft, 0)
            let bsTone: Color = {
                if bsLeft == 0 { return Color.roammateDanger }
                if bsLeft <= 3 { return Color.roammateAmber }
                return Color.roammateInk
            }()
            let tripsTone: Color = ent.activeTripCount >= tripCap
                ? Color.roammateAmber
                : Color.roammateInk

            Button {
                NotificationCenter.default.post(
                    name: .needsPlus, object: nil,
                    userInfo: ["feature": PaywallFeature.concierge.rawValue]
                )
            } label: {
                HStack(spacing: 14) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .fill(RoammateGradient.plus)
                            .frame(width: 28, height: 28)
                        Image(systemName: "sparkles")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(.white)
                    }

                    VStack(alignment: .leading, spacing: 0) {
                        Text("BRAINSTORMS")
                            .font(.system(size: 9, weight: .black))
                            .tracking(0.6)
                            .foregroundStyle(Color.roammateMuted)
                        Text("\(bsUsed) / \(bsCap)")
                            .font(.system(.subheadline, design: .rounded, weight: .black))
                            .foregroundStyle(bsTone)
                            .monospacedDigit()
                    }

                    Rectangle()
                        .fill(Color.roammateBorder)
                        .frame(width: 1, height: 24)

                    VStack(alignment: .leading, spacing: 0) {
                        Text("ACTIVE TRIPS")
                            .font(.system(size: 9, weight: .black))
                            .tracking(0.6)
                            .foregroundStyle(Color.roammateMuted)
                        Text("\(ent.activeTripCount) / \(tripCap)")
                            .font(.system(.subheadline, design: .rounded, weight: .black))
                            .foregroundStyle(tripsTone)
                            .monospacedDigit()
                    }

                    Spacer(minLength: 0)

                    Text("UPGRADE →")
                        .font(.system(size: 10, weight: .black))
                        .tracking(0.6)
                        .foregroundStyle(Color.roammateIndigo)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(Color.roammateSurface)
                        .overlay(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .stroke(Color.roammateBorder, lineWidth: 1)
                        )
                )
            }
            .buttonStyle(.plain)
        }
    }
}
