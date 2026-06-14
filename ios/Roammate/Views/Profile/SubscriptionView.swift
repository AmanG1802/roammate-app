import SwiftUI

/// The full Roammate Plus subscription screen. Renders one of two states
/// driven by `SubscriptionStore.entitlement`:
///   - Free: paywall hero, tier comparison, Subscribe CTA, Restore Purchases
///   - Plus: status header, manage / restore / Apple ID deep link
struct SubscriptionView: View {
    @EnvironmentObject private var subscriptionStore: SubscriptionStore
    @State private var paywallContext: PaywallContext?
    @State private var isRestoring = false

    struct PaywallContext: Identifiable {
        let id = UUID()
        let preferredPlan: PaywallPreferredPlan
    }

    var body: some View {
        ScrollView {
            VStack(spacing: RoammateSpacing.lg) {
                if subscriptionStore.entitlement.isPlus {
                    PlusManagementSection()
                } else {
                    FreeUpsellSection(onSubscribe: { plan in
                        paywallContext = PaywallContext(preferredPlan: plan)
                    })
                }

                RestoreSection(isRestoring: $isRestoring)
                    .padding(.top, RoammateSpacing.sm)
            }
            .padding(RoammateSpacing.lg)
        }
        .background(Color.roammateBackground.ignoresSafeArea())
        .navigationTitle("Subscription")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await subscriptionStore.loadProductIfNeeded()
            await subscriptionStore.refresh()
        }
        .sheet(item: $paywallContext) { ctx in
            PaywallSheet(feature: .concierge, preferredPlan: ctx.preferredPlan) { subscribed in
                paywallContext = nil
                if subscribed {
                    Task { await subscriptionStore.refresh() }
                }
            }
        }
    }
}


// MARK: - Free state — two plan cards + comparison

private struct FreeUpsellSection: View {
    let onSubscribe: (PaywallPreferredPlan) -> Void
    @EnvironmentObject private var subscriptionStore: SubscriptionStore

    var body: some View {
        VStack(alignment: .leading, spacing: RoammateSpacing.md) {
            // Hero — crest + wordmark + tagline
            HStack(alignment: .top, spacing: RoammateSpacing.md) {
                PlusCrestView(size: 56)
                VStack(alignment: .leading, spacing: 4) {
                    PlusWordmark(font: .system(.title2, design: .rounded, weight: .black))
                    Text("Pick the plan that fits — both unlock everything.")
                        .font(.subheadline)
                        .foregroundStyle(Color.roammateMuted)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
            }
            .padding(.bottom, RoammateSpacing.xs)

            PlanCard(
                tone: .primary,
                badge: "RECOMMENDED",
                name: "Monthly",
                price: "₹\(subscriptionStore.entitlement.priceInr)",
                unit: "/ month",
                subline: "Auto-renews · cancel anytime",
                bullets: [
                    "Unlimited everything, every month",
                    "Cancel anytime in Settings → Apple ID",
                    "UPI AutoPay, cards, or Apple ID billing",
                ],
                cta: "Subscribe for ₹\(subscriptionStore.entitlement.priceInr)/mo",
                onTap: { onSubscribe(.monthly) }
            )

            PlanCard(
                tone: .secondary,
                badge: "FLEX",
                name: "One-time",
                price: "₹\(subscriptionStore.entitlement.onetimePriceInr)",
                unit: "/ \(subscriptionStore.entitlement.onetimeDurationDays) days",
                subline: "One charge · no auto-renew",
                bullets: [
                    "\(subscriptionStore.entitlement.onetimeDurationDays) days of full Plus access",
                    "Hard-expires — never charges again",
                    "No subscription mandate required",
                ],
                cta: "Pay ₹\(subscriptionStore.entitlement.onetimePriceInr) · \(subscriptionStore.entitlement.onetimeDurationDays) days",
                onTap: { onSubscribe(.oneTime) }
            )

            Label("Payments handled by Apple — coupon codes apply at checkout.", systemImage: "checkmark.shield.fill")
                .font(.caption2.weight(.semibold))
                .foregroundStyle(Color.roammateMuted)
                .padding(.top, RoammateSpacing.xs)

            TierComparisonList()
                .padding(.top, RoammateSpacing.sm)
        }
    }
}

/// Pre-selected plan when the paywall opens from a specific CTA.
enum PaywallPreferredPlan: String { case monthly, oneTime }

private struct PlanCard: View {
    enum Tone { case primary, secondary }
    let tone: Tone
    let badge: String
    let name: String
    let price: String
    let unit: String
    let subline: String
    let bullets: [String]
    let cta: String
    let onTap: () -> Void

