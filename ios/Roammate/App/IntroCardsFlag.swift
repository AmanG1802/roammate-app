import Foundation

/// Install-wide "first-launch intro cards have been shown" flag.
///
/// Not keyed on user_id — survives logout/login and is reset only when the
/// app is uninstalled (which clears UserDefaults). Bump the key suffix to
/// force the cards to re-appear after a major overhaul.
enum IntroCardsFlag {
    private static let key = "intro_cards_seen_v1"

    static func hasSeen() -> Bool {
        UserDefaults.standard.bool(forKey: key)
    }

    static func markSeen() {
        UserDefaults.standard.set(true, forKey: key)
    }
}
