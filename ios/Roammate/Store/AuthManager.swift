import SwiftUI
import Combine

@MainActor
final class AuthManager: ObservableObject {
    @Published var currentUser: User?
    @Published var isAuthenticated = false
    @Published var isLoading = false
    @Published var error: String?

    private var sessionObserver: NSObjectProtocol?

    init() {
        // When APIClient detects a 401, it broadcasts `.sessionExpired`. We
        // log out so the auth gate in ContentView swaps to LoginView.
        sessionObserver = NotificationCenter.default.addObserver(
            forName: .sessionExpired, object: nil, queue: .main
        ) { [weak self] _ in
            Task { @MainActor [weak self] in self?.logout() }
        }
    }

    deinit {
        if let sessionObserver { NotificationCenter.default.removeObserver(sessionObserver) }
    }

    func checkAuth() async {
        guard KeychainHelper.loadToken() != nil else { return }
        do {
            currentUser = try await AuthService.getMe()
            isAuthenticated = true
        } catch {
            KeychainHelper.deleteToken()
        }
    }

    func login(email: String, password: String) async {
        isLoading = true
        error = nil
        defer { isLoading = false }
        do {
            let token = try await AuthService.login(email: email, password: password)
            KeychainHelper.saveToken(token)
            currentUser = try await AuthService.getMe()
            isAuthenticated = true
        } catch let e as APIError {
            self.error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func register(name: String, email: String, password: String) async {
        isLoading = true
        error = nil
        defer { isLoading = false }
        do {
            _ = try await AuthService.register(name: name, email: email, password: password)
            await login(email: email, password: password)
        } catch let e as APIError {
            self.error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func logout() {
        KeychainHelper.deleteToken()
        DiskCache.shared.clearAll()
        currentUser = nil
        isAuthenticated = false
    }
}