    private var isPrimary: Bool { tone == .primary }

    var body: some View {
        VStack(alignment: .leading, spacing: RoammateSpacing.sm) {
            HStack {
                Text(name)
                    .font(.caption.weight(.black))
                    .tracking(0.5)
                    .foregroundStyle(Color.roammateInk)
                Spacer()
                Text(badge)
                    .font(.system(size: 9, weight: .black))
                    .tracking(0.6)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Capsule().fill(isPrimary
                        ? Color.roammateIndigoTint
                        : Color.roammateAmberTint))
                    .foregroundStyle(isPrimary ? Color.roammateIndigo : Color.roammateAmber)
            }

            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text(price)
                    .font(.system(.largeTitle, design: .rounded, weight: .black))
                    .foregroundStyle(Color.roammateInk)
                Text(unit)
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateMuted)
            }
            Text(subline)
                .font(.caption2.weight(.black))
                .tracking(0.5)
                .foregroundStyle(Color.roammateMuted)
                .padding(.bottom, 2)

            VStack(alignment: .leading, spacing: 6) {
                ForEach(bullets, id: \.self) { b in
                    HStack(alignment: .top, spacing: 8) {
                        ZStack {
                            Circle().fill(Color.roammateIndigoTint).frame(width: 16, height: 16)
                            Image(systemName: "checkmark")
                                .font(.system(size: 8, weight: .black))
                                .foregroundStyle(Color.roammateIndigo)
                        }
                        .padding(.top, 2)
                        Text(b)
                            .font(.system(size: 13, weight: .semibold, design: .rounded))
                            .foregroundStyle(Color.roammateInk)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }

            Button(action: onTap) {
                Text(cta)
                    .font(.system(.subheadline, design: .rounded, weight: .bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .background(Capsule().fill(isPrimary ? Color.roammateIndigo : Color.roammateInk))
                    .foregroundStyle(.white)
                    .if(isPrimary) { view in
                        view.shadow(
                            color: RoammateShadow.indigoGlow.color,
                            radius: RoammateShadow.indigoGlow.radius,
                            x: RoammateShadow.indigoGlow.x,
                            y: RoammateShadow.indigoGlow.y
                        )
                    }
            }
            .buttonStyle(.plain)
            .padding(.top, RoammateSpacing.xs)
        }
        .padding(RoammateSpacing.lg)
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.card, style: .continuous)
                .fill(Color.roammateSurface)
                .overlay(
                    RoundedRectangle(cornerRadius: RoammateRadius.card, style: .continuous)
                        .stroke(isPrimary ? Color.roammateIndigo.opacity(0.25) : Color.roammateBorder,
                                lineWidth: isPrimary ? 1.5 : 1)
                )
        )
        .overlay(alignment: .top) {
            if isPrimary {
                RoundedRectangle(cornerRadius: 2)
                    .fill(RoammateGradient.plus)
                    .frame(height: 4)
                    .padding(.horizontal, RoammateRadius.card)
                    .offset(y: -2)
            }
        }
        .shadow(
            color: RoammateShadow.card.color,
            radius: RoammateShadow.card.radius,
            x: RoammateShadow.card.x,
            y: RoammateShadow.card.y
        )
    }
}

private extension View {
    @ViewBuilder
    func `if`<Content: View>(_ condition: Bool, transform: (Self) -> Content) -> some View {
        if condition { transform(self) } else { self }
    }
}


// MARK: - Plus state — status banner + management

private struct PlusManagementSection: View {
    @EnvironmentObject private var subscriptionStore: SubscriptionStore

