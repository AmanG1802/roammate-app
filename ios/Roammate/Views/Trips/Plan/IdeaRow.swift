import SwiftUI

struct IdeaRow: View {
    let idea: IdeaBinItem
    let isSelecting: Bool
    let isSelected: Bool
    let isExpanded: Bool
    let onToggle: () -> Void
    let onTap: () -> Void

    @EnvironmentObject var store: TripDetailStore

    @State private var editingTime = false
    @State private var editStart = Date()
    @State private var editEnd = Date()

    private var timeText: String {
        let fmt = DateFormatter()
        fmt.dateFormat = "h:mm a"
        let s = idea.startTime.map { fmt.string(from: $0) }
        let e = idea.endTime.map { fmt.string(from: $0) }
        if let s, let e { return "\(s) – \(e)" }
        if let s { return s }
        return "No time set"
    }

    var onDelete: (() -> Void)?

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .top, spacing: 0) {
                if isSelecting {
                    Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                        .font(.system(size: 22))
                        .foregroundStyle(isSelected ? Color.roammateIndigo : Color.roammateMuted)
                        .transition(.scale.combined(with: .opacity))
                        .padding(.trailing, 10)
                }

                CategoryColorBar(category: idea.category)
                    .padding(.trailing, 10)

                VStack(alignment: .leading, spacing: 4) {
                    HStack(alignment: .top) {
                        Text(idea.title)
                            .font(.system(.subheadline, design: .rounded, weight: .semibold))
                            .foregroundStyle(Color.roammateInk)
                            .lineLimit(isExpanded ? nil : 2)

                        Spacer(minLength: 8)

                        if !isSelecting {
                            Button {
                                HapticManager.light()
                                onDelete?()
                            } label: {
                                Image(systemName: "trash")
                                    .font(.system(size: 13, weight: .medium))
                                    .foregroundStyle(Color.roammateMuted)
                                    .frame(width: 28, height: 28)
                                    .background(
                                        RoundedRectangle(cornerRadius: 6, style: .continuous)
                                            .fill(Color.roammateBackground)
                                    )
                            }
                            .buttonStyle(.plain)
                        }
                    }

                    if let category = idea.category {
                        PillLabel(
                            text: category.capitalized,
                            background: Color.categoryTint(category),
                            foreground: Color.categoryColor(category)
                        )
                    }

                    HStack(spacing: 0) {
                        Button {
                            editStart = idea.startTime ?? Date()
                            editEnd = idea.endTime ?? Date()
                            editingTime = true
                        } label: {
                            HStack(spacing: 4) {
                                Image(systemName: "clock")
                                    .font(.system(size: 11))
                                Text(timeText)
                                    .font(.system(.caption, design: .rounded, weight: .medium))
                                Image(systemName: "pencil")
                                    .font(.system(size: 10))
                            }
                            .foregroundStyle(Color.roammateMuted)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(
                                Capsule().fill(Color.roammateBackground)
                            )
                        }
                        .buttonStyle(.plain)

                        Spacer()

                        if !isSelecting {
                            ThumbsVoteControl(
                                up: idea.up,
                                down: idea.down,
                                myVote: idea.myVote,
                                onVote: { value in
                                    Task { await store.voteIdea(ideaId: idea.id, value: value) }
                                }
                            )
                        }
                    }
                }
            }

            if isExpanded {
                expandedContent
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.small, style: .continuous)
                .fill(Color.roammateSurface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: RoammateRadius.small, style: .continuous)
                .stroke(
                    isSelected ? Color.roammateIndigo : Color.roammateBorder,
                    lineWidth: isSelected ? 1.5 : 0.5
                )
        )
        .contentShape(Rectangle())
        .onTapGesture {
            if isSelecting {
                HapticManager.selection()
                onToggle()
            } else {
                HapticManager.light()
                onTap()
            }
        }
        .sheet(isPresented: $editingTime) {
            timeEditSheet
        }
    }

    @ViewBuilder
    private var expandedContent: some View {
        VStack(alignment: .leading, spacing: 8) {
            Divider().padding(.vertical, 4)

            if let desc = idea.description, !desc.isEmpty {
                Text(desc)
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(Color.roammateInk.opacity(0.8))
            }

            if let address = idea.address, !address.isEmpty {
                HStack(spacing: 4) {
                    Image(systemName: "mappin")
                        .font(.system(size: 11))
                        .foregroundStyle(Color.roammateMuted)
                    Text(address)
                        .font(.system(.caption, design: .rounded))
                        .foregroundStyle(Color.roammateMuted)
                }
            }

            if let rating = idea.rating, rating > 0 {
                HStack(spacing: 4) {
                    Image(systemName: "star.fill")
                        .font(.system(size: 11))
                        .foregroundStyle(Color.roammateAmber)
                    Text(String(format: "%.1f", rating))
                        .font(.system(.caption, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.roammateMuted)
                }
            }

            if let addedBy = idea.addedBy, !addedBy.isEmpty {
                HStack(spacing: 4) {
                    Image(systemName: "person.fill")
                        .font(.system(size: 11))
                        .foregroundStyle(Color.roammateMuted)
                    Text("Added by \(addedBy)")
                        .font(.system(.caption, design: .rounded))
                        .foregroundStyle(Color.roammateMuted)
                }
            }

            if let url = idea.photoUrl, let imageURL = URL(string: url) {
                AsyncImage(url: imageURL) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFill()
                            .frame(maxWidth: .infinity)
                            .frame(height: 120)
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    default:
                        EmptyView()
                    }
                }
            }
        }
    }

    private var timeEditSheet: some View {
        NavigationStack {
            Form {
                DatePicker("Start Time", selection: $editStart, displayedComponents: .hourAndMinute)
                DatePicker("End Time", selection: $editEnd, displayedComponents: .hourAndMinute)
            }
            .navigationTitle("Edit Time")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { editingTime = false }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            await store.updateIdea(
                                ideaId: idea.id,
                                fields: IdeaUpdate(title: nil, startTime: editStart, endTime: editEnd, timeCategory: nil)
                            )
                        }
                        editingTime = false
                    }
                }
            }
        }
        .presentationDetents([.medium])
    }
}
