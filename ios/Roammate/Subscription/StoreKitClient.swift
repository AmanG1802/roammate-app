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
    static let monthlyProductID = "app.roammate.ios.plus.monthly"
    static let oneTimeProductID = "app.roammate.ios.plus.onetime"
    static let productID = monthlyProductID  // back-compat

    private var updatesTask: Task<Void, Never>?
    private(set) var monthlyProduct: Product?
    private(set) var oneTimeProduct: Product?
    var product: Product? { monthlyProduct }  // back-compat

    /// Called for every verified transaction (purchase, renewal, restore).
    /// Set by SubscriptionStore on init.
    /// Called for every verified transaction (purchase, renewal, restore).
    /// The `signedJWS` is the verifiable JWS string that the backend decodes
    /// via `/billing/apple/verify`. Returns `true` only when the backend
    /// confirmed the Plus entitlement; we use that to decide whether to
    /// `.finish()` the transaction — an unconfirmed transaction is left in the
    /// queue so `Transaction.updates` redelivers it and we retry verification
    /// rather than silently dropping a real, paid-for purchase.
    var onVerifiedTransaction: ((_ signedJWS: String, _ transaction: StoreKit.Transaction) async -> Bool)?

    init() {
        // The updates stream MUST be observed from app launch so we don't
        // miss transactions that finish while the app was backgrounded.
        updatesTask = Task.detached { [weak self] in
            for await result in Transaction.updates {
                guard let self else { return }
                if let pair = await self.verifiedPair(result) {
                    let confirmed = await self.onVerifiedTransaction?(pair.jws, pair.tx) ?? false
                    // Only finish once the backend has granted entitlement;
                    // otherwise leave it queued for a later retry.
                    if confirmed { await pair.tx.finish() }
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
            let ids: [String] = [Self.monthlyProductID, Self.oneTimeProductID]
            let products = try await Product.products(for: ids)
            self.monthlyProduct = products.first { $0.id == Self.monthlyProductID }
            self.oneTimeProduct = products.first { $0.id == Self.oneTimeProductID }
            print("[StoreKit] Loaded \(products.count)/\(ids.count) products: \(products.map(\.id))")
            return monthlyProduct
        } catch {
            print("[StoreKit] Product load failed: \(error)")
            return nil
        }
    }

    /// Monthly subscription purchase, optionally with a signed promotional offer.
    func purchaseMonthly(withPromotionalOffer offer: SignedPromotionalOffer? = nil) async throws -> PurchaseOutcome {
        if monthlyProduct == nil { _ = await loadProduct() }
        guard let product = monthlyProduct else {
            let found = [monthlyProduct, oneTimeProduct].compactMap { $0 }.count
            throw PurchaseError.productUnavailable(found: found, requested: 2)
        }

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
        guard let product = oneTimeProduct else {
            let found = [monthlyProduct, oneTimeProduct].compactMap { $0 }.count
            throw PurchaseError.productUnavailable(found: found, requested: 2)
        }
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
            // Treat the purchase as successful only when the backend has
            // actually granted the entitlement. If verification fails we leave
            // the transaction unfinished (so `Transaction.updates` retries it)
            // and surface an error instead of a false "Welcome to Plus".
            let confirmed = await onVerifiedTransaction?(pair.jws, pair.tx) ?? false
            guard confirmed else {
                throw PurchaseError.verificationFailed
            }
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
                _ = await onVerifiedTransaction?(pair.jws, pair.tx)
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
        case productUnavailable(found: Int, requested: Int)
        case unverifiedTransaction
        case verificationFailed

        var errorDescription: String? {
            switch self {
            case .productUnavailable(let found, let requested):
                return "Could not load products from the App Store (\(found)/\(requested) found). " +
                       "Ensure both products are 'Ready to Submit' in App Store Connect and " +
                       "a Sandbox Tester is signed in under Settings → App Store."
            case .unverifiedTransaction:
                return "Could not verify this purchase with the App Store."
            case .verificationFailed:
                return "Your payment went through, but we couldn't activate Plus just yet. " +
                       "It'll be retried automatically — pull to refresh or tap Restore Purchases in a moment."
            }
        }
    }
}
