import SwiftUI

struct PlanPaneView: View {
    @EnvironmentObject var store: TripDetailStore
    @State private var page = 0

    var body: some View {
        PaneSlider(page: $page, pageCount: 2) {
            PlanMapPage()
                .tag(0)

            IdeaBinView()
                .tag(1)
        }
    }
}