    private var periodEndLabel: String? {
        guard let date = subscriptionStore.entitlement.periodEnd else { return nil }
        let f = DateFormatter()
        f.dateStyle = .long
        return f.string(from: date)
    }

    var body: some View {
        VStack(spacing: RoammateSpacing.md) {
            // Status banner — uses the Plus gradient as a soft tinted background.
            HStack(alignment: .top, spacing: RoammateSpacing.md) {
                PlusCrestView(size: 56)
                VStack(alignment: .leading, spacing: 4) {
                    (Text("You're on ").foregroundStyle(Color.roammateInk)
                        + Text("Roammate Plus").foregroundStyle(RoammateGradient.plus))
                        .font(.system(.title3, design: .rounded, weight: .black))
                    if subscriptionStore.entitlement.status == "one_time", let periodEndLabel {
                        Text("One-time plan · Active until \(periodEndLabel). After that, your account returns to free.")
                            .font(.subheadline)
                            .foregroundStyle(Color.roammateMuted)
                    } else if subscriptionStore.entitlement.status == "canceled", let periodEndLabel {
                        Text("Active until \(periodEndLabel). After that, your account reverts to free.")
                            .font(.subheadline)
                            .foregroundStyle(Color.roammateMuted)
                    } else if let periodEndLabel {
                        Text("Renews on \(periodEndLabel) · ₹\(subscriptionStore.entitlement.priceInr)/month")
                            .font(.subheadline)
                            .foregroundStyle(Color.roammateMuted)
                    }
                    if subscriptionStore.entitlement.status == "past_due" {
                        Text("Last payment failed — open Apple ID Settings to update.")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(Color.roammateDanger)
                            .padding(.top, 2)
                    }
                }
                Spacer(minLength: 0)
            }
            .padding(RoammateSpacing.lg)
            .background(
                RoundedRectangle(cornerRadius: RoammateRadius.card, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [
                                Color(red: 238/255, green: 242/255, blue: 255/255),
                                Color(red: 250/255, green: 232/255, blue: 255/255),
                                Color(red: 254/255, green: 243/255, blue: 199/255),
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: RoammateRadius.card, style: .continuous)
                            .stroke(Color.roammateIndigo.opacity(0.18), lineWidth: 1)
                    )
            )

            // Usage card
            HStack(spacing: 0) {
                StatCell(label: "Active trips", value: "\(subscriptionStore.entitlement.activeTripCount)", sub: "No cap")
                Divider().padding(.vertical, 8)
                StatCell(label: "Brainstorms", value: "\(subscriptionStore.entitlement.brainstormUsed)", sub: "Unlimited")
                Divider().padding(.vertical, 8)
                StatCell(label: "Concierge", value: "On", sub: "Always")
            }
            .background(
                RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                    .fill(Color.roammateSurface)
                    .overlay(
                        RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                            .stroke(Color.roammateBorder, lineWidth: 1)
                    )
            )

            // Manage row
            VStack(spacing: 0) {
                if subscriptionStore.entitlement.status == "one_time" {
                    ManageRow(
                        icon: "arrow.triangle.2.circlepath",
                        title: "Switch to monthly subscription",
                        subtitle: "Keep Plus going for ₹\(subscriptionStore.entitlement.priceInr)/mo"
                    ) {
                        NotificationCenter.default.post(
                            name: .needsPlus, object: nil,
                            userInfo: ["feature": PaywallFeature.concierge.rawValue]
                        )
                    }
                }
                ManageRow(
                    icon: "arrow.up.right.square.fill",
                    title: "Manage in Apple ID",
                    subtitle: "Cancel, change plan, or update payment in Settings"
                ) {
                    if let url = URL(string: "itms-apps://apps.apple.com/account/subscriptions") {
                        UIApplication.shared.open(url)
                    }
                }
            }
            .background(
                RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                    .fill(Color.roammateSurface)
                    .overlay(
                        RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                            .stroke(Color.roammateBorder, lineWidth: 1)
                    )
            )
        }
    }
}


// MARK: - Shared bits

