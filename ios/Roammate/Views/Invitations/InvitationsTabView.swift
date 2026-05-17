import SwiftUI

struct InvitationsTabView: View {
    @EnvironmentObject var tripStore: TripStore

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(spacing: RoammateSpacing.md) {
                    if tripStore.pendingInvitations.isEmpty {
                        EmptyState(
                            icon: "envelope.open",
                            title: "No pending invitations",
                            subtitle: "When someone invites you to a trip, it'll show up here."
                        )
                        .padding(.top, RoammateSpacing.xxl)
                    } else {
                        ForEach(tripStore.pendingInvitations) { invitation in
                            InvitationRow(
                                invitation: invitation,
                                onAccept: { await tripStore.acceptInvitation(memberId: invitation.id) },
                                onDecline: { await tripStore.declineInvitation(memberId: invitation.id) }
                            )
                            .transition(.opacity.combined(with: .move(edge: .top)))
                        }
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.top, RoammateSpacing.md)
                .padding(.bottom, RoammateLayout.contentBottomPadding)
                .animation(.spring(response: 0.3, dampingFraction: 0.8), value: tripStore.pendingInvitations.count)
            }
            .background(Color.roammateBackground.ignoresSafeArea())
            .navigationTitle("Invitations")
            .navigationBarTitleDisplayMode(.large)
            .refreshable { await tripStore.loadInvitations() }
            .task { await tripStore.loadInvitations() }
        }
    }
}
