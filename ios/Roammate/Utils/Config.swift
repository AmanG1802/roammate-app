import Foundation

enum Config {
    /// Base URL for the backend REST API, e.g. `https://api.roammate.xyz/api`.
    ///
    /// Resolution order (DEBUG-only cases are compiled out of Release):
    ///   1. `API_BASE_URL` env var — always wins when set (set it in the scheme
    ///      to point at staging, a tunnel, a teammate's box, etc.).
    ///   2. DEBUG + simulator      → localhost.
    ///   3. DEBUG + physical device → the dev Mac's LAN IP, injected into
    ///      Info.plist at build time by the "Inject dev LAN host" build phase
    ///      (see `Scripts/inject-dev-host.sh` / `project.yml`).
    ///   4. RELEASE                → production.
    static let apiBaseURL: String = resolveAPIBaseURL()

    /// `apiBaseURL` as a `URL`. Force-unwrapped on purpose: a malformed base
    /// URL is a build/config mistake we want to surface immediately, not a
    /// runtime condition to recover from.
    static let apiBaseURLValue: URL = {
        guard let url = URL(string: apiBaseURL) else {
            fatalError("Config.apiBaseURL is not a valid URL: \(apiBaseURL)")
        }
        return url
    }()

    private static func resolveAPIBaseURL() -> String {
        #if DEBUG
        if let override = envOverride { return override }
        #if targetEnvironment(simulator)
        return "http://localhost:8000/api"
        #else
        return "http://\(devLANHost):8000/api"
        #endif
        #else
        return "https://api.roammate.xyz/api"
        #endif
    }

    #if DEBUG
    /// Trimmed, non-empty `API_BASE_URL` from the environment, else nil.
    private static var envOverride: String? {
        guard let raw = ProcessInfo.processInfo.environment["API_BASE_URL"] else { return nil }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    /// Dev Mac LAN host written into Info.plist at build time by the
    /// "Inject dev LAN host" phase. Falls back to a last-known IP when the
    /// phase produced nothing (e.g. the Mac was offline at build time).
    private static var devLANHost: String {
        let injected = Bundle.main.object(forInfoDictionaryKey: "DevLANHost") as? String
        let trimmed = injected?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? fallbackLANHost : trimmed
    }

    /// Last-resort LAN IP if build-time injection produced nothing. Normal
    /// device builds overwrite this automatically; keep it roughly current.
    private static let fallbackLANHost = "192.168.1.107"
    #endif
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
