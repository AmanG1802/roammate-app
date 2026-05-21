import Foundation

/// Per-user "Plus onboarding sheet has been shown" flag.
///
/// Cleared on logout and when a Plus subscriber downgrades back to free, so
/// the soft pitch can re-appear on their next free launch.
enum PlusOnboardingFlag {
    private static func key(for userId: Int) -> String {
        "plus_onboarding_shown_\(userId)"
    }

    static func hasSeen(userId: Int) -> Bool {
        UserDefaults.standard.bool(forKey: key(for: userId))
    }

    static func markSeen(userId: Int) {
        UserDefaults.standard.set(true, forKey: key(for: userId))
    }

    static func clear(userId: Int) {
        UserDefaults.standard.removeObject(forKey: key(for: userId))
    }
}
