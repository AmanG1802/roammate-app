import SwiftUI

enum AppTab: Int, CaseIterable, Identifiable {
    case dashboard, trips, invitations, groups, profile

    var id: Int { rawValue }

    var icon: String {
        switch self {
        case .dashboard:   return "house.fill"
        case .trips:       return "map.fill"
        case .invitations: return "envelope.fill"
        case .groups:      return "person.3.fill"
        case .profile:     return "person.crop.circle.fill"
        }
    }

    var title: String {
        switch self {
        case .dashboard:   return "Home"
        case .trips:       return "Trips"
        case .invitations: return "Inbox"
        case .groups:      return "Groups"
        case .profile:     return "Profile"
        }
    }
}

struct FloatingTabBar: View {
    @Binding var selection: AppTab

    var body: some View {
        HStack(spacing: 0) {
            ForEach(AppTab.allCases) { tab in
                tabButton(tab)
            }
        }
        .frame(height: 56)
        .padding(.horizontal, 4)
        .background(
            Capsule(style: .continuous)
                .fill(.regularMaterial)
        )
        .overlay(
            Capsule(style: .continuous)
                .strokeBorder(Color.white.opacity(0.5), lineWidth: 0.5)
        )
        .shadow(
            color: RoammateShadow.floating.color,
            radius: 12, x: 0, y: 4
        )
        .padding(.horizontal, RoammateSpacing.lg)
        .frame(maxWidth: .infinity)   // constrain horizontal so material clips correctly
    }

    @ViewBuilder
    private func tabButton(_ tab: AppTab) -> some View {
        let isSelected = selection == tab

        Button {
            if selection != tab {
                HapticManager.selection()
                withAnimation(.spring(response: 0.35, dampingFraction: 0.75)) {
                    selection = tab
                }
            }
        } label: {
            ZStack {
                // Per-cell selection pill (no matchedGeometryEffect — was causing layout bug)
                Capsule()
                    .fill(Color.roammateIndigo)
                    .padding(.vertical, 6)
                    .padding(.horizontal, 4)
                    .opacity(isSelected ? 1 : 0)
                    .scaleEffect(isSelected ? 1 : 0.9)
                    .animation(.spring(response: 0.35, dampingFraction: 0.8), value: isSelected)

                Image(systemName: tab.icon)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(isSelected ? .white : Color.roammateMuted)
                    .scaleEffect(isSelected ? 1.05 : 1.0)
                    .animation(.spring(response: 0.35, dampingFraction: 0.8), value: isSelected)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .contentShape(Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(tab.title)
    }
}
