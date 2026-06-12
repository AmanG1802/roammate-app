import SwiftUI

enum DrawerTab: Equatable {
    case timeline
    case ideaBin
}

struct DrawerTabStrip: View {
    @Binding var selection: DrawerTab

    var body: some View {
        HStack(spacing: 3) {
            tabButton(.timeline, icon: "calendar", label: "Timeline")
            tabButton(.ideaBin, icon: "lightbulb.fill", label: "Idea Bin")
        }
        .padding(4)
        .background(
            Capsule()
                .fill(Color.roammateBackground)
                .overlay(Capsule().stroke(Color.roammateBorder, lineWidth: 0.5))
        )
        .shadow(color: .black.opacity(0.04), radius: 4, y: 1)
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.top, 10)
        .padding(.bottom, 6)
    }

    private func tabButton(_ tab: DrawerTab, icon: String, label: String) -> some View {
        let isActive = selection == tab
        let accent: Color = tab == .timeline ? .roammateEmerald : .roammateAmber

        return Button {
            HapticManager.selection()
            withAnimation(.spring(response: 0.25, dampingFraction: 0.8)) {
                selection = tab
            }
        } label: {
            HStack(spacing: 5) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .black))
                Text(label)
                    .font(.system(size: 12, weight: .black))
                    .tracking(0.2)
            }
            .foregroundStyle(isActive ? accent : Color.roammateMuted)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .frame(maxWidth: .infinity)
            .background(
                Capsule()
                    .fill(isActive ? accent.opacity(0.12) : Color.clear)
            )
            .contentShape(Capsule())
        }
        .buttonStyle(.plain)
        .animation(.spring(response: 0.25, dampingFraction: 0.8), value: isActive)
    }
}
