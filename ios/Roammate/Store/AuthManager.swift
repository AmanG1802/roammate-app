import SwiftUI
import Combine
import AuthenticationServices
import CryptoKit

@MainActor
final class AuthManager: NSObject, ObservableObject {
    @Published var currentUser: User?
    @Published var isAuthenticated = false
    @Published var isLoading = false
    @Published var error: String?
    @Published var pendingVerificationEmail: String?

    private var sessionObserver: NSObjectProtocol?
    private var appleNonce: String?
    private var pendingPassword: String?

    override init() {
        super.init()
        sessionObserver = NotificationCenter.default.addObserver(
            forName: .sessionExpired, object: nil, queue: .main
        ) { [weak self] _ in
            Task { @MainActor [weak self] in self?.logout() }
        }
    }

    deinit {
        if let sessionObserver { NotificationCenter.default.removeObserver(sessionObserver) }
    }

    // MARK: - Session boot

    func checkAuth() async {
        // If the access token is missing but a refresh token exists, attempt a
        // silent refresh before giving up (covers Keychain eviction edge cases).
        if KeychainHelper.loadToken() == nil {
            guard let raw = KeychainHelper.loadRefreshToken() else { return }
            do {
                let pair = try await AuthService.refresh(refreshToken: raw)
                KeychainHelper.saveToken(pair.access_token)
                KeychainHelper.saveRefreshToken(pair.refresh_token)
            } catch {
                KeychainHelper.clearAll()
                return
            }
        }
        do {
            currentUser = try await AuthService.getMe()
            isAuthenticated = true
        } catch {
            // /users/me requires email_verified; if 403 the client should route
            // through the verify flow rather than wipe.
            if let api = error as? APIError, case .serverError(let status, _) = api, status == 403 {
                pendingVerificationEmail = nil
                logout()
            } else {
                KeychainHelper.clearAll()
            }
        }
    }

    // MARK: - Email + password

    func login(email: String, password: String) async {
        await run {
            do {
                let pair = try await AuthService.login(email: email, password: password)
                self.persist(pair)
            } catch APIError.serverError(409, _) {
                self.pendingVerificationEmail = email
                self.pendingPassword = password
                self.error = "Please verify your email — check your inbox."
            }
        }
    }

    func skipVerification() async {
        guard let email = pendingVerificationEmail, let password = pendingPassword else { return }
        await run {
            let pair = try await AuthService.login(email: email, password: password, skipVerification: true)
            self.pendingPassword = nil
            self.persist(pair)
        }
    }

    func signup(name: String, email: String, password: String) async {
        await run {
            try await AuthService.signup(name: name, email: email, password: password)
            self.pendingVerificationEmail = email
        }
    }

    func resendVerification(email: String) async {
        await run { try await AuthService.resendVerification(email: email) }
    }

    func consumeVerification(token: String) async {
        await run {
            let pair = try await AuthService.verify(token: token)
            self.persist(pair)
            self.pendingVerificationEmail = nil
        }
    }

    func forgotPassword(email: String) async {
        await run { try await AuthService.forgotPassword(email: email) }
    }

    func resetPassword(token: String, newPassword: String) async {
        await run {
            let pair = try await AuthService.resetPassword(token: token, newPassword: newPassword)
            self.persist(pair)
        }
    }

    // MARK: - Google

    func signInWithGoogle(idToken: String) async {
        await run {
            let pair = try await AuthService.loginWithGoogle(idToken: idToken)
            self.persist(pair)
        }
    }

    // MARK: - Apple

    /// Build a fresh nonce for the next Sign-in-with-Apple request.
    /// The raw value is stored locally and the SHA-256 returned for ASAuthorizationAppleIDRequest.
    func prepareAppleNonce() -> String {
        let raw = Self.randomNonceString()
        appleNonce = raw
        return Self.sha256(raw)
    }

    func handleAppleAuthorization(_ authorization: ASAuthorization) async {
        guard
            let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
            let tokenData = credential.identityToken,
            let idToken = String(data: tokenData, encoding: .utf8)
        else {
            error = "Apple sign-in failed: no identity token"
            return
        }
        let nonce = appleNonce
        appleNonce = nil
        await run {
            let pair = try await AuthService.loginWithApple(idToken: idToken, nonce: nonce)
            self.persist(pair)
        }
    }

    // MARK: - Logout

    func logout() {
        Task { try? await AuthService.logout() }
        if let uid = currentUser?.id {
            PlusOnboardingFlag.clear(userId: uid)
        }
        KeychainHelper.clearAll()
        DiskCache.shared.clearAll()
        currentUser = nil
        isAuthenticated = false
        pendingVerificationEmail = nil
        pendingPassword = nil
    }

    // MARK: - Deep links (universal links: /verify, /reset)

    /// Returns true if the URL was consumed by the auth flow.
    func handleDeepLink(_ url: URL) -> Bool {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return false }
        let path = components.path
        let token = components.queryItems?.first(where: { $0.name == "token" })?.value
        guard let token else { return false }
        if path.hasSuffix("/verify") {
            Task { await consumeVerification(token: token) }
            return true
        }
        if path.hasSuffix("/reset") {
            NotificationCenter.default.post(
                name: .authResetTokenReceived, object: nil, userInfo: ["token": token]
            )
            return true
        }
        return false
    }

    // MARK: - Helpers

    private func persist(_ pair: AuthTokenPair) {
        KeychainHelper.saveToken(pair.access_token)
        KeychainHelper.saveRefreshToken(pair.refresh_token)
        Task {
            do {
                self.currentUser = try await AuthService.getMe()
                self.isAuthenticated = true
                self.pendingVerificationEmail = nil
            } catch {
                self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
            }
        }
    }

    private func run(_ op: @escaping () async throws -> Void) async {
        isLoading = true
        error = nil
        defer { isLoading = false }
        do {
            try await op()
        } catch let e as APIError {
            self.error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: - Nonce utilities (Apple recommends a SHA-256-hashed nonce)

    private static func randomNonceString(length: Int = 32) -> String {
        precondition(length > 0)
        let charset: [Character] = Array("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-._")
        var result = ""
        var remainingLength = length
        while remainingLength > 0 {
            var randoms = [UInt8](repeating: 0, count: 16)
            let status = SecRandomCopyBytes(kSecRandomDefault, randoms.count, &randoms)
            precondition(status == errSecSuccess)
            for random in randoms where remainingLength > 0 {
                if random < charset.count {
                    result.append(charset[Int(random)])
                    remainingLength -= 1
                }
            }
        }
        return result
    }

    private static func sha256(_ input: String) -> String {
        let hash = SHA256.hash(data: Data(input.utf8))
        return hash.map { String(format: "%02x", $0) }.joined()
    }
}

extension Notification.Name {
    static let authResetTokenReceived = Notification.Name("com.roammate.authResetTokenReceived")
}
