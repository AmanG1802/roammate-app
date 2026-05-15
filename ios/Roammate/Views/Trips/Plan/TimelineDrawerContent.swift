import SwiftUI
import UniformTypeIdentifiers

struct TimelineDrawerContent: View {
    @EnvironmentObject var store: TripDetailStore
    @Binding var selectedDayIndex: Int
    @State private var dayToDelete: TripDay?
    @State private var draggingEventId: Int?
    @State private var reorderedEvents: [Event]?

    private var displayEvents: [Event] {
        if draggingEventId != nil, let reorderedEvents {
            return reorderedEvents
        }
        return currentEvents
    }

    private var sortedDays: [TripDay] {
        store.days.sorted { $0.dayNumber < $1.dayNumber }
    }

    private var eventCountsByDate: [String: Int] {
        store.eventsByDay.mapValues { $0.count }
    }

    private var currentDay: TripDay? {
        guard !sortedDays.isEmpty else { return nil }
        let idx = min(selectedDayIndex, sortedDays.count - 1)
        guard idx >= 0 else { return nil }
        return sortedDays[idx]
    }

    private var currentEvents: [Event] {
        guard let day = currentDay else { return [] }
        let key = EventService.isoDateString(from: day.date)
        return (store.eventsByDay[key] ?? []).sorted { $0.sortOrder < $1.sortOrder }
    }

    private var conflictIds: Set<Int> {
        var ids = Set<Int>()
        var maxEnd: Date?
        for ev in displayEvents {
            if ev.isSkipped { continue }
            if let start = ev.startTime, let prevEnd = maxEnd, start < prevEnd {
                ids.insert(ev.id)
            }
            if let end = ev.endTime, end > (maxEnd ?? .distantPast) {
                maxEnd = end
            }
        }
        return ids
    }

