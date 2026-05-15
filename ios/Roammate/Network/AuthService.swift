import Foundation

struct LoginRequest: Encodable {
    let email: String
    let password: String
}

struct RegisterRequest: Encodable {
    let email: String
    let password: String
    let name: String
}

struct TokenResponse: Decodable {
    let accessToken: String
    let tokenType: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
    }
}

struct ProfileUpdate: Encodable {
    let name: String?
    let avatarUrl: String?
    let homeCity: String?
    let timezone: String?
    let currency: String?
    let travelBlurb: String?
    let password: String?
    let currentPassword: String?

    enum CodingKeys: String, CodingKey {
        case name, timezone, currency, password
        case avatarUrl = "avatar_url"
        case homeCity = "home_city"
        case travelBlurb = "travel_blurb"
        case currentPassword = "current_password"
    }
}

struct PersonasUpdate: Encodable {
    let personas: [String]
}

enum AuthService {
    static func login(email: String, password: String) async throws -> String {
        let body = LoginRequest(email: email, password: password)
        let response: TokenResponse = try await APIClient.shared.request(
            "/users/login", method: "POST", body: body, requiresAuth: false
        )
        return response.accessToken
    }

    static func register(name: String, email: String, password: String) async throws -> User {
        let body = RegisterRequest(email: email, password: password, name: name)
        return try await APIClient.shared.request(
            "/users/register", method: "POST", body: body, requiresAuth: false
        )
    }

    static func getMe() async throws -> User {
        try await APIClient.shared.request("/users/me")
    }

    static func updateMe(_ update: ProfileUpdate) async throws -> User {
        try await APIClient.shared.request("/users/me", method: "PUT", body: update)
    }

    static func updatePersonas(_ personas: [String]) async throws {
        let _: JSONValue = try await APIClient.shared.request(
            "/users/me/personas", method: "PUT", body: PersonasUpdate(personas: personas)
        )
    }

    static func deleteAccount() async throws {
        let _: EmptyResponse = try await APIClient.shared.request("/users/me", method: "DELETE")
    }
}
