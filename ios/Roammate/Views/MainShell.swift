import SwiftUI

/// Root authenticated shell: a 5-tab experience with a floating pill nav.
/// Each tab hosts its own NavigationStack so push/pop is per-tab.
struct MainShell: View {
    @State private var selection: AppTab = .dashboard
    @StateObject private var tabBarVisibility = TabBarVisibility()

    var body: some View {
        ZStack(alignment: .bottom) {
            Color.roammateBackground.ignoresSafeArea()

            Group {
                switch selection {
                case .dashboard:   DashboardView()
                case .trips:       TripsTabView()
                case .invitations: InvitationsTabView()
                case .groups:      GroupsTabView()
                case .profile:     ProfileTabView()
                }
            }
            .transition(.opacity)
            .animation(.easeInOut(duration: 0.18), value: selection)

            if tabBarVisibility.isVisible {
                FloatingTabBar(selection: $selection)
                    .padding(.bottom, RoammateLayout.tabBarBottomInset)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .animation(.spring(response: 0.35, dampingFraction: 0.85), value: tabBarVisibility.isVisible)
        .environment(\.tabBarVisibility, tabBarVisibility)
        .environmentObject(tabBarVisibility)
    }
}
