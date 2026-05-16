import Foundation
import StoreKit

/// Thin wrapper around StoreKit 2. Owns:
///   - product fetch for the monthly Plus product
///   - `purchase()` and `restore()` flows
///   - the `Transaction.updates` listener that fires on renewals and
///     out-of-band purchases (e.g. from another device)
///
/// All transaction-related work pushes through `onVerifiedTransaction`, which
/// SubscriptionStore wires up to call the backend `/billing/apple/verify`.
@MainActor
final class StoreKitClient {
    static let monthlyProductID = "com.roammate.app.plus.monthly"
    static let oneTimeProductID = "com.roammate.app.plus.onetime"
    static let productID = monthlyProductID  // back-compat

    private var updatesTask: Task<Void, Never>?
    private(set) var monthlyProduct: Product?
    private(set) var oneTimeProduct: Product?
    var product: Product? { monthlyProduct }  // back-compat

    /// Called for every verified transaction (purchase, renewal, restore).
    /// Set by SubscriptionStore on init.
    /// Called for every verified transaction (purchase, renewal, restore).
    /// The `signedJWS` is the verifiable JWS string that the backend decodes
    /// via `/billing/apple/verify`; the `Transaction` instance is provided so
    /// the listener can call `.finish()` after backend reconciliation.
    var onVerifiedTransaction: ((_ signedJWS: String, _ transaction: StoreKit.Transaction) async -> Void)?

    init() {
        // The updates stream MUST be observed from app launch so we don't
        // miss transactions that finish while the app was backgrounded.
        updatesTask = Task.detached { [weak self] in
            for await result in Transaction.updates {
                guard let self else { return }
                if let pair = await self.verifiedPair(result) {
                    await self.onVerifiedTransaction?(pair.jws, pair.tx)
                    await pair.tx.finish()
                }
            }
        }
    }

    deinit {
        updatesTask?.cancel()
    }

    /// Load product metadata for both the monthly subscription and the
    /// non-renewing one-time product. Returns nil entries are tolerated so
    /// missing App Store Connect configuration doesn't crash the whole flow.
    @discardableResult
    func loadProduct() async -> Product? {
        do {
            let products = try await Product.products(for: [
                Self.monthlyProductID,
                Self.oneTimeProductID,
            ])
            self.monthlyProduct = products.first { $0.id == Self.monthlyProductID }
            self.oneTimeProduct = products.first { $0.id == Self.oneTimeProductID }
            return monthlyProduct
        } catch {
            return nil
        }
    }

    /// Monthly subscription purchase, optionally with a signed promotional offer.
    func purchaseMonthly(withPromotionalOffer offer: SignedPromotionalOffer? = nil) async throws -> PurchaseOutcome {
        if monthlyProduct == nil { _ = await loadProduct() }
        guard let product = monthlyProduct else { throw PurchaseError.productUnavailable }

        var options: Set<Product.PurchaseOption> = []
        if let offer {
            guard let sigData = Data(base64Encoded: offer.signature) else {
                throw PurchaseError.unverifiedTransaction
            }
            options.insert(.promotionalOffer(
                offerID: offer.offerId,
                keyID: offer.keyId,
                nonce: UUID(uuidString: offer.nonce) ?? UUID(),
                signature: sigData,
                timestamp: Int(offer.timestampMs)
            ))
        }

        let result = try await product.purchase(options: options)
        return try await handle(result: result)
    }

    /// Non-renewing one-time purchase (₹200 / 30 days). After verification
    /// the backend sets `subscription_status = "one_time"` and a 30-day
    /// `period_end`.
    func purchaseOneTime() async throws -> PurchaseOutcome {
        if oneTimeProduct == nil { _ = await loadProduct() }
        guard let product = oneTimeProduct else { throw PurchaseError.productUnavailable }
        let result = try await product.purchase()
        return try await handle(result: result)
    }

    /// Back-compat shim — calls the monthly path.
    func purchase() async throws -> PurchaseOutcome {
        try await purchaseMonthly(withPromotionalOffer: nil)
    }

    private func handle(result: Product.PurchaseResult) async throws -> PurchaseOutcome {
        switch result {
        case .success(let verification):
            guard let pair = verifiedPair(verification) else {
                throw PurchaseError.unverifiedTransaction
            }
            await onVerifiedTransaction?(pair.jws, pair.tx)
            await pair.tx.finish()
            return .succeeded
        case .userCancelled:
            return .cancelled
        case .pending:
            return .pending
        @unknown default:
            return .cancelled
        }
    }

    /// Re-read current entitlements and replay them through the verify hook.
    /// Used by the Plus management screen.
    func restorePurchases() async {
        for await result in Transaction.currentEntitlements {
            if let pair = verifiedPair(result) {
                await onVerifiedTransaction?(pair.jws, pair.tx)
            }
        }
    }

    // MARK: - Helpers

    /// Extract a verified Transaction together with its JWS string. We only
    /// accept `.verified` results — `.unverified` indicates Apple's signature
    /// chain didn't validate and we shouldn't trust the payload.
    private func verifiedPair(_ result: VerificationResult<StoreKit.Transaction>) -> (tx: StoreKit.Transaction, jws: String)? {
        switch result {
        case .verified(let tx): return (tx, result.jwsRepresentation)
        case .unverified: return nil
        }
    }

    enum PurchaseOutcome {
        case succeeded
        case cancelled
        case pending
    }

    enum PurchaseError: LocalizedError {
        case productUnavailable
        case unverifiedTransaction

        var errorDescription: String? {
            switch self {
            case .productUnavailable:
                return "Subscription is temporarily unavailable. Please try again."
            case .unverifiedTransaction:
                return "Could not verify this purchase with the App Store."
            }
        }
    }
}
