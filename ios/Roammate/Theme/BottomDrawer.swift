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
    var panelAnchorID: String? = nil
    @ViewBuilder let content: () -> Content

    // Tracks live drag position. Kept as @State (not @GestureState) so that
    // onEnded can animate it back to 0 together with the detent snap.
    @State private var dragOffset: CGFloat = 0

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
                                // Direct assignment — no animation, pure finger tracking.
                                dragOffset = v.translation.height
                            }
                            .onEnded { v in
                                // predictedEndTranslation incorporates velocity so fast
                                // flicks snap to the correct detent without full travel.
                                let projected = targetH - v.predictedEndTranslation.height
                                let nearest = detents.min(by: {
                                    abs($0.height(in: totalH) - projected) <
                                    abs($1.height(in: totalH) - projected)
                                }) ?? current
                                withAnimation(.interactiveSpring(response: 0.4, dampingFraction: 0.82)) {
                                    current = nearest
                                    dragOffset = 0
                                }
                            }
                    )

                ScrollView {
                    content()
                }
                // Disable scroll both at minimised detent and during an active
                // drag so the two gesture recognisers don't compete.
                .scrollDisabled(current == .minimised(140) || dragOffset != 0)
            }
            // Frame stays FIXED at targetH — no layout work during drag.
            .frame(height: max(0, targetH))
            // Live drag position via a GPU-only offset transform (zero layout cost).
            .offset(y: dragOffset)
            .frame(maxWidth: .infinity)
            .background(
                UnevenRoundedRectangle(
                    topLeadingRadius: cornerRadius,
                    topTrailingRadius: cornerRadius
                )
                .fill(Color.roammateSurface)
                .shadow(color: .black.opacity(0.08), radius: 16, y: -4)
            )
            .tutorialAnchorIf(panelAnchorID)
            .frame(maxHeight: .infinity, alignment: .bottom)
            // Animate detent changes. dragOffset changes during drag are NOT
            // wrapped in withAnimation so this implicit animation never fires
            // for raw tracking — only for the snap in onEnded.
            .animation(.interactiveSpring(response: 0.4, dampingFraction: 0.82), value: current)
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
