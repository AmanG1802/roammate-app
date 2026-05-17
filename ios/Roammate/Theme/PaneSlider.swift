import SwiftUI

struct PaneSlider<Content: View>: View {
    @Binding var page: Int
    let pageCount: Int
    @ViewBuilder let content: () -> Content

    var body: some View {
        ZStack(alignment: .top) {
            TabView(selection: $page) {
                content()
            }
            .tabViewStyle(.page(indexDisplayMode: .never))

            pagerDots
                .padding(.top, 8)
        }
    }

    private var pagerDots: some View {
        HStack(spacing: 6) {
            ForEach(0..<pageCount, id: \.self) { idx in
                Circle()
                    .fill(idx == page ? Color.roammateIndigo : Color.roammateMuted.opacity(0.3))
                    .frame(width: 6, height: 6)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 4)
        .background(Capsule().fill(.ultraThinMaterial))
    }
}
