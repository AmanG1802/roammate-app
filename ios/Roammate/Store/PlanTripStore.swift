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

    /// Tutorial: simulate a full plan turn — typewriter the prompt, sit in the
    /// planning state, then drop a canned NYC preview — without touching the
    /// LLM. Mirrors the web `runTutorialPlanDemo`.
    func runTutorialDemo() async {
        reset()
        let sample = "A 3-day New York City trip with iconic landmarks, food, and parks"
        for ch in sample {
            prompt.append(ch)
            try? await Task.sleep(nanoseconds: 18_000_000)
        }
        try? await Task.sleep(nanoseconds: 200_000_000)
        messages.append(PlanTripMessage(role: "user", text: sample))
        prompt = ""
        phase = .planning
        try? await Task.sleep(nanoseconds: 2_600_000_000)
        let canned = Self.tutorialPreview
        preview = canned
        if let out = canned.userOutput, !out.isEmpty {
            messages.append(PlanTripMessage(role: "assistant", text: out))
        }
        phase = .previewing
        HapticManager.success()
    }

    /// Canned NYC preview shown during the tutorial (keyed to the seeded trip).
    static let tutorialPreview: PlanTripPreview = {
        func item(_ title: String, _ category: String, _ time: String) -> BrainstormItem {
            BrainstormItem(
                title: title, description: nil, category: category, placeId: nil,
                lat: nil, lng: nil, address: nil, photoUrl: nil, rating: nil,
                priceLevel: nil, types: nil, timeCategory: time, addedBy: nil
            )
        }
        return PlanTripPreview(
            tripName: "Welcome to Roammate — New York",
            startDate: nil,
            durationDays: 3,
            items: [
                item("Times Square", "landmark", "morning"),
                item("Museum of Modern Art", "museum", "afternoon"),
                item("Central Park Picnic", "park", "midday"),
                item("Brooklyn Bridge Sunset Walk", "landmark", "evening"),
                item("Joe's Pizza", "restaurant", "midday"),
            ],
            userOutput: "Three days in NYC: anchor Day 1 in Midtown (Times Square + MoMA), Day 2 in Central Park + Brooklyn Bridge at sunset, Day 3 around the Village with a Joe's Pizza stop.",
            timezone: "America/New_York"
        )
    }()

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
            if let userOutput = result.userOutput, !userOutput.isEmpty {
                messages.append(PlanTripMessage(role: "assistant", text: userOutput))
            }
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
                timezone: preview.timezone ?? TimeZone.current.identifier
            )
            let trip = try await TripService.createTrip(payload)
            if !preview.items.isEmpty {
                _ = try await PlanTripService.bulkAddBrainstormItems(tripId: trip.id, items: preview.items)
            }
            // Backfill the planning conversation as the first Brainstorm chat.
            // Best-effort: failure here shouldn't block trip creation.
            if !messages.isEmpty {
                let seeds = messages.map { BrainstormSeedMessage(role: $0.role, content: $0.text) }
                do {
                    _ = try await BrainstormService.seedMessages(tripId: trip.id, messages: seeds)
                } catch {
                    // ignore — seed is best-effort
                }
            }
            HapticManager.success()
            phase = .idle
            self.preview = nil
            self.prompt = ""
            self.messages = []
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
