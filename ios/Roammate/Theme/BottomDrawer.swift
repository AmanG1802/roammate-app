import SwiftUI

enum DrawerDetent: Equatable {
    case minimised(CGFloat)
    case fraction(CGFloat)

    func height(in totalHeight: CGFloat) -> CGFloat {
        switch self {
        case .minimised(let h): return h
        case .fraction(let f): return totalHeight * f
        }
    }
}

struct BottomDrawer<Content: View>: View {
    let detents: [DrawerDetent]
    @Binding var current: DrawerDetent
    @ViewBuilder let content: () -> Content

    @State private var dragOffset: CGFloat = 0
    @State private var drawerHeight: CGFloat = 0

    private let cornerRadius: CGFloat = 28
    private let handleHeight: CGFloat = 28

    var body: some View {
        GeometryReader { geo in
            let totalH = geo.size.height
            let targetH = current.height(in: totalH)

            VStack(spacing: 0) {
                handle
                    .gesture(
                        DragGesture()
                            .onChanged { v in
                                dragOffset = v.translation.height
                            }
                            .onEnded { v in
                                let projected = targetH - v.translation.height
                                let nearest = detents.min(by: {
                                    abs($0.height(in: totalH) - projected) <
                                    abs($1.height(in: totalH) - projected)
                                }) ?? current
                                withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                                    current = nearest
                                    dragOffset = 0
                                }
                            }
                    )

                ScrollView {
                    content()
                }
                .scrollDisabled(current == .minimised(140))
            }
            .frame(height: max(0, targetH - dragOffset))
            .frame(maxWidth: .infinity)
            .background(
                UnevenRoundedRectangle(
                    topLeadingRadius: cornerRadius,
                    topTrailingRadius: cornerRadius
                )
                .fill(Color.roammateSurface)
                .shadow(color: .black.opacity(0.08), radius: 16, y: -4)
            )
            .frame(maxHeight: .infinity, alignment: .bottom)
            .animation(.spring(response: 0.35, dampingFraction: 0.85), value: current)
        }
    }

    private var handle: some View {
        VStack(spacing: 0) {
            Capsule()
                .fill(Color.secondary.opacity(0.4))
                .frame(width: 36, height: 5)
                .padding(.top, 10)
                .padding(.bottom, 13)
        }
        .frame(maxWidth: .infinity)
        .frame(height: handleHeight)
        .contentShape(Rectangle())
    }
}
