import Foundation
import SwiftUI

enum TutorialStatus: String, Codable {
    case notStarted = "not_started"
    case inProgress = "in_progress"
    case completed
    case skipped
}

/// Mirrors the Web `useTutorial` hook. Lives at MainShell scope as an
/// `@EnvironmentObject`.
@MainActor
final class TutorialStore: ObservableObject {
    @Published var status: TutorialStatus = .notStarted
    @Published var currentStep: Int = 0
    @Published var tutorialTripId: Int? = nil
    @Published var isLoading = true

    var isActive: Bool { status == .inProgress }

    func loadStatus() async {
        defer { isLoading = false }
        do {
            apply(try await TutorialService.status())
        } catch {
            // Anonymous / network error — keep defaults.
        }
    }

    func start() async {
        await runMutation { try await TutorialService.start() }
    }

    func advance(to step: Int) async {
        // Update locally first so every view's `.onChange(of: currentStep)` fires
        // immediately — the navigation (push/pop) then happens in lockstep with
        // the step change instead of waiting on a network round-trip, which made
        // Back-navigation race the server response.
        if isActive, currentStep != step { currentStep = step }
        await runMutation { try await TutorialService.setStep(step) }
    }

    func skip() async {
        await runMutation { try await TutorialService.skip() }
    }

    func complete() async {
        await runMutation { try await TutorialService.complete() }
    }

    func replay() async {
        await runMutation { try await TutorialService.replay() }
    }

    func deleteTutorialTrip() async {
        await runMutation { try await TutorialService.deleteTrip() }
    }

    // MARK: - private

    private func runMutation(_ op: () async throws -> TutorialState) async {
        do {
            apply(try await op())
        } catch {
            // No-op: keep last known state.
        }
    }

    private func apply(_ s: TutorialState) {
        status = TutorialStatus(rawValue: s.status) ?? .notStarted
        currentStep = s.step
        tutorialTripId = s.tripId
    }
}
