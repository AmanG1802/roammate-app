import SwiftUI

struct PlanTripMessage: Identifiable {
    let id = UUID()
    let role: String   // "user" or "assistant"
    let text: String
}

@MainActor
final class PlanTripStore: ObservableObject {
    enum Phase: Equatable {
        case idle, planning, previewing, creating
    }

    @Published var prompt: String = ""
    @Published var phase: Phase = .idle
    @Published var preview: PlanTripPreview?
    @Published var error: String?
    @Published var messages: [PlanTripMessage] = []

    let wittyMessages = [
        "Picking the brain of a thousand travel guides…",
        "Bribing the algorithm with extra croissants…",
        "Cross-referencing with our 2 a.m. street-food cravings…",
        "Asking the locals nicely…",
        "Looking for the photos worth printing…",
        "Mapping the route the GPS would never suggest…",
        "Checking which seasons are showing up…",
    ]

    func reset() {
        prompt = ""
        preview = nil
        phase = .idle
        error = nil
        messages = []
    }

    func plan() async {
        let p = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !p.isEmpty else { return }

        messages.append(PlanTripMessage(role: "user", text: p))
        prompt = ""
        phase = .planning
        preview = nil
        error = nil
        do {
            let result = try await PlanTripService.plan(prompt: p)
            preview = result
            phase = .previewing
            HapticManager.success()
        } catch let e as APIError {
            error = e.errorDescription
            phase = messages.count > 0 ? .previewing : .idle
            HapticManager.error()
        } catch {
            self.error = error.localizedDescription
            phase = messages.count > 0 ? .previewing : .idle
            HapticManager.error()
        }
    }

    func createTrip() async -> Trip? {
        guard let preview else { return nil }
        phase = .creating
        error = nil
        do {
            let payload = TripCreate(
                name: preview.tripName,
                startDate: preview.startDate,
                endDate: nil,
                timezone: TimeZone.current.identifier
            )
            let trip = try await TripService.createTrip(payload)
            if !preview.items.isEmpty {
                _ = try await PlanTripService.bulkAddBrainstormItems(tripId: trip.id, items: preview.items)
            }
            HapticManager.success()
            phase = .idle
            self.preview = nil
            self.prompt = ""
            return trip
        } catch let e as APIError {
            error = e.errorDescription
            phase = .previewing
            HapticManager.error()
            return nil
        } catch {
            self.error = error.localizedDescription
            phase = .previewing
            HapticManager.error()
            return nil
        }
    }
}
