import Foundation
import StoreKit
import SwiftUI

/// Single source of truth for the user's Roammate Plus entitlement on iOS.
///
/// Hydrated from `GET /billing/status` at app boot and after every successful
/// purchase. Components read `entitlement` to render tier-aware UI; the
/// paywall sheet calls `purchase()` directly.
@MainActor
final class SubscriptionStore: ObservableObject {
    @Published private(set) var entitlement: Entitlement = .freeDefault
    @Published private(set) var isLoading: Bool = false
    @Published private(set) var product: Product?
    @Published var lastError: String?

    private let storeKit = StoreKitClient()

    /// Coupon currently in flight (one per purchase attempt). Captured so
    /// `verifyWithBackend` can stamp the redemption ledger after StoreKit
    /// confirms the transaction.
    private var pendingCouponId: Int?

    init() {
        storeKit.onVerifiedTransaction = { [weak self] jws, _ in
            await self?.verifyWithBackend(signedJWS: jws)
        }
    }

    /// Call once after authentication. Loads the product and entitlement.
    func boot() async {
        await loadProductIfNeeded()
        await refresh()
    }

    /// Forget all subscription state — called from logout.
    func reset() {
        entitlement = .freeDefault
        product = nil
    }

    func loadProductIfNeeded() async {
        if product != nil { return }
        product = await storeKit.loadProduct()
    }

    /// Re-fetch the user's entitlement from the backend.
    func refresh() async {
        do {
            let dto: Entitlement = try await APIClient.shared.request(
                "/billing/status",
                method: "GET"
            )
            entitlement = dto
            NotificationCenter.default.post(name: .subscriptionUpdated, object: nil)
        } catch {
            // Keep the previous entitlement on failure — don't fail closed
            // and re-lock features the user has already paid for.
        }
    }

    /// Back-compat shim — equivalent to `purchaseMonthly(couponCode: nil)`.
    func purchase() async throws -> Bool {
        try await purchaseMonthly(couponCode: nil)
    }

    /// Validate a coupon code against the backend without redeeming it.
    func validateCoupon(_ code: String, target: String) async throws -> CouponQuote {
        struct Body: Encodable { let code: String; let target: String }
        return try await APIClient.shared.request(
            "/billing/coupons/validate",
            method: "POST",
            body: Body(code: code, target: target)
        )
    }

    /// Monthly subscription via StoreKit, optionally with a coupon code that
    /// maps to an Apple Promotional Offer (EARLYSALE → first month at ₹49).
    func purchaseMonthly(couponCode: String?) async throws -> Bool {
        lastError = nil
        isLoading = true
        defer { isLoading = false }
        var signedOffer: SignedPromotionalOffer?
        if let code = couponCode, !code.isEmpty {
            struct Body: Encodable { let code: String }
            do {
                signedOffer = try await APIClient.shared.request(
                    "/billing/apple/redeem-offer",
                    method: "POST",
                    body: Body(code: code)
                )
                pendingCouponId = signedOffer?.couponId
            } catch {
                lastError = "Code can't be applied on iOS. Try checking out on the web."
                throw error
            }
        } else {
            pendingCouponId = nil
        }
        do {
            let outcome = try await storeKit.purchaseMonthly(withPromotionalOffer: signedOffer)
            switch outcome {
            case .succeeded: return true
            case .cancelled, .pending: return false
            }
        } catch {
            lastError = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            throw error
        }
    }

    /// One-time non-renewing IAP (₹200 / 30 days). Couponed free grants
    /// (EARLYACCESS at ₹0) bypass StoreKit and go through the backend
    /// `/billing/razorpay/one-time` free-grant path instead.
    func purchaseOneTime(couponCode: String?) async throws -> Bool {
        lastError = nil
        isLoading = true
        defer { isLoading = false }

        // Free-grant short-circuit
        if let code = couponCode, !code.isEmpty {
            do {
                let quote = try await validateCoupon(code, target: "one_time")
                if quote.finalAmountPaise == 0 {
                    struct GrantBody: Encodable { let coupon_code: String }
                    struct GrantResp: Decodable {
                        let granted: Bool
                        let entitlement: Entitlement?
                    }
                    let resp: GrantResp = try await APIClient.shared.request(
                        "/billing/razorpay/one-time",
                        method: "POST",
                        body: GrantBody(coupon_code: code)
                    )
                    if resp.granted, let e = resp.entitlement {
                        entitlement = e
                        NotificationCenter.default.post(name: .subscriptionUpdated, object: nil)
                        return true
                    }
                }
                pendingCouponId = quote.couponId
            } catch {
                lastError = (error as? LocalizedError)?.errorDescription ?? "Invalid code"
                throw error
            }
        } else {
            pendingCouponId = nil
        }

        do {
            let outcome = try await storeKit.purchaseOneTime()
            switch outcome {
            case .succeeded: return true
            case .cancelled, .pending: return false
            }
        } catch {
            lastError = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            throw error
        }
    }

    func restorePurchases() async {
        await storeKit.restorePurchases()
        await refresh()
    }

    /// POST the JWS to the backend so it can flip the user to Plus.
    private func verifyWithBackend(signedJWS: String) async {
        struct VerifyBody: Encodable {
            let signed_transaction_info: String
            let coupon_id: Int?
        }
        let body = VerifyBody(
            signed_transaction_info: signedJWS,
            coupon_id: pendingCouponId
        )
        pendingCouponId = nil  // single-shot
        do {
            let dto: Entitlement = try await APIClient.shared.request(
                "/billing/apple/verify",
                method: "POST",
                body: body
            )
            entitlement = dto
            NotificationCenter.default.post(name: .subscriptionUpdated, object: nil)
        } catch {
            lastError = (error as? LocalizedError)?.errorDescription ?? "Could not verify purchase"
        }
    }
}
