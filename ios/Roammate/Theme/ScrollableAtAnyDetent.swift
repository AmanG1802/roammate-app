import SwiftUI

/// Introspects the enclosing UISheetPresentationController and disables
/// the default "scroll to expand" behaviour so list content scrolls freely
/// at any detent without first expanding the sheet.
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
