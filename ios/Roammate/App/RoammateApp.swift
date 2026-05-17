import SwiftUI

#if canImport(GoogleSignIn)
import GoogleSignIn
#endif

@main
struct RoammateApp: App {
    @StateObject private var authManager = AuthManager()
    @StateObject private var tripStore = TripStore()
    @StateObject private var groupStore = GroupStore()
    @StateObject private var notificationStore = NotificationStore()
    @StateObject private var subscriptionStore = SubscriptionStore()

    @State private var pendingResetToken: String?

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
                .environmentObject(tripStore)
                .environmentObject(groupStore)
                .environmentObject(notificationStore)
                .environmentObject(subscriptionStore)
                .tint(Color.roammateIndigo)
                .task {
                    await authManager.checkAuth()
                    if authManager.isAuthenticated {
                        await subscriptionStore.boot()
                    }
                }
                .onChange(of: authManager.isAuthenticated) { _, isAuth in
                    if isAuth {
                        Task {
                            await tripStore.load()
                            await tripStore.loadInvitations()
                            await groupStore.load()
                            await subscriptionStore.boot()
                        }
                    } else {
                        subscriptionStore.reset()
                    }
                }
                .onOpenURL { url in
                    #if canImport(GoogleSignIn)
                    if GIDSignIn.sharedInstance.handle(url) { return }
                    #endif
                    _ = authManager.handleDeepLink(url)
                }
                .onReceive(NotificationCenter.default.publisher(for: .authResetTokenReceived)) { note in
                    if let token = note.userInfo?["token"] as? String {
                        pendingResetToken = token
                    }
                }
                .sheet(item: Binding<ResetTokenWrapper?>(
                    get: { pendingResetToken.map(ResetTokenWrapper.init) },
                    set: { if $0 == nil { pendingResetToken = nil } }
                )) { wrapper in
                    ResetPasswordView(token: wrapper.token)
                        .environmentObject(authManager)
                }
        }
    }
}

private struct ResetTokenWrapper: Identifiable {
    let token: String
    var id: String { token }
}
