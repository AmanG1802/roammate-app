import SwiftUI

struct PeoplePaneView: View {
    @EnvironmentObject var store: TripDetailStore
    @EnvironmentObject var authManager: AuthManager

    @State private var showInvite = false
    @State private var memberToRemove: TripMember?
    @State private var memberToChangeRole: TripMember?

    private var currentUserId: Int { authManager.currentUser?.id ?? -1 }

    private var isAdmin: Bool {
        store.members.first(where: { $0.userId == currentUserId })?.role == "admin"
    }

    private var acceptedMembers: [TripMember] {
        store.members.filter { $0.status == "accepted" }
    }

    private var pendingMembers: [TripMember] {
        store.members.filter { $0.status == "invited" }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: RoammateSpacing.lg) {
                header
                travellersSection
                if !pendingMembers.isEmpty {
                    pendingSection
                }
            }
            .padding(.top, RoammateSpacing.md)
            .padding(.bottom, RoammateSpacing.xl)
        }
        .background(Color.roammateBackground)
        .sheet(isPresented: $showInvite) {
            InviteSheet { email, role in
                await store.invite(email: email, role: role)
            }
            .presentationDetents([.medium])
        }
        .alert("Remove member?", isPresented: .init(
            get: { memberToRemove != nil },
            set: { if !$0 { memberToRemove = nil } }
        )) {
            Button("Remove", role: .destructive) {
                if let m = memberToRemove {
                    Task { await store.removeMember(memberId: m.id) }
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            if let m = memberToRemove {
                Text("Remove \(m.user.name) from this trip?")
            }
        }
        .confirmationDialog("Change role", isPresented: .init(
            get: { memberToChangeRole != nil },
            set: { if !$0 { memberToChangeRole = nil } }
        ), titleVisibility: .visible) {
            Button("Admin") { changeRole("admin") }
            Button("Can vote") { changeRole("view_with_vote") }
            Button("View only") { changeRole("view_only") }
            Button("Cancel", role: .cancel) {}
        }
    }

    private var header: some View {
        HStack {
            Text("People")
                .font(.system(.title2, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateInk)

            Spacer()

            if isAdmin {
                Button {
                    HapticManager.light()
                    showInvite = true
                } label: {
                    Image(systemName: "plus.circle.fill")
                        .font(.system(size: 24))
                        .foregroundStyle(Color.roammateIndigo)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, RoammateSpacing.md)
    }

    private var travellersSection: some View {
        VStack(alignment: .leading, spacing: RoammateSpacing.sm) {
            Text("Travellers")
                .font(.system(.subheadline, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateMuted)
                .padding(.horizontal, RoammateSpacing.md)

            ForEach(acceptedMembers) { member in
                memberRow(member)
            }
        }
    }

    private var pendingSection: some View {
        VStack(alignment: .leading, spacing: RoammateSpacing.sm) {
            Text("Pending invitations")
                .font(.system(.subheadline, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateMuted)
                .padding(.horizontal, RoammateSpacing.md)

            ForEach(pendingMembers) { member in
                pendingRow(member)
            }
        }
    }

    private func memberRow(_ member: TripMember) -> some View {
        HStack(spacing: 12) {
            AvatarCircle(name: member.user.name, avatarUrl: member.user.avatarUrl)

            VStack(alignment: .leading, spacing: 2) {
                Text(member.user.name)
                    .font(.system(.body, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateInk)
                Text(member.user.email)
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
            }

            Spacer()

            rolePill(member.role)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 10)
        .background(Color.roammateSurface)
        .contentShape(Rectangle())
        .onTapGesture {
            if isAdmin && member.userId != currentUserId {
                memberToChangeRole = member
            }
        }
        .contextMenu {
            if isAdmin && member.userId != currentUserId {
                Button {
                    memberToChangeRole = member
                } label: {
                    Label("Change role", systemImage: "person.badge.key")
                }
                Button(role: .destructive) {
                    memberToRemove = member
                } label: {
                    Label("Remove", systemImage: "person.badge.minus")
                }
            }
        }
    }

    private func pendingRow(_ member: TripMember) -> some View {
        HStack(spacing: 12) {
            AvatarCircle(name: member.user.name, avatarUrl: member.user.avatarUrl)

            VStack(alignment: .leading, spacing: 2) {
                Text(member.user.name)
                    .font(.system(.body, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateInk)
                Text(member.user.email)
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
            }

            Spacer()

            PillLabel(
                text: "Pending",
                background: Color.roammateAmberTint,
                foreground: Color.roammateAmber
            )

            rolePill(member.role)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 10)
        .background(Color.roammateSurface)
        .contextMenu {
            if isAdmin {
                Button(role: .destructive) {
                    Task { await store.removeMember(memberId: member.id) }
                } label: {
                    Label("Revoke", systemImage: "xmark.circle")
                }
            }
        }
    }

    private func rolePill(_ role: String) -> some View {
        let (bg, fg, label): (Color, Color, String) = {
            switch role {
            case "admin":
                return (Color.roammateIndigoTint, Color.roammateIndigo, "Admin")
            case "view_with_vote":
                return (Color.roammateVioletTint, Color.roammateViolet, "Can vote")
            default:
                return (Color.roammateSkyTint, Color.roammateSky, "View only")
            }
        }()
        return PillLabel(text: label, background: bg, foreground: fg)
    }

    private func changeRole(_ role: String) {
        guard let member = memberToChangeRole else { return }
        Task {
            let updated = try? await MemberService.updateRole(
                tripId: store.tripId, memberId: member.id, role: role
            )
            if let updated {
                if let idx = store.members.firstIndex(where: { $0.id == member.id }) {
                    store.members[idx] = updated
                }
            }
        }
    }
}
