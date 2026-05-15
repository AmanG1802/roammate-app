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
}
