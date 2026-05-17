import Foundation

enum PlanTripService {
    /// Ask the LLM to draft a trip from a single free-text prompt.
    static func plan(prompt: String) async throws -> PlanTripPreview {
        try await APIClient.shared.request(
            "/llm/plan-trip",
            method: "POST",
            body: PlanTripRequest(prompt: prompt, timezone: TimeZone.current.identifier),
            retries: 0          // LLM calls are slow and expensive; don't auto-retry
        )
    }

    /// Bulk-insert the generated brainstorm items into a newly created trip.
    @discardableResult
    static func bulkAddBrainstormItems(tripId: Int, items: [BrainstormItem]) async throws -> [BrainstormItem] {
        try await APIClient.shared.request(
            "/trips/\(tripId)/brainstorm/bulk",
            method: "POST",
            body: BrainstormBulkRequest(items: items)
        )
    }
}
