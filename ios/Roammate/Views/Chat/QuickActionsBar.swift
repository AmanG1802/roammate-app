import SwiftUI

struct QuickActionsBar: View {
    let onMyDay: () -> Void
    let onWhatsNext: () -> Void
    let onFindNearby: () -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                chip(icon: "calendar", label: "My day", action: onMyDay)
                chip(icon: "arrow.right.circle", label: "What's next?", action: onWhatsNext)
                chip(icon: "mappin.circle", label: "Find nearby", action: onFindNearby)
            }
            .padding(.horizontal, RoammateSpacing.md)
        }
    }

    private func chip(icon: String, label: String, action: @escaping () -> Void) -> some View {
        Button {
            HapticManager.light()
            action()
        } label: {
            HStack(spacing: 6) {
                Image(systemName: icon).font(.system(size: 13, weight: .semibold))
                Text(label).font(.system(.footnote, design: .rounded, weight: .semibold))
            }
            .foregroundStyle(Color.roammateIndigo)
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(Capsule().fill(Color.roammateIndigoTint))
        }
        .buttonStyle(.plain)
    }
}
