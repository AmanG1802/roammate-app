import Foundation

enum Config {
    static var apiBaseURL: String {
        #if DEBUG
        return ProcessInfo.processInfo.environment["API_BASE_URL"] ?? "http://localhost:8000/api"
        #else
        return "https://api.roammate.app/api"
        #endif
    }
}

extension Notification.Name {
    static let sessionExpired = Notification.Name("com.roammate.sessionExpired")
    /// Broadcast when the backend returns 402 needs_plus. userInfo["feature"]
    /// is the feature code ("concierge" | "brainstorm_quota" | "active_trips"
    /// | "offline_maps") that the paywall sheet uses to render contextual copy.
    static let needsPlus = Notification.Name("com.roammate.needsPlus")
    /// Broadcast after a successful StoreKit purchase + backend verify so any
    /// screen showing tier-aware UI can refresh.
    static let subscriptionUpdated = Notification.Name("com.roammate.subscriptionUpdated")
}
