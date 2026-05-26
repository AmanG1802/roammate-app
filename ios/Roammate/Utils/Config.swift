import Foundation

enum Config {
    static var apiBaseURL: String {
        #if DEBUG
        if let override = ProcessInfo.processInfo.environment["API_BASE_URL"] {
            return override
        }
        #if targetEnvironment(simulator)
        return "http://localhost:8000/api"
        #else
        // Physical device on the same Wi-Fi as the dev Mac. Update when LAN
        // IP changes (run `ipconfig getifaddr en0` on the Mac) or override
        // via the API_BASE_URL scheme env var.
        return "http://192.168.1.110:8000/api"
        #endif
        #else
        return "https://api.roammate.xyz/api"
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