private struct TierComparisonList: View {
    struct Row {
        let label: String
        let icon: String   // SF Symbol
        let free: String
        let plus: PlusValue
    }
    enum PlusValue {
        case infinity         // "∞"
        case check            // "✓"
        case checkLabel(String)
    }

    // Column widths chosen so "2 at a time" / "15 / month" fit Free without
    // wrapping, and the Plus column hosts a single bold symbol. The remaining
    // width goes to the feature label so SF Symbol + name render in full.
    private let freeColumnWidth: CGFloat = 86
    private let plusColumnWidth: CGFloat = 48
    private let iconColumnWidth: CGFloat = 22

    private let rows: [Row] = [
        Row(label: "Active trips",   icon: "calendar",  free: "2 at a time", plus: .infinity),
        Row(label: "AI brainstorms", icon: "sparkles",  free: "15 / month",  plus: .infinity),
        Row(label: "AI concierge",   icon: "infinity",  free: "—",           plus: .check),
        Row(label: "Offline maps",   icon: "map.fill",  free: "—",           plus: .check),
    ]

    var body: some View {
        VStack(spacing: 0) {
            // Header — aligns directly above each row column
            HStack(spacing: 12) {
                Text("FEATURE")
                    .padding(.leading, iconColumnWidth + 10)  // align under the label, past the icon
                    .frame(maxWidth: .infinity, alignment: .leading)
                Text("FREE")
                    .frame(width: freeColumnWidth, alignment: .center)
                Text("PLUS")
                    .frame(width: plusColumnWidth, alignment: .center)
            }
            .font(.caption2.weight(.black))
            .foregroundStyle(Color.roammateMuted)
            .tracking(0.5)
            .padding(.horizontal, RoammateSpacing.md)
            .padding(.vertical, 10)
            .background(Color.roammateBackground)

            ForEach(Array(rows.enumerated()), id: \.offset) { idx, row in
                HStack(spacing: 12) {
                    // Feature: icon chip + label, takes all remaining width
                    HStack(spacing: 10) {
                        ZStack {
                            RoundedRectangle(cornerRadius: 6, style: .continuous)
                                .fill(Color.roammateIndigoTint)
                                .frame(width: iconColumnWidth, height: iconColumnWidth)
                            Image(systemName: row.icon)
                                .font(.system(size: 11, weight: .bold))
                                .foregroundStyle(Color.roammateIndigo)
                        }
                        Text(row.label)
                            .font(.system(.subheadline, design: .rounded, weight: .semibold))
                            .foregroundStyle(Color.roammateInk)
                            .lineLimit(1)
                            .minimumScaleFactor(0.9)
                    }
                    .layoutPriority(1)
                    .frame(maxWidth: .infinity, alignment: .leading)

                    Text(row.free)
                        .font(.subheadline)
                        .foregroundStyle(row.free == "—" ? Color.roammateBorder : Color.roammateMuted)
                        .lineLimit(1)
                        .frame(width: freeColumnWidth, alignment: .center)

                    plusCell(for: row.plus)
                        .frame(width: plusColumnWidth, alignment: .center)
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.vertical, 12)

                if idx < rows.count - 1 {
                    Divider().padding(.leading, RoammateSpacing.md + iconColumnWidth + 10)
                }
            }
        }
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                .fill(Color.roammateSurface)
                .overlay(
                    RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                        .stroke(Color.roammateBorder, lineWidth: 1)
                )
        )
    }

    @ViewBuilder
    private func plusCell(for value: PlusValue) -> some View {
        switch value {
        case .infinity:
            Image(systemName: "infinity")
                .font(.system(size: 18, weight: .black))
                .foregroundStyle(RoammateGradient.plus)
        case .check:
            Image(systemName: "checkmark")
                .font(.system(size: 14, weight: .black))
                .foregroundStyle(RoammateGradient.plus)
        case .checkLabel(let s):
            HStack(spacing: 3) {
                Image(systemName: "checkmark")
                    .font(.system(size: 11, weight: .black))
                Text(s)
                    .font(.system(.subheadline, design: .rounded, weight: .bold))
                    .lineLimit(1)
            }
            .foregroundStyle(RoammateGradient.plus)
        }
    }
}


