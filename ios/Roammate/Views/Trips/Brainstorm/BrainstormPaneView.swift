import SwiftUI

struct BrainstormPaneView: View {
    @EnvironmentObject var brainstormStore: BrainstormStore
    @EnvironmentObject var tutorial: TutorialStore
    @State private var page = 0

    var body: some View {
        PaneSlider(page: $page, pageCount: 2) {
            BrainstormChatView(page: $page)
                .tag(0)

            BrainstormBinView()
                .tag(1)
        }
        .task {
            await brainstormStore.load()
        }
        .onAppear { applyTutorialPane() }
        .onChange(of: tutorial.currentStep) { _, _ in applyTutorialPane() }
    }

    /// Tutorial: slide to chat (0) or bin (1) for the brainstorm steps.
    private func applyTutorialPane() {
        guard tutorial.isActive else { return }
        let loc = TutorialScript.location(for: tutorial.currentStep)
        if loc.subPage == .brainstorm, let idx = loc.paneIndex, page != idx {
            withAnimation { page = idx }
        }
    }
}
