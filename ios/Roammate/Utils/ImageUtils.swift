import UIKit

extension UIImage {
    /// Decode a `data:image/...;base64,<payload>` URI into a UIImage.
    /// Returns nil for non-data URIs or invalid payloads.
    static func fromDataURI(_ uri: String) -> UIImage? {
        guard uri.hasPrefix("data:"),
              let commaIdx = uri.firstIndex(of: ",") else { return nil }
        let base64 = String(uri[uri.index(after: commaIdx)...])
        guard let data = Data(base64Encoded: base64, options: .ignoreUnknownCharacters) else { return nil }
        return UIImage(data: data)
    }
}
