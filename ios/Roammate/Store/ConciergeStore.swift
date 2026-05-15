import SwiftUI

@MainActor
final class ConciergeStore: ObservableObject {
    let tripId: Int

    @Published var messages: [ChatMessage] = []
    @Published var isThinking = false
    @Published var error: String?
    @Published var pendingResponse: ConciergeChatResponse?

    init(tripId: Int) {
        self.tripId = tripId
    }

    func send(_ text: String) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        messages.append(ChatMessage(role: .user, text: trimmed))
        isThinking = true
        error = nil
        defer { isThinking = false }

        do {
            let res = try await ConciergeService.chat(tripId: tripId, message: trimmed)
            messages.append(ChatMessage(
                role: .assistant,
                text: res.userMessage,
                intent: res.intent,
                params: res.params,
                requiresConfirmation: res.requiresConfirmation,
                messageType: res.messageType
            ))
            pendingResponse = res.requiresConfirmation ? res : nil
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func confirmPending() async -> ExecuteResponse? {
        guard let res = pendingResponse else { return nil }
        defer { pendingResponse = nil }
        do {
            let exec = try await ConciergeService.execute(
                tripId: tripId,
                intent: res.intent.rawValue,
                params: res.params
            )
            messages.append(ChatMessage(role: .assistant, text: exec.message))
            return exec
        } catch let e as APIError {
            error = e.errorDescription
            return nil
        } catch {
            self.error = error.localizedDescription
            return nil
        }
    }

    func cancelPending() {
        pendingResponse = nil
    }

    func whatsNext() async -> WhatsNextResponse? {
        try? await ConciergeService.whatsNext(tripId: tripId)
    }

    func todaySummary() async -> TodaySummaryResponse? {
        try? await ConciergeService.todaySummary(tripId: tripId)
    }
}
