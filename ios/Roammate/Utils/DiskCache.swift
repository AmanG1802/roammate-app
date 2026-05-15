import Foundation

/// Simple `UserDefaults`-backed JSON cache. Used by stores for
/// stale-while-revalidate: load from cache for instant display, then refresh
/// from the network in the background.
final class DiskCache {
    static let shared = DiskCache()
    private let defaults = UserDefaults.standard

    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()

    private let decoder: JSONDecoder = {
        APIClient.shared.decoder
    }()

    private init() {}

    func store<T: Encodable>(_ value: T, key: String) {
        if let data = try? encoder.encode(value) {
            defaults.set(data, forKey: cacheKey(key))
        }
    }

    func load<T: Decodable>(_ type: T.Type, key: String) -> T? {
        guard let data = defaults.data(forKey: cacheKey(key)) else { return nil }
        return try? decoder.decode(type, from: data)
    }

    func remove(key: String) {
        defaults.removeObject(forKey: cacheKey(key))
    }

    /// Wipe all roammate cache entries. Called on logout.
    func clearAll() {
        let prefix = "roammate.cache."
        for key in defaults.dictionaryRepresentation().keys where key.hasPrefix(prefix) {
            defaults.removeObject(forKey: key)
        }
    }

    private func cacheKey(_ key: String) -> String {
        "roammate.cache.\(key)"
    }
}
