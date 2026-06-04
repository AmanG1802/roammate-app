import Foundation

// MARK: - Wire shapes (match /api/auth/* on the backend)

struct AuthEmailLoginRequest: Encodable {
    let email: String
    let password: String
    let skip_verification: Bool?
}

struct AuthEmailSignupRequest: Encodable {
    let email: String
    let password: String
    let name: String
}

struct AuthOAuthRequest: Encodable {
    let id_token: String
    let platform: String          // "ios"
    let nonce: String?
    let authorization_code: String?
}

struct AuthVerifyRequest: Encodable {
    let token: String
}

struct AuthResendRequest: Encodable {
    let email: String
}

struct AuthForgotRequest: Encodable {
    let email: String
}

struct AuthResetRequest: Encodable {
    let token: String
    let new_password: String
}

struct AuthRefreshRequest: Encodable {
    let refresh_token: String
}

struct AuthUserPayload: Decodable {
    let id: Int
    let email: String
    let name: String?
    let avatar_url: String?
    let email_verified: Bool
}

struct AuthTokenPair: Decodable {
    let access_token: String
    let refresh_token: String
    let token_type: String
    let expires_in: Int
    let user: AuthUserPayload
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
    // MARK: - Email + password

    static func signup(name: String, email: String, password: String) async throws {
        let body = AuthEmailSignupRequest(email: email, password: password, name: name)
        let _: JSONValue = try await APIClient.shared.request(
            "/auth/signup", method: "POST", body: body, requiresAuth: false
        )
    }

    static func login(email: String, password: String, skipVerification: Bool = false) async throws -> AuthTokenPair {
        let body = AuthEmailLoginRequest(
            email: email, password: password,
            skip_verification: skipVerification ? true : nil
        )
        return try await APIClient.shared.request(
            "/auth/login", method: "POST", body: body, requiresAuth: false
        )
    }

    // MARK: - OAuth

    static func loginWithGoogle(idToken: String) async throws -> AuthTokenPair {
        let body = AuthOAuthRequest(id_token: idToken, platform: "ios", nonce: nil, authorization_code: nil)
        return try await APIClient.shared.request(
            "/auth/google", method: "POST", body: body, requiresAuth: false
        )
    }

    static func loginWithApple(idToken: String, nonce: String?, authorizationCode: String?) async throws -> AuthTokenPair {
        let body = AuthOAuthRequest(id_token: idToken, platform: "ios", nonce: nonce, authorization_code: authorizationCode)
        return try await APIClient.shared.request(
            "/auth/apple", method: "POST", body: body, requiresAuth: false
        )
    }

    // MARK: - Verification + reset

    static func verify(token: String) async throws -> AuthTokenPair {
        try await APIClient.shared.request(
            "/auth/verify", method: "POST", body: AuthVerifyRequest(token: token), requiresAuth: false
        )
    }

    static func resendVerification(email: String) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/auth/verify/resend", method: "POST", body: AuthResendRequest(email: email), requiresAuth: false
        )
    }

    static func forgotPassword(email: String) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            "/auth/password/forgot", method: "POST", body: AuthForgotRequest(email: email), requiresAuth: false
        )
    }

    static func resetPassword(token: String, newPassword: String) async throws -> AuthTokenPair {
        try await APIClient.shared.request(
            "/auth/password/reset", method: "POST",
            body: AuthResetRequest(token: token, new_password: newPassword), requiresAuth: false
        )
    }

    // MARK: - Session lifecycle

    static func refresh(refreshToken: String) async throws -> AuthTokenPair {
        try await APIClient.shared.request(
            "/auth/refresh", method: "POST",
            body: AuthRefreshRequest(refresh_token: refreshToken), requiresAuth: false
        )
    }

    static func logout() async throws {
        let body = KeychainHelper.loadRefreshToken().map { AuthRefreshRequest(refresh_token: $0) }
        let _: EmptyResponse = try await APIClient.shared.request(
            "/auth/logout", method: "POST", body: body, requiresAuth: true
        )
    }

    // MARK: - Profile (still on /users)

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
