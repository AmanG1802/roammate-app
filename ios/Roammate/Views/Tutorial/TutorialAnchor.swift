import SwiftUI

/// PreferenceKey carrying per-anchor bounds for the tutorial overlay.
/// Targets in the view tree publish their rect via `.tutorialAnchor(id:)`;
/// the overlay reads them with `geometryProxy[anchor]`.
struct TutorialAnchorKey: PreferenceKey {
    static var defaultValue: [String: Anchor<CGRect>] = [:]
    static func reduce(
        value: inout [String: Anchor<CGRect>],
        nextValue: () -> [String: Anchor<CGRect>]
    ) {
        value.merge(nextValue(), uniquingKeysWith: { $1 })
    }
}

extension View {
    /// Attach this view to the tutorial coordinator under *id*. The overlay
    /// uses the published rect to size and position the spotlight cutout.
    func tutorialAnchor(_ id: String) -> some View {
        anchorPreference(key: TutorialAnchorKey.self, value: .bounds) { [id: $0] }
    }

    /// Conditionally attach a tutorial anchor — no-op when *id* is nil.
    @ViewBuilder
    func tutorialAnchorIf(_ id: String?) -> some View {
        if let id { tutorialAnchor(id) } else { self }
    }
}
