import SwiftUI

struct TimelineRow: View {
    let event: Event
    var isExpanded: Bool = false
    @EnvironmentObject var store: TripDetailStore
    @State private var expanded: Bool = false
    @State private var editingTime = false
    @State private var editStart = Date()
    @State private var editEnd = Date()

    private var startTimeText: String {
        guard let start = event.startTime else { return "TBD" }
        let fmt = DateFormatter()
        fmt.dateFormat = "h:mm a"
        return fmt.string(from: start)
    }

    private var endTimeText: String {
        guard let end = event.endTime else { return "" }
        let fmt = DateFormatter()
        fmt.dateFormat = "h:mm a"
        return fmt.string(from: end)
    }

    private var timeRangeText: String {
        let s = startTimeText
        let e = endTimeText
        if !e.isEmpty && e != s { return "\(s) – \(e)" }
        return s
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 0) {
                CategoryColorBar(category: event.category)
                    .padding(.trailing, 10)

                VStack(alignment: .leading, spacing: 6) {
                    HStack(alignment: .top) {
                        Text(event.title)
                            .font(.system(.subheadline, design: .rounded, weight: .semibold))
                            .foregroundStyle(Color.roammateInk)
                            .lineLimit(expanded ? nil : 2)

                        Spacer(minLength: 8)

                        Button {
                            HapticManager.light()
                            Task { await store.moveEventToBin(eventId: event.id) }
                        } label: {
                            Image(systemName: "tray.and.arrow.down")
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

                    if let category = event.category {
                        PillLabel(
                            text: category.capitalized,
                            background: Color.categoryTint(category),
                            foreground: Color.categoryColor(category)
                        )
                    }

                    HStack {
                        Button {
                            editStart = event.startTime ?? Date()
                            editEnd = event.endTime ?? Date()
                            editingTime = true
                        } label: {
                            HStack(spacing: 4) {
                                Image(systemName: "clock")
                                    .font(.system(size: 11))
                                Text(timeRangeText)
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

                        ThumbsVoteControl(
                            up: event.up,
                            down: event.down,
                            myVote: event.myVote,
                            onVote: { value in
                                Task { await store.voteEvent(eventId: event.id, value: value) }
                            }
                        )
                    }
                }
            }

            if expanded {
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
                .stroke(Color.roammateBorder, lineWidth: 0.5)
        )
        .contentShape(Rectangle())
        .onTapGesture {
            HapticManager.light()
            withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                expanded.toggle()
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

            if let desc = event.description, !desc.isEmpty {
                Text(desc)
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(Color.roammateInk.opacity(0.8))
            }

            if let address = event.address, !address.isEmpty {
                HStack(spacing: 4) {
                    Image(systemName: "mappin")
                        .font(.system(size: 11))
                        .foregroundStyle(Color.roammateMuted)
                    Text(address)
                        .font(.system(.caption, design: .rounded))
                        .foregroundStyle(Color.roammateMuted)
                }
            }

            if let rating = event.rating, rating > 0 {
                HStack(spacing: 4) {
                    Image(systemName: "star.fill")
                        .font(.system(size: 11))
                        .foregroundStyle(Color.roammateAmber)
                    Text(String(format: "%.1f", rating))
                        .font(.system(.caption, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.roammateMuted)
                }
            }

            if let url = event.photoUrl, let imageURL = URL(string: url) {
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
                            let update = EventUpdate(
                                title: nil,
                                dayDate: nil,
                                startTime: editStart,
                                endTime: editEnd,
                                sortOrder: nil,
                                timeCategory: nil,
                                isSkipped: nil
                            )
                            try? await EventService.updateEvent(id: event.id, update: update)
                            await store.loadAll()
                        }
                        editingTime = false
                    }
                }
            }
        }
        .presentationDetents([.medium])
    }
}

// MARK: - Category Color Bar (shared)

struct CategoryColorBar: View {
    let category: String?
    var body: some View {
        RoundedRectangle(cornerRadius: 2)
            .fill(Color.categoryColor(category))
            .frame(width: 4)
    }
}

// MARK: - Thumbs Up/Down Vote Control

struct ThumbsVoteControl: View {
    let up: Int
    let down: Int
    let myVote: Int
    let onVote: (Int) -> Void

    var body: some View {
        HStack(spacing: 6) {
            Button {
                HapticManager.light()
                onVote(myVote == 1 ? 0 : 1)
            } label: {
                HStack(spacing: 3) {
                    Image(systemName: myVote == 1 ? "hand.thumbsup.fill" : "hand.thumbsup")
                        .font(.system(size: 13, weight: .semibold))
                    Text("\(up)")
                        .font(.system(.caption2, design: .rounded, weight: .black))
                }
                .foregroundStyle(myVote == 1 ? Color.roammateEmerald : Color.roammateMuted)
                .padding(.horizontal, 8)
                .padding(.vertical, 5)
                .background(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .fill(myVote == 1 ? Color.roammateEmeraldTint : Color.roammateBackground)
                )
            }
            .buttonStyle(.plain)

            Button {
                HapticManager.light()
                onVote(myVote == -1 ? 0 : -1)
            } label: {
                HStack(spacing: 3) {
                    Image(systemName: myVote == -1 ? "hand.thumbsdown.fill" : "hand.thumbsdown")
                        .font(.system(size: 13, weight: .semibold))
                    Text("\(down)")
                        .font(.system(.caption2, design: .rounded, weight: .black))
                }
                .foregroundStyle(myVote == -1 ? Color.roammateDanger : Color.roammateMuted)
                .padding(.horizontal, 8)
                .padding(.vertical, 5)
                .background(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .fill(myVote == -1 ? Color(red: 254/255, green: 242/255, blue: 242/255) : Color.roammateBackground)
                )
            }
            .buttonStyle(.plain)
        }
    }
}
