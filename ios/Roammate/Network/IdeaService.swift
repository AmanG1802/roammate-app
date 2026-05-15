import Foundation

enum IdeaService {
    static func getIdeas(tripId: Int) async throws -> [IdeaBinItem] {
        try await APIClient.shared.request("/trips/\(tripId)/ideas")
    }

    static func deleteIdea(tripId: Int, ideaId: Int) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/trips/\(tripId)/ideas/\(ideaId)", method: "DELETE"
        )
    }

    static func updateIdea(tripId: Int, ideaId: Int, fields: IdeaUpdate) async throws -> IdeaBinItem {
        try await APIClient.shared.request(
            "/trips/\(tripId)/ideas/\(ideaId)", method: "PATCH", body: fields
        )
    }

    /// Drop a block of free text (or a URL) and let the backend extract and
    /// enrich place ideas. Used for "paste an Instagram link" UX.
    static func ingest(tripId: Int, text: String, sourceUrl: String? = nil) async throws -> [IdeaBinItem] {
        try await APIClient.shared.request(
            "/trips/\(tripId)/ingest",
            method: "POST",
            body: IngestRequest(text: text, sourceUrl: sourceUrl)
        )
    }
}
