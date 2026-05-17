import SwiftUI

struct InvitationRow: View {
    let invitation: Invitation
    let onAccept: () async -> Void
    let onDecline: () async -> Void

    @State private var isWorking = false
    @State private var showDeclineConfirm = false

    private var roleLabel: String {
        switch invitation.role {
        case "admin": return "Admin"
        case "view_with_vote": return "Can vote"
        default: return "View only"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: RoammateSpacing.md) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(invitation.trip.name)
                        .font(.system(.headline, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.roammateInk)
                    if let inviter = invitation.inviter {
                        Text("Invited by \(inviter.name)")
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(Color.roammateMuted)
                    }
                }
                Spacer()
                PillLabel(text: roleLabel)
            }

            HStack(spacing: RoammateSpacing.sm) {
                Button {
                    Task {
                        isWorking = true
                        await onAccept()
                        HapticManager.success()
                        isWorking = false
                    }
                } label: {
                    Text("Accept")
                }
                .buttonStyle(RoammatePrimaryButtonStyle(isLoading: isWorking))
                .disabled(isWorking)

                Button {
                    showDeclineConfirm = true
                } label: {
                    Text("Decline")
                }
                .buttonStyle(RoammateSecondaryButtonStyle())
                .disabled(isWorking)
            }
        }
        .roammateCard()
        .confirmationDialog(
            "Decline invitation?",
            isPresented: $showDeclineConfirm,
            titleVisibility: .visible
        ) {
            Button("Decline", role: .destructive) {
                Task {
                    isWorking = true
                    await onDecline()
                    isWorking = false
                }
            }
            Button("Cancel", role: .cancel) {}
        }
    }
}
