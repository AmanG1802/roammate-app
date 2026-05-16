import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case unauthorized
    case paymentRequired(feature: String)
    case serverError(Int, String)
    case decodingError(Error)
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Invalid URL"
        case .unauthorized: return "Session expired. Please log in again."
        case .paymentRequired: return "This feature is part of Roammate Plus."
        case .serverError(_, let msg): return msg
        case .decodingError(let e): return "Failed to parse response: \(e.localizedDescription)"
        case .networkError(let e): return e.localizedDescription
        }
    }
}

/// 402 body shape: `{"detail": {"code": "needs_plus", "feature": "concierge", ...}}`.
private struct NeedsPlusDetail: Decodable {
    let code: String
    let feature: String
}
private struct NeedsPlusBody: Decodable {
    let detail: NeedsPlusDetail
}

/// Internal helper for decoding FastAPI's `{"detail": "..."}` error body.
private struct FastAPIErrorBody: Decodable {
    let detail: JSONValue?

    var message: String? {
        switch detail {
        case .string(let s): return s
        case .array(let arr):
            // Pydantic validation errors: array of {loc, msg, type, ...}
            return arr.compactMap { $0["msg"]?.stringValue }.joined(separator: "; ")
        default: return nil
        }
    }
}

/// `EmptyResponse` is what callers pass as `T` for endpoints that return
/// 204 No Content. The decoder special-cases empty data.
struct EmptyResponse: Decodable {}

final class APIClient {
    static let shared = APIClient()

    let decoder: JSONDecoder = {
        let d = JSONDecoder()
        let iso = ISO8601DateFormatter()
        let isoFractional = ISO8601DateFormatter()
        isoFractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let dateOnly = DateFormatter()
        dateOnly.calendar = Calendar(identifier: .iso8601)
        dateOnly.timeZone = TimeZone(identifier: "UTC")
        dateOnly.dateFormat = "yyyy-MM-dd"
        let dateTimeNoTZ = DateFormatter()
        dateTimeNoTZ.calendar = Calendar(identifier: .iso8601)
        dateTimeNoTZ.timeZone = TimeZone(identifier: "UTC")
        dateTimeNoTZ.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        d.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let str = try container.decode(String.self)
            if let date = iso.date(from: str) { return date }
            if let date = isoFractional.date(from: str) { return date }
            if let date = dateTimeNoTZ.date(from: str) { return date }
            if let date = dateOnly.date(from: str) { return date }
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Cannot decode date: \(str)"
            )
        }
        return d
    }()

    let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()

    private init() {}

    // MARK: - Public entry points

    /// Request with a typed Encodable body.
    func request<T: Decodable, B: Encodable>(
        _ path: String,
        method: String = "GET",
        body: B?,
        query: [String: String?] = [:],
        requiresAuth: Bool = true,
        retries: Int = 2
    ) async throws -> T {
        try await perform(
            path: path, method: method,
            bodyData: try body.map { try encoder.encode($0) },
            query: query, requiresAuth: requiresAuth, retries: retries
        )
    }

    /// Request with no body.
    func request<T: Decodable>(
        _ path: String,
        method: String = "GET",
        query: [String: String?] = [:],
        requiresAuth: Bool = true,
        retries: Int = 2
    ) async throws -> T {
        try await perform(
            path: path, method: method,
            bodyData: nil,
            query: query, requiresAuth: requiresAuth, retries: retries
        )
    }

    // MARK: - Core implementation

    private func perform<T: Decodable>(
        path: String,
        method: String,
        bodyData: Data?,
        query: [String: String?],
        requiresAuth: Bool,
        retries: Int
    ) async throws -> T {
        guard var components = URLComponents(string: Config.apiBaseURL + path) else {
            throw APIError.invalidURL
        }
        let queryItems = query.compactMap { (k, v) -> URLQueryItem? in
            guard let v else { return nil }
            return URLQueryItem(name: k, value: v)
        }
        if !queryItems.isEmpty { components.queryItems = queryItems }
        guard let url = components.url else { throw APIError.invalidURL }

        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.setValue("ios", forHTTPHeaderField: "X-Client-Platform")

        if requiresAuth, let token = KeychainHelper.loadToken() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = bodyData

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: req)
        } catch {
            if retries > 0 {
                return try await perform(
                    path: path, method: method, bodyData: bodyData,
                    query: query, requiresAuth: requiresAuth, retries: retries - 1
                )
            }
            throw APIError.networkError(error)
        }

        guard let http = response as? HTTPURLResponse else { throw APIError.invalidURL }

        if http.statusCode == 401 {
            NotificationCenter.default.post(name: .sessionExpired, object: nil)
            throw APIError.unauthorized
        }

        if http.statusCode == 402,
           let body = try? decoder.decode(NeedsPlusBody.self, from: data),
           body.detail.code == "needs_plus" {
            NotificationCenter.default.post(
                name: .needsPlus,
                object: nil,
                userInfo: ["feature": body.detail.feature]
            )
            throw APIError.paymentRequired(feature: body.detail.feature)
        }

        guard (200..<300).contains(http.statusCode) else {
            let message = (try? decoder.decode(FastAPIErrorBody.self, from: data))?.message
                ?? String(data: data, encoding: .utf8)
                ?? "Server error"
            throw APIError.serverError(http.statusCode, message)
        }

        // 204 No Content (or empty body)
        if data.isEmpty, T.self == EmptyResponse.self {
            // Force a fresh EmptyResponse — JSONDecoder can't decode empty Data.
            return EmptyResponse() as! T
        }

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }
}