    var body: some View {
        VStack(spacing: 0) {
            DayTabsBar(
                days: sortedDays,
                selectedIndex: $selectedDayIndex,
                eventCounts: eventCountsByDate,
                onAddDay: {
                    Task { await addNextDay() }
                }
            )

            if sortedDays.isEmpty {
                EmptyState(
                    icon: "calendar.badge.plus",
                    title: "No days yet",
                    subtitle: "Tap 'Add Day' to start building your timeline."
                )
                .padding(.top, RoammateSpacing.xl)
            } else if let day = currentDay {
                daySectionHeader(day: day, count: currentEvents.count)

                if currentEvents.isEmpty {
                    EmptyState(
                        icon: "calendar.badge.plus",
                        title: "No events yet",
                        subtitle: "Add ideas from the Idea Bin to build your timeline."
                    )
                    .padding(.top, RoammateSpacing.xl)
                } else {
                    let events = displayEvents
                    LazyVStack(spacing: 0) {
                        ForEach(events) { event in
                            VStack(spacing: 0) {
                                TimelineRow(event: event, isExpanded: false, isConflict: conflictIds.contains(event.id))

                                if let index = events.firstIndex(where: { $0.id == event.id }),
                                   index < events.count - 1 {
                                    hourDots(from: event, to: events[index + 1])
                                }
                            }
                            .padding(.horizontal, RoammateSpacing.md)
                            .padding(.vertical, 4)
                            .onDrag {
                                draggingEventId = event.id
                                return NSItemProvider(object: String(event.id) as NSString)
                            }
                            .onDrop(of: [UTType.text], delegate: TimelineDropDelegate(
                                targetEvent: event,
                                events: events,
                                draggingEventId: $draggingEventId,
                                reorderedEvents: $reorderedEvents,
                                onDrop: { reordered in
                                    Task { await commitReorder(reordered) }
                                }
                            ))
                            .transition(.asymmetric(
                                insertion: .opacity,
                                removal: .move(edge: .leading).combined(with: .opacity)
                            ))
                        }
                    }
                    .animation(.spring(response: 0.35, dampingFraction: 0.8), value: events.map(\.id))
                }
            }
        }
        .onChange(of: selectedDayIndex) { _, _ in
            reorderedEvents = nil
            draggingEventId = nil
        }
        .onChange(of: store.eventsByDay) { _, _ in
            if draggingEventId == nil {
                reorderedEvents = nil
            }
        }
        .confirmationDialog(
            "Delete Day \(dayToDelete?.dayNumber ?? 0)?",
            isPresented: .init(
                get: { dayToDelete != nil },
                set: { if !$0 { dayToDelete = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("Send items to Idea Bin") {
                if let day = dayToDelete {
                    Task {
                        await store.deleteDay(id: day.id, itemsAction: "bin")
                        clampSelectedDay()
                    }
                }
            }
            Button("Delete permanently", role: .destructive) {
                if let day = dayToDelete {
                    Task {
                        await store.deleteDay(id: day.id, itemsAction: "delete")
                        clampSelectedDay()
                    }
                }
            }
            Button("Cancel", role: .cancel) {}
        }
    }

    // MARK: - Day Section Header with Delete

    private func daySectionHeader(day: TripDay, count: Int) -> some View {
        let fmt = DateFormatter()
        fmt.dateFormat = "MMM d"
        let dateStr = fmt.string(from: day.date)

        return HStack {
            Text("\(dateStr) — \(count) \(count == 1 ? "stop" : "stops")")
                .font(.system(.subheadline, design: .rounded, weight: .medium))
                .foregroundStyle(Color.roammateMuted)

            Spacer()

            Button {
                let key = EventService.isoDateString(from: day.date)
                let hasEvents = !(store.eventsByDay[key] ?? []).isEmpty
                if hasEvents {
                    HapticManager.warning()
                    dayToDelete = day
                } else {
                    HapticManager.light()
                    Task {
                        await store.deleteDay(id: day.id, itemsAction: "delete")
                        clampSelectedDay()
                    }
                }
            } label: {
                Image(systemName: "trash")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(Color.roammateMuted)
                    .frame(width: 32, height: 32)
                    .background(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .fill(Color.roammateBackground)
                    )
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, RoammateSpacing.sm)
        .background(Color.roammateSurface.opacity(0.95))
    }

    // MARK: - Hour Dots

    private func hourDots(from: Event, to: Event) -> some View {
        let hours: Int = {
            guard let end = from.endTime ?? from.startTime,
                  let start = to.startTime else { return 1 }
            let diff = start.timeIntervalSince(end)
            return max(1, min(8, Int(diff / 3600)))
        }()

        return VStack(spacing: 6) {
            ForEach(0..<hours, id: \.self) { _ in
                Circle()
                    .fill(Color.roammateIndigo.opacity(0.25))
                    .frame(width: 6, height: 6)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 4)
    }

    private func clampSelectedDay() {
        let count = store.days.count
        if selectedDayIndex >= count {
            withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                selectedDayIndex = max(0, count - 1)
            }
        }
    }

    private func commitReorder(_ events: [Event]) async {
        guard let day = currentDay else { return }
        let key = EventService.isoDateString(from: day.date)

        var updated = events.enumerated().map { idx, event in
            Event(
                id: event.id, tripId: event.tripId, title: event.title,
                description: event.description, category: event.category,
                placeId: event.placeId, lat: event.lat, lng: event.lng,
                address: event.address, photoUrl: event.photoUrl, rating: event.rating,
                priceLevel: event.priceLevel, types: event.types,
                timeCategory: event.timeCategory, addedBy: event.addedBy,
                locationName: event.locationName, dayDate: event.dayDate,
                startTime: event.startTime, endTime: event.endTime,
                isLocked: event.isLocked, eventType: event.eventType,
                sortOrder: idx, isSkipped: event.isSkipped,
                up: event.up, down: event.down, myVote: event.myVote
            )
        }

        // Auto-resolve conflicts: if any overlaps exist, sort by startTime
        if hasConflicts(updated) {
            updated.sort { ($0.startTime ?? .distantFuture) < ($1.startTime ?? .distantFuture) }
            updated = updated.enumerated().map { idx, event in
                Event(
                    id: event.id, tripId: event.tripId, title: event.title,
                    description: event.description, category: event.category,
                    placeId: event.placeId, lat: event.lat, lng: event.lng,
                    address: event.address, photoUrl: event.photoUrl, rating: event.rating,
                    priceLevel: event.priceLevel, types: event.types,
                    timeCategory: event.timeCategory, addedBy: event.addedBy,
                    locationName: event.locationName, dayDate: event.dayDate,
                    startTime: event.startTime, endTime: event.endTime,
                    isLocked: event.isLocked, eventType: event.eventType,
                    sortOrder: idx, isSkipped: event.isSkipped,
                    up: event.up, down: event.down, myVote: event.myVote
                )
            }
            HapticManager.success()
        } else {
            HapticManager.medium()
        }

        withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
            store.eventsByDay[key] = updated
            reorderedEvents = nil
        }

        await store.batchUpdateSortOrders(events: updated)
    }

    private func hasConflicts(_ events: [Event]) -> Bool {
        var maxEnd: Date?
        for ev in events {
            if ev.isSkipped { continue }
            if let start = ev.startTime, let prevEnd = maxEnd, start < prevEnd {
                return true
            }
            if let end = ev.endTime, end > (maxEnd ?? .distantPast) {
                maxEnd = end
            }
        }
        return false
    }

    private func addNextDay() async {
        let cal = Calendar.current
        let nextDate: Date

        if let lastDay = sortedDays.last {
            let candidate = cal.date(byAdding: .day, value: 1, to: lastDay.date) ?? Date()
            // If trip start is after the candidate (user moved dates forward), start from trip start + existing count
            if let tripStart = store.trip?.startDate,
               cal.startOfDay(for: tripStart) > cal.startOfDay(for: candidate) {
                nextDate = cal.date(byAdding: .day, value: sortedDays.count, to: tripStart) ?? candidate
            } else {
                nextDate = candidate
            }
        } else if let tripStart = store.trip?.startDate {
            nextDate = tripStart
        } else {
            nextDate = Date()
        }

        await store.addDay(date: nextDate)
        let updatedDays = store.days.sorted { $0.dayNumber < $1.dayNumber }
        withAnimation {
            selectedDayIndex = max(0, updatedDays.count - 1)
        }
    }
}

// MARK: - Drop Delegate

struct TimelineDropDelegate: DropDelegate {
    let targetEvent: Event
    let events: [Event]
    @Binding var draggingEventId: Int?
    @Binding var reorderedEvents: [Event]?
    let onDrop: ([Event]) -> Void

    func dropEntered(info: DropInfo) {
        guard let dragId = draggingEventId,
              dragId != targetEvent.id else { return }

        let current = reorderedEvents ?? events
        guard let fromIndex = current.firstIndex(where: { $0.id == dragId }),
              let toIndex = current.firstIndex(where: { $0.id == targetEvent.id }),
              fromIndex != toIndex else { return }

        withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
            var updated = current
            updated.move(fromOffsets: IndexSet(integer: fromIndex), toOffset: toIndex > fromIndex ? toIndex + 1 : toIndex)
            reorderedEvents = updated
        }
    }

    func dropUpdated(info: DropInfo) -> DropProposal? {
        DropProposal(operation: .move)
    }

    func performDrop(info: DropInfo) -> Bool {
        let reordered = reorderedEvents ?? events
        onDrop(reordered)
        draggingEventId = nil
        reorderedEvents = nil
        return true
    }

    func dropExited(info: DropInfo) {}

    func validateDrop(info: DropInfo) -> Bool { true }
}
