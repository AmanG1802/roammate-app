import SwiftUI

/// Local notification preferences. Backend doesn't have a prefs endpoint yet,
/// so these are stored in UserDefaults via @AppStorage. When we wire APNs and
/// the backend's `/users/me/notification-prefs` route, replace storage here.
struct NotificationsSettingsView: View {
    // Trip & members
    @AppStorage("notif.tripActivity")      private var tripActivity      = true
    @AppStorage("notif.invitations")       private var invitations       = true
    @AppStorage("notif.memberChanges")     private var memberChanges     = true

    // Itinerary
    @AppStorage("notif.ideaAdded")         private var ideaAdded         = true
    @AppStorage("notif.eventAdded")        private var eventAdded        = true
    @AppStorage("notif.eventMoved")        private var eventMoved        = true
    @AppStorage("notif.rippleFired")       private var rippleFired       = true

    // Groups
    @AppStorage("notif.groupActivity")     private var groupActivity     = true

    // AI
    @AppStorage("notif.aiSuggestions")     private var aiSuggestions     = true

    var body: some View {
        ZStack {
            Color.roammateBackground.ignoresSafeArea()
            List {
                Section("Trip activity") {
                    toggle("Trip created or updated", icon: "airplane", isOn: $tripActivity)
                    toggle("Invitations to trips", icon: "envelope.fill", isOn: $invitations)
                    toggle("Member added or removed", icon: "person.2.fill", isOn: $memberChanges)
                }

                Section("Itinerary") {
                    toggle("New idea in the bin", icon: "lightbulb.fill", isOn: $ideaAdded)
                    toggle("Event added to timeline", icon: "calendar.badge.plus", isOn: $eventAdded)
                    toggle("Event time or day moved", icon: "arrow.left.arrow.right", isOn: $eventMoved)
                    toggle("Ripple shifted the day", icon: "wave.3.right", isOn: $rippleFired)
                }

                Section("Groups") {
                    toggle("Group invitations and updates", icon: "person.3.fill", isOn: $groupActivity)
                }

                Section("Concierge") {
                    toggle("AI suggestions and reminders", icon: "sparkles", isOn: $aiSuggestions)
                }
            }
            .scrollContentBackground(.hidden)
        }
        .navigationTitle("Notifications")
        .navigationBarTitleDisplayMode(.inline)
    }

    @ViewBuilder
    private func toggle(_ title: String, icon: String, isOn: Binding<Bool>) -> some View {
        Toggle(isOn: isOn) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .foregroundStyle(Color.roammateIndigo)
                    .frame(width: 22)
                Text(title)
                    .font(.system(.body, design: .rounded))
                    .foregroundStyle(Color.roammateInk)
            }
        }
        .tint(Color.roammateIndigo)
    }
}
