import SwiftUI
import UIKit

/// Embeds a zero-height UIView at the top of a native sheet's content area and
/// publishes the sheet's live top-edge Y position (in window coordinates) back to
/// SwiftUI at the display refresh rate via CADisplayLink.
///
/// Embed this as the first item in the sheet's VStack with .frame(height: 0) so its
/// window-Y equals the sheet content's top edge. Use the published value to drive
/// any SwiftUI overlay that needs to float pixel-perfect above the sheet during drags.
struct SheetPositionTracker: UIViewRepresentable {
    @Binding var sheetTopY: CGFloat

    func makeUIView(context: Context) -> SheetTrackerView {
        SheetTrackerView(binding: $sheetTopY)
    }

    func updateUIView(_ uiView: SheetTrackerView, context: Context) {}

    static func dismantleUIView(_ uiView: SheetTrackerView, coordinator: ()) {
        uiView.stop()
    }
}

final class SheetTrackerView: UIView {
    private var binding: Binding<CGFloat>
    private var displayLink: CADisplayLink?

    init(binding: Binding<CGFloat>) {
        self.binding = binding
        super.init(frame: .zero)
        isUserInteractionEnabled = false
        backgroundColor = .clear
        alpha = 0

        let link = CADisplayLink(target: self, selector: #selector(tick))
        link.add(to: .main, forMode: .common)
        displayLink = link
    }

    required init?(coder: NSCoder) { fatalError() }

    func stop() {
        displayLink?.invalidate()
        displayLink = nil
    }

    @objc private func tick() {
        guard let window else { return }
        // convert(.zero, to: window) gives the top-left corner of this view in
        // window coordinates — i.e., the sheet content area's top-edge Y.
        let y = convert(.zero, to: window).y
        // Suppress SwiftUI re-renders while the sheet is stationary.
        if abs(y - binding.wrappedValue) > 0.5 {
            binding.wrappedValue = y
        }
    }
}
