import Foundation

/// Mirrors `backend/app/services/entitlements.py:Entitlement.to_dto()`.
/// Single source of truth for what the user can do — driven by the backend.
struct Entitlement: Codable, Equatable {
    let tier: String                    // "free" | "plus"
    let status: String                  // "none" | "active" | "past_due" | "canceled" | "expired" | "pending"
    let periodEnd: Date?
    let canCreateActiveTrip: Bool
    let canUseConcierge: Bool
    let canUseOfflineMaps: Bool
    let brainstormRemaining: Int?       // nil = unlimited
    let activeTripCount: Int
    let activeTripCap: Int?             // nil = unlimited
    let brainstormUsed: Int
    let brainstormCap: Int?             // nil = unlimited
    let priceInr: Int
    let onetimePriceInr: Int
    let onetimeDurationDays: Int

    enum CodingKeys: String, CodingKey {
        case tier, status
        case periodEnd = "period_end"
        case canCreateActiveTrip = "can_create_active_trip"
        case canUseConcierge = "can_use_concierge"
        case canUseOfflineMaps = "can_use_offline_maps"
        case brainstormRemaining = "brainstorm_remaining"
        case activeTripCount = "active_trip_count"
        case activeTripCap = "active_trip_cap"
        case brainstormUsed = "brainstorm_used"
        case brainstormCap = "brainstorm_cap"
        case priceInr = "price_inr"
        case onetimePriceInr = "onetime_price_inr"
        case onetimeDurationDays = "onetime_duration_days"
    }

    init(tier: String, status: String, periodEnd: Date?, canCreateActiveTrip: Bool,
         canUseConcierge: Bool, canUseOfflineMaps: Bool, brainstormRemaining: Int?,
         activeTripCount: Int, activeTripCap: Int?, brainstormUsed: Int,
         brainstormCap: Int?, priceInr: Int,
         onetimePriceInr: Int = 200, onetimeDurationDays: Int = 30) {
        self.tier = tier
        self.status = status
        self.periodEnd = periodEnd
        self.canCreateActiveTrip = canCreateActiveTrip
        self.canUseConcierge = canUseConcierge
        self.canUseOfflineMaps = canUseOfflineMaps
        self.brainstormRemaining = brainstormRemaining
        self.activeTripCount = activeTripCount
        self.activeTripCap = activeTripCap
        self.brainstormUsed = brainstormUsed
        self.brainstormCap = brainstormCap
        self.priceInr = priceInr
        self.onetimePriceInr = onetimePriceInr
        self.onetimeDurationDays = onetimeDurationDays
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        tier = try c.decode(String.self, forKey: .tier)
        status = try c.decode(String.self, forKey: .status)
        periodEnd = try c.decodeIfPresent(Date.self, forKey: .periodEnd)
        canCreateActiveTrip = try c.decode(Bool.self, forKey: .canCreateActiveTrip)
        canUseConcierge = try c.decode(Bool.self, forKey: .canUseConcierge)
        canUseOfflineMaps = try c.decode(Bool.self, forKey: .canUseOfflineMaps)
        brainstormRemaining = try c.decodeIfPresent(Int.self, forKey: .brainstormRemaining)
        activeTripCount = try c.decode(Int.self, forKey: .activeTripCount)
        activeTripCap = try c.decodeIfPresent(Int.self, forKey: .activeTripCap)
        brainstormUsed = try c.decode(Int.self, forKey: .brainstormUsed)
        brainstormCap = try c.decodeIfPresent(Int.self, forKey: .brainstormCap)
        priceInr = try c.decode(Int.self, forKey: .priceInr)
        onetimePriceInr = try c.decodeIfPresent(Int.self, forKey: .onetimePriceInr) ?? 200
        onetimeDurationDays = try c.decodeIfPresent(Int.self, forKey: .onetimeDurationDays) ?? 30
    }

    static let freeDefault = Entitlement(
        tier: "free",
        status: "none",
        periodEnd: nil,
        canCreateActiveTrip: true,
        canUseConcierge: false,
        canUseOfflineMaps: false,
        brainstormRemaining: 15,
        activeTripCount: 0,
        activeTripCap: 2,
        brainstormUsed: 0,
        brainstormCap: 15,
        priceInr: 149,
        onetimePriceInr: 200,
        onetimeDurationDays: 30
    )

    var isPlus: Bool {
        tier == "plus" && (status == "active" || status == "past_due" || status == "one_time")
    }
    var isOneTime: Bool { status == "one_time" }
}

/// Coupon quote returned by `POST /billing/coupons/validate`.
struct CouponQuote: Codable, Equatable {
    let couponId: Int
    let code: String
    let appliesTo: String
    let originalAmountPaise: Int
    let discountAmountPaise: Int
    let finalAmountPaise: Int
    let razorpayOfferId: String?
    let appleOfferId: String?
    let displayMessage: String

    enum CodingKeys: String, CodingKey {
        case couponId = "coupon_id"
        case code
        case appliesTo = "applies_to"
        case originalAmountPaise = "original_amount_paise"
        case discountAmountPaise = "discount_amount_paise"
        case finalAmountPaise = "final_amount_paise"
        case razorpayOfferId = "razorpay_offer_id"
        case appleOfferId = "apple_offer_id"
        case displayMessage = "display_message"
    }
}

/// Signed Apple Promotional Offer payload returned by `/billing/apple/redeem-offer`.
struct SignedPromotionalOffer: Codable, Equatable {
    let productId: String
    let offerId: String
    let keyId: String
    let nonce: String
    let timestampMs: Int64
    let signature: String
    let usernameHash: String
    let couponId: Int
    let displayMessage: String

    enum CodingKeys: String, CodingKey {
        case productId = "product_id"
        case offerId = "offer_id"
        case keyId = "key_id"
        case nonce
        case timestampMs = "timestamp_ms"
        case signature
        case usernameHash = "username_hash"
        case couponId = "coupon_id"
        case displayMessage = "display_message"
    }
}

/// Paywall feature code returned by the backend in 402 responses. Used as the
/// key for contextual paywall copy.
enum PaywallFeature: String {
    case concierge
    case brainstormQuota = "brainstorm_quota"
    case activeTrips = "active_trips"
    case offlineMaps = "offline_maps"
}
