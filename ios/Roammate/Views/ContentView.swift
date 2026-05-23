import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authManager: AuthManager
    @State private var introSeen: Bool = IntroCardsFlag.hasSeen()

    var body: some View {
        Group {
            if authManager.isAuthenticated {
                MainShell()
            } else if !introSeen {
                IntroCardsView(onFinish: {
                    IntroCardsFlag.markSeen()
                    introSeen = true
                })
            } else {
                LoginView()
            }
        }
        .animation(.easeInOut(duration: 0.25), value: authManager.isAuthenticated)
        .animation(.easeInOut(duration: 0.25), value: introSeen)
        .observePaywall()
    }
}
