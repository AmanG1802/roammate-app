import SwiftUI

struct TripConciergeView: View {
    let trip: Trip

    var body: some View {
        ZStack {
            Color.roammateBackground.ignoresSafeArea()
            ContentUnavailableView(
                "Concierge – coming soon",
                systemImage: "sparkles",
                description: Text("Trip-scoped AI concierge will live here.")
            )
        }
    }
}