private struct StatCell: View {
    let label: String
    let value: String
    let sub: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label.uppercased())
                .font(.caption2.weight(.black))
                .tracking(0.5)
                .foregroundStyle(Color.roammateMuted)
            Text(value)
                .font(.system(.title3, design: .rounded, weight: .black))
                .foregroundStyle(Color.roammateInk)
            Text(sub)
                .font(.caption2)
                .foregroundStyle(Color.roammateMuted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(RoammateSpacing.md)
    }
}


private struct ManageRow: View {
    let icon: String
    let title: String
    let subtitle: String?
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                ZStack {
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(Color.roammateIndigoTint)
                        .frame(width: 36, height: 36)
                    Image(systemName: icon)
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(Color.roammateIndigo)
                }
                VStack(alignment: .leading, spacing: 1) {
                    Text(title)
                        .font(.system(.subheadline, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.roammateInk)
                    if let subtitle {
                        Text(subtitle)
                            .font(.caption)
                            .foregroundStyle(Color.roammateMuted)
                    }
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color.roammateMuted)
            }
            .padding(RoammateSpacing.md)
        }
        .buttonStyle(.plain)
    }
}


private struct RestoreSection: View {
    @EnvironmentObject private var subscriptionStore: SubscriptionStore
    @Binding var isRestoring: Bool

    private enum RestoreStatus {
        case success
        case alreadyPlus
        case nothingFound
        case failed(String)
    }
    @State private var restoreStatus: RestoreStatus?

    var body: some View {
        VStack(spacing: 8) {
            Button {
                isRestoring = true
                restoreStatus = nil
                Task {
                    let wasPlus = subscriptionStore.entitlement.isPlus
                    await subscriptionStore.restorePurchases()
                    isRestoring = false
                    if !wasPlus && subscriptionStore.entitlement.isPlus {
                        restoreStatus = .success
                    } else if wasPlus {
                        restoreStatus = .alreadyPlus
                    } else if let err = subscriptionStore.lastError {
                        restoreStatus = .failed(err)
                    } else {
                        restoreStatus = .nothingFound
                    }
                }
            } label: {
                HStack(spacing: 6) {
                    if isRestoring {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Image(systemName: "arrow.clockwise")
                            .font(.system(size: 12, weight: .bold))
                    }
                    Text("Restore purchases")
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                }
                .foregroundStyle(Color.roammateMuted)
            }
            .buttonStyle(.plain)
            .disabled(isRestoring)

            if let status = restoreStatus {
                restoreStatusBanner(status)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            } else {
                Text("Already subscribed on another device? Tap above.")
                    .font(.caption2)
                    .foregroundStyle(Color.roammateMuted.opacity(0.7))
            }
        }
        .animation(.easeInOut(duration: 0.2), value: restoreStatus == nil)
        .frame(maxWidth: .infinity)
        .padding(.vertical, RoammateSpacing.sm)
    }

    @ViewBuilder
    private func restoreStatusBanner(_ status: RestoreStatus) -> some View {
        switch status {
        case .success:
            Label("Plus activated! Welcome to Roammate Plus.", systemImage: "checkmark.circle.fill")
                .font(.caption.weight(.semibold))
                .foregroundStyle(Color.roammateSuccess)
        case .alreadyPlus:
            Label("You're already on Plus.", systemImage: "checkmark.circle.fill")
                .font(.caption.weight(.semibold))
                .foregroundStyle(Color.roammateSuccess)
        case .nothingFound:
            Label("No purchase found. Make sure you're signed in with the Apple ID used to buy Plus.", systemImage: "exclamationmark.circle")
                .font(.caption.weight(.semibold))
                .foregroundStyle(Color.roammateMuted)
                .multilineTextAlignment(.center)
        case .failed(let message):
            Label(message, systemImage: "xmark.circle.fill")
                .font(.caption.weight(.semibold))
                .foregroundStyle(Color.roammateDanger)
                .multilineTextAlignment(.center)
        }
    }
}
