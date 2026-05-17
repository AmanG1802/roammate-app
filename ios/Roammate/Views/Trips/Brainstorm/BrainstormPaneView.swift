import SwiftUI

struct BrainstormPaneView: View {
    @EnvironmentObject var brainstormStore: BrainstormStore
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
    }
}
