import SwiftUI

@MainActor
final class NotificationStore: ObservableObject {
    @Published var notifications: [AppNotification] = []
    @Published var unreadCount: Int = 0
    @Published var isLoading = false

    private let cacheKey = "notifications"

    init() {
        notifications = DiskCache.shared.load([AppNotification].self, key: cacheKey) ?? []
        unreadCount = notifications.filter { !$0.isRead }.count
    }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            async let listTask = NotificationService.getNotifications()
            async let countTask = NotificationService.getUnreadCount()
            let (list, count) = try await (listTask, countTask)
            notifications = list
            unreadCount = count
            DiskCache.shared.store(list, key: cacheKey)
        } catch {
            // Soft-fail; keep cached values.
        }
    }

    func refreshUnreadCount() async {
        unreadCount = (try? await NotificationService.getUnreadCount()) ?? unreadCount
    }

    func markRead(id: Int) async {
        do {
            try await NotificationService.markRead(id: id)
            if let idx = notifications.firstIndex(where: { $0.id == id }) {
                let n = notifications[idx]
                notifications[idx] = AppNotification(
                    id: n.id, type: n.type, payload: n.payload,
                    tripId: n.tripId, groupId: n.groupId, actor: n.actor,
                    readAt: Date(), createdAt: n.createdAt
                )
            }
            unreadCount = max(0, unreadCount - 1)
        } catch {}
    }

    func markAllRead() async {
        do {
            try await NotificationService.markAllRead()
            notifications = notifications.map {
                AppNotification(
                    id: $0.id, type: $0.type, payload: $0.payload,
                    tripId: $0.tripId, groupId: $0.groupId, actor: $0.actor,
                    readAt: $0.readAt ?? Date(), createdAt: $0.createdAt
                )
            }
            unreadCount = 0
        } catch {}
    }
}
