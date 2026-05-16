import Foundation
import Security

enum KeychainHelper {
    private static let service = "com.roammate.app"
    private static let tokenKey = "auth_token"
    private static let refreshKey = "refresh_token"

    // MARK: - Generic

    private static func save(_ value: String, key: String) {
        guard let data = value.data(using: .utf8) else { return }
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
        ]
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }

    private static func load(key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var result: AnyObject?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    private static func delete(key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
        ]
        SecItemDelete(query as CFDictionary)
    }

    // MARK: - Access token

    static func saveToken(_ token: String)   { save(token, key: tokenKey) }
    static func loadToken() -> String?       { load(key: tokenKey) }
    static func deleteToken()                { delete(key: tokenKey) }

    // MARK: - Refresh token

    static func saveRefreshToken(_ token: String) { save(token, key: refreshKey) }
    static func loadRefreshToken() -> String?     { load(key: refreshKey) }
    static func deleteRefreshToken()              { delete(key: refreshKey) }

    /// Wipes both tokens — used on logout / session-revoked.
    static func clearAll() {
        deleteToken()
        deleteRefreshToken()
    }
}
