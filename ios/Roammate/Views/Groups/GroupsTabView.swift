import SwiftUI

struct GroupsTabView: View {
    @EnvironmentObject var groupStore: GroupStore
    @State private var showCreate = false
    @State private var newGroupName = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(spacing: RoammateSpacing.sm) {
                    if groupStore.groups.isEmpty && !groupStore.isLoading {
                        EmptyState(
                            icon: "person.3",
                            title: "No groups yet",
                            subtitle: "Create a group to organise trips with the same crew."
                        )
                        .padding(.top, RoammateSpacing.xxl)
                    } else {
                        ForEach(groupStore.groups) { group in
                            groupRow(group)
                        }
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.top, RoammateSpacing.md)
                .padding(.bottom, RoammateLayout.contentBottomPadding)
            }
            .background(Color.roammateBackground.ignoresSafeArea())
            .navigationTitle("Groups")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        HapticManager.light()
                        newGroupName = ""
                        showCreate = true
                    } label: {
                        Image(systemName: "plus")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(Color.roammateIndigo)
                    }
                }
            }
            .refreshable { await groupStore.load() }
            .task {
                if groupStore.groups.isEmpty { await groupStore.load() }
            }
            .alert("New group", isPresented: $showCreate) {
                TextField("Group name", text: $newGroupName)
                Button("Cancel", role: .cancel) {}
                Button("Create") {
                    let name = newGroupName.trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !name.isEmpty else { return }
                    Task {
                        _ = await groupStore.create(name: name)
                        HapticManager.success()
                    }
                }
            } message: {
                Text("Give your group a short, recognisable name.")
            }
        }
    }

    private func groupRow(_ group: TravelGroup) -> some View {
        HStack(spacing: RoammateSpacing.md) {
            ZStack {
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(Color.roammateIndigoTint)
                Image(systemName: "person.3.fill")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Color.roammateIndigo)
            }
            .frame(width: 44, height: 44)

            VStack(alignment: .leading, spacing: 2) {
                Text(group.name)
                    .font(.system(.body, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateInk)
                Text("\(group.memberCount) members · \(group.tripCount) trips")
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(Color.roammateMuted)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 12)
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                .fill(Color.roammateSurface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                .stroke(Color.roammateBorder, lineWidth: 1)
        )
    }
}
