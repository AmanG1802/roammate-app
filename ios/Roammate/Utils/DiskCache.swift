import Foundation

/// File-backed JSON cache. Used by stores for stale-while-revalidate:
/// load from cache for instant display, then refresh from the network
/// in the background. Stores each key as a separate file in the Caches
/// directory to avoid the ~4 MB per-entry UserDefaults limit.
final class DiskCache {
    static let shared = DiskCache()

    private let cacheDir: URL
    private let queue = DispatchQueue(label: "com.roammate.diskcache", qos: .utility)

    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()

    private let decoder: JSONDecoder = {
        APIClient.shared.decoder
    }()

    private init() {
        let base = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first!
        cacheDir = base.appendingPathComponent("roammate_cache", isDirectory: true)
        try? FileManager.default.createDirectory(at: cacheDir, withIntermediateDirectories: true)
        migrateFromUserDefaults()
    }

    func store<T: Encodable>(_ value: T, key: String) {
        guard let data = try? encoder.encode(value) else { return }
        let url = fileURL(for: key)
        queue.async {
            try? data.write(to: url, options: .atomic)
        }
    }

    func load<T: Decodable>(_ type: T.Type, key: String) -> T? {
        let url = fileURL(for: key)
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? decoder.decode(type, from: data)
    }

    func remove(key: String) {
        let url = fileURL(for: key)
        queue.async {
            try? FileManager.default.removeItem(at: url)
        }
    }

    /// Wipe all roammate cache files. Called on logout.
    func clearAll() {
        queue.async { [cacheDir] in
            try? FileManager.default.removeItem(at: cacheDir)
            try? FileManager.default.createDirectory(at: cacheDir, withIntermediateDirectories: true)
        }
    }

    private func fileURL(for key: String) -> URL {
        let safe = key.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? key
        return cacheDir.appendingPathComponent(safe + ".json")
    }

    /// One-time migration: move any existing UserDefaults cache entries to files.
    private func migrateFromUserDefaults() {
        let defaults = UserDefaults.standard
        let prefix = "roammate.cache."
        var keysToRemove: [String] = []
        for (key, value) in defaults.dictionaryRepresentation() {
            guard key.hasPrefix(prefix) else { continue }
            let shortKey = String(key.dropFirst(prefix.count))
            if let data = value as? Data {
                let url = fileURL(for: shortKey)
                try? data.write(to: url, options: .atomic)
            }
            keysToRemove.append(key)
        }
        for key in keysToRemove {
            defaults.removeObject(forKey: key)
        }
    }
}
