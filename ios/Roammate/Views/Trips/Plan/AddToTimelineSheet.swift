import SwiftUI

struct AddToTimelineSheet: View {
    let selectedIdeaIds: [Int]
    let onComplete: () -> Void

    @EnvironmentObject var store: TripDetailStore
    @Environment(\.dismiss) private var dismiss

    @State private var selectedDayId: Int?
    @State private var isAdding = false

    private var sortedDays: [TripDay] {
        store.days.sorted { $0.dayNumber < $1.dayNumber }
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: RoammateSpacing.md) {
                Text("Add \(selectedIdeaIds.count) \(selectedIdeaIds.count == 1 ? "idea" : "ideas") to which day?")
                    .font(.system(.headline, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.roammateInk)
                    .padding(.top, RoammateSpacing.md)

                if sortedDays.isEmpty {
                    EmptyState(
                        icon: "calendar",
                        title: "No days",
                        subtitle: "Add days to your trip first."
                    )
                } else {
                    ScrollView {
                        LazyVStack(spacing: RoammateSpacing.sm) {
                            ForEach(sortedDays) { day in
                                dayRow(day)
                            }
                        }
                        .padding(.horizontal, RoammateSpacing.md)
                    }
                }

                Spacer()

                Button {
                    Task { await addToTimeline() }
                } label: {
                    if isAdding {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Text("Add to Timeline")
                    }
                }
                .buttonStyle(RoammatePrimaryButtonStyle(isLoading: isAdding))
                .disabled(selectedDayId == nil || isAdding)
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.bottom, RoammateSpacing.md)
            }
            .navigationTitle("Add to Day")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }

    private func dayRow(_ day: TripDay) -> some View {
        let isSelected = selectedDayId == day.id
        let fmt = DateFormatter()
        fmt.dateFormat = "MMM d, yyyy"

        return Button {
            HapticManager.selection()
            selectedDayId = day.id
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Day \(day.dayNumber)")
                        .font(.system(.body, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.roammateInk)
                    Text(fmt.string(from: day.date))
                        .font(.system(.caption, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.roammateMuted)
                }

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 22))
                        .foregroundStyle(Color.roammateIndigo)
                }
            }
            .padding(14)
            .background(
                RoundedRectangle(cornerRadius: RoammateRadius.small, style: .continuous)
                    .fill(isSelected ? Color.roammateIndigoTint : Color.roammateSurface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: RoammateRadius.small, style: .continuous)
                    .stroke(isSelected ? Color.roammateIndigo : Color.roammateBorder, lineWidth: isSelected ? 1.5 : 0.5)
            )
        }
        .buttonStyle(.plain)
    }

    private func addToTimeline() async {
        guard let dayId = selectedDayId,
              let day = sortedDays.first(where: { $0.id == dayId }) else { return }

        isAdding = true
        defer { isAdding = false }

        let selectedIdeas = store.ideas.filter { selectedIdeaIds.contains($0.id) }
        let key = EventService.isoDateString(from: day.date)
        let existing = (store.eventsByDay[key] ?? [])

        // Merge existing + new ideas, sort by start_time, then assign sort_order
        let allItems: [(startTime: TimeOfDay?, idea: IdeaBinItem?)] =
            existing.map { (startTime: $0.startTime, idea: nil) } +
            selectedIdeas.map { (startTime: $0.startTime, idea: $0) }
        let sorted = allItems.sorted {
            if let a = $0.startTime, let b = $1.startTime { return a < b }
            if $0.startTime != nil { return true }
            return false
        }

        // Compute sort_order for each new idea based on its position in the merged sorted list
        var ideaSortOrders: [Int: Int] = [:]
        for (idx, item) in sorted.enumerated() {
            if let idea = item.idea {
                ideaSortOrders[idea.id] = idx
            }
        }

        // Capture the trip id up front — the addTask closures are Sendable and
        // must not touch the main-actor-isolated `store`.
        let tripId = store.tripId
        await withTaskGroup(of: (Event?, Int).self) { group in
            for idea in selectedIdeas {
                let assignedOrder = ideaSortOrders[idea.id] ?? existing.count
                group.addTask {
                    let create = EventCreate(
                        tripId: tripId,
                        title: idea.title,
                        description: idea.description,
                        category: idea.category,
                        placeId: idea.placeId,
                        lat: idea.lat,
                        lng: idea.lng,
                        address: idea.address,
                        photoUrl: idea.photoUrl,
                        rating: idea.rating,
                        priceLevel: idea.priceLevel,
                        types: idea.types,
                        timeCategory: idea.timeCategory,
                        addedBy: idea.addedBy,
                        locationName: nil,
                        dayDate: EventService.isoDateString(from: day.date),
                        startTime: idea.startTime,
                        endTime: idea.endTime,
                        isLocked: false,
                        eventType: nil,
                        sortOrder: assignedOrder,
                        isSkipped: false,
                        sourceIdeaId: idea.id
                    )
                    do {
                        let event = try await EventService.createEvent(create)
                        return (event, idea.id)
                    } catch {
                        print("[AddToTimeline] Event creation failed for idea \(idea.id): \(error)")
                        return (nil, idea.id)
                    }
                }
            }

            for await (event, ideaId) in group {
                if let event {
                    store.eventsByDay[EventService.isoDateString(from: day.date), default: []].append(event)
                    // Delete source idea from backend so it doesn't reappear on reload
                    try? await IdeaService.deleteIdea(tripId: store.tripId, ideaId: ideaId)
                    store.ideas.removeAll { $0.id == ideaId }
                }
            }
        }

        // Sync local state with backend as a safety net
        await store.loadAll()

        HapticManager.success()
        onComplete()
        dismiss()
    }
}
