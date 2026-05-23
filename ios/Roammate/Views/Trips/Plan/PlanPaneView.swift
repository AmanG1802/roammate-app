import SwiftUI

struct PlanPaneView: View {
    @EnvironmentObject var store: TripDetailStore
    @EnvironmentObject var tutorial: TutorialStore
    @State private var page = 0

    var body: some View {
        PaneSlider(page: $page, pageCount: 2) {
            PlanMapPage()
                .tag(0)

            IdeaBinView()
                .tag(1)
        }
        .onAppear { applyTutorialPane() }
        .onChange(of: tutorial.currentStep) { _, _ in applyTutorialPane() }
    }

    /// Tutorial: slide to timeline (0) or idea-bin (1) for the plan steps.
    private func applyTutorialPane() {
        guard tutorial.isActive else { return }
        let loc = TutorialScript.location(for: tutorial.currentStep)
        if loc.subPage == .plan, let idx = loc.paneIndex, page != idx {
            withAnimation { page = idx }
        }
    }
}
