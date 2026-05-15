import SwiftUI

@main
struct RoammateApp: App {
    @StateObject private var authManager = AuthManager()
    @StateObject private var tripStore = TripStore()
    @StateObject private var groupStore = GroupStore()
    @StateObject private var notificationStore = NotificationStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
                .environmentObject(tripStore)
                .environmentObject(groupStore)
                .environmentObject(notificationStore)
                .tint(Color.roammateIndigo)
                .task {
                    await authManager.checkAuth()
                }
                .onChange(of: authManager.isAuthenticated) { _, isAuth in
                    if isAuth {
                        Task {
                            await tripStore.load()
                            await tripStore.loadInvitations()
                            await groupStore.load()
                        }
                    }
                }
        }
    }
}
