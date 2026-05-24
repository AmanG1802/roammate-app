import SwiftUI

struct IdeaBinView: View {
    @EnvironmentObject var store: TripDetailStore

    @State private var isSelecting = false
    @State private var selected: Set<Int> = []
    @State private var showAddSheet = false
    @State private var expandedId: Int?
    @State private var deletingId: Int?

    var body: some View {
        VStack(spacing: 0) {
            header
                .tutorialAnchor("idea-bin-list")

            if store.ideas.isEmpty {
                Spacer()
                EmptyState(
                    icon: "lightbulb",
                    title: "No ideas yet",
                    subtitle: "Brainstorm or paste a link to add ideas."
                )
                Spacer()
            } else {
                ScrollView {
                    LazyVStack(spacing: RoammateSpacing.sm) {
                        ForEach(store.ideas) { idea in
                            if deletingId != idea.id {
                                IdeaRow(
                                    idea: idea,
                                    isSelecting: isSelecting,
                                    isSelected: selected.contains(idea.id),
                                    isExpanded: expandedId == idea.id,
                                    onToggle: { toggleSelection(idea.id) },
                                    onTap: {
                                        withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                                            expandedId = expandedId == idea.id ? nil : idea.id
                                        }
                                    },
                                    onDelete: {
                                        withAnimation(.spring(response: 0.15, dampingFraction: 0.9)) {
                                            deletingId = idea.id
                                        }
                                        Task {
                                            try? await Task.sleep(nanoseconds: 150_000_000)
                                            await store.deleteIdea(ideaId: idea.id)
                                            deletingId = nil
                                        }
                                    }
                                )
                                .transition(.asymmetric(
                                    insertion: .opacity,
                                    removal: .move(edge: .leading).combined(with: .opacity)
                                ))
                            }
                        }
                    }
                    .animation(.spring(response: 0.15, dampingFraction: 0.9), value: store.ideas.map(\.id))
                    .padding(.horizontal, RoammateSpacing.md)
                    .padding(.vertical, RoammateSpacing.sm)
                    .padding(.bottom, isSelecting ? 80 : RoammateSpacing.xl)
                }
            }

            if isSelecting && !selected.isEmpty {
                selectionToolbar
            }
        }
        .background(Color.roammateBackground)
        .sheet(isPresented: $showAddSheet) {
            AddToTimelineSheet(
                selectedIdeaIds: Array(selected),
                onComplete: {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                        selected.removeAll()
                        isSelecting = false
                    }
                }
            )
            .environmentObject(store)
            .presentationDetents([.medium])
        }
    }

    private var header: some View {
        HStack {
            Text("\(store.ideas.count) ideas")
                .font(.system(.headline, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateInk)

            Spacer()

            Button {
                HapticManager.selection()
                withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                    isSelecting.toggle()
                    if !isSelecting {
                        selected.removeAll()
                        expandedId = nil
                    }
                }
            } label: {
                Text(isSelecting ? "Cancel" : "Select")
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateIndigo)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 12)
    }

    private var selectionToolbar: some View {
        HStack(spacing: RoammateSpacing.md) {
            Button {
                showAddSheet = true
            } label: {
                Text("Add \(selected.count) to Timeline")
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
            }
            .buttonStyle(RoammatePrimaryButtonStyle())

            Button {
                withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                    selected.removeAll()
                    isSelecting = false
                }
            } label: {
                Text("Cancel")
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateMuted)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 12)
        .background(Color.roammateSurface.shadow(.drop(radius: 8, y: -4)))
        .transition(.move(edge: .bottom).combined(with: .opacity))
    }

    private func toggleSelection(_ id: Int) {
        if selected.contains(id) {
            selected.remove(id)
        } else {
            selected.insert(id)
        }
    }
}
