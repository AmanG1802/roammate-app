import SwiftUI

struct PlanPaneView: View {
    @EnvironmentObject var store: TripDetailStore
    @EnvironmentObject var tutorial: TutorialStore

    var body: some View {
        PlanMapPage()
    }
}
