import SwiftUI

@MainActor
final class BrainstormStore: ObservableObject {
    let tripId: Int

    @Published var messages: [BrainstormMessage] = []
    @Published var items: [BrainstormItemOut] = []
    @Published var isSending = false
    @Published var isExtracting = false
    @Published var isLoading = false
    @Published var error: String?

    var onIdeasPromoted: (([IdeaBinItem]) -> Void)?
    var onIdeasTimeUpdated: (() async -> Void)?

    init(tripId: Int) {
        self.tripId = tripId
    }

    func load() async {
        isLoading = true
        defer { isLoading = false }

        async let messagesTask = BrainstormService.getMessages(tripId: tripId)
        async let itemsTask = BrainstormService.getItems(tripId: tripId)

        do {
            let (msgs, itms) = try await (messagesTask, itemsTask)
            messages = msgs
            items = itms
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func send(_ text: String) async {
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        isSending = true
        defer { isSending = false }

        let optimisticUser = BrainstormMessage(
            id: -(messages.count + 1),
            role: "user",
            content: text,
            createdAt: Date()
        )
        messages.append(optimisticUser)

        do {
            let response = try await BrainstormService.chat(tripId: tripId, message: text)
            messages = response.history
        } catch let e as APIError {
            messages.removeAll { $0.id == optimisticUser.id }
            error = e.errorDescription
        } catch {
            messages.removeAll { $0.id == optimisticUser.id }
            self.error = error.localizedDescription
        }
    }

    @discardableResult
    func extract() async -> Int {
        isExtracting = true
        defer { isExtracting = false }

        do {
            let response = try await BrainstormService.extract(tripId: tripId)
            items.append(contentsOf: response.items)
            return response.items.count
        } catch let e as APIError {
            error = e.errorDescription
            return 0
        } catch {
            self.error = error.localizedDescription
            return 0
        }
    }

    func promote(itemIds: [Int]?) async {
        do {
            let promoted = try await BrainstormService.promote(tripId: tripId, itemIds: itemIds)
            let removedIds = Set(itemIds ?? items.map(\.id))

            let brainstormItems = itemIds != nil
                ? items.filter { removedIds.contains($0.id) }
                : items

            items.removeAll { removedIds.contains($0.id) }
            onIdeasPromoted?(promoted)

            await applyTimeCategoryDefaults(promoted: promoted, brainstormItems: brainstormItems)
            await onIdeasTimeUpdated?()
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func applyTimeCategoryDefaults(promoted: [IdeaBinItem], brainstormItems: [BrainstormItemOut]) async {
        for idea in promoted {
            if idea.startTime != nil { continue }

            let matchingBrainstorm = brainstormItems.first { $0.title == idea.title }
            guard let tc = matchingBrainstorm?.timeCategory ?? idea.timeCategory,
                  !tc.isEmpty else { continue }

            let (start, end) = Self.timeCategoryToTimes(tc)
            let update = IdeaUpdate(title: nil, startTime: start, endTime: end, timeCategory: tc)
            do {
                _ = try await IdeaService.updateIdea(tripId: tripId, ideaId: idea.id, fields: update)
            } catch {}
        }
    }

    private static func timeCategoryToTimes(_ category: String) -> (Date, Date) {
        let cal = Calendar.current
        let today = cal.startOfDay(for: Date())
        let (startHour, endHour): (Int, Int) = {
            switch category.lowercased() {
            case "morning": return (9, 11)
            case "afternoon": return (14, 16)
            case "evening": return (18, 20)
            case "night": return (21, 23)
            case "all_day": return (9, 18)
            default: return (10, 12)
            }
        }()
        let start = cal.date(bySettingHour: startHour, minute: 0, second: 0, of: today)!
        let end = cal.date(bySettingHour: endHour, minute: 0, second: 0, of: today)!
        return (start, end)
    }

    func delete(itemId: Int) async {
        let backup = items
        items.removeAll { $0.id == itemId }

        do {
            try await BrainstormService.deleteItem(tripId: tripId, itemId: itemId)
        } catch {
            items = backup
        }
    }

    func clearAll() async {
        let backup = items
        items.removeAll()

        do {
            try await BrainstormService.clearAll(tripId: tripId)
        } catch {
            items = backup
        }
    }
}
