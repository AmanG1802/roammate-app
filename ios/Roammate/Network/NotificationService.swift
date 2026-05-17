import Foundation

enum NotificationService {
    static func getNotifications(limit: Int = 30, beforeId: Int? = nil) async throws -> [AppNotification] {
        try await APIClient.shared.request(
            "/notifications/",
            query: [
                "limit": String(limit),
                "before_id": beforeId.map(String.init),
            ]
        )
    }

    static func getUnreadCount() async throws -> Int {
        let res: UnreadCount = try await APIClient.shared.request("/notifications/unread-count")
        return res.unread
    }

    static func markRead(id: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/notifications/\(id)/read", method: "POST"
        )
    }

    static func markAllRead() async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/notifications/mark-all-read", method: "POST"
        )
    }
}
