import SwiftUI
import UIKit

/// Introspects the enclosing UISheetPresentationController and disables the default
/// "scroll to expand" behaviour, so list content scrolls freely at any detent without
/// first snapping the sheet to large.
///
/// Embed as .background { ScrollableAtAnyDetent() } on the sheet's root content view.
struct ScrollableAtAnyDetent: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> UIViewController {
        UIViewController()
    }

    func updateUIViewController(_ vc: UIViewController, context: Context) {
        DispatchQueue.main.async {
            vc.sheetPresentationController?
                .prefersScrollingExpandsWhenScrolledToEdge = false
        }
    }
}
