import SwiftUI

struct TimelineDrawerContent: View {
    @EnvironmentObject var store: TripDetailStore
    @Binding var selectedDayIndex: Int
    @State private var dayToDelete: TripDay?

    private var sortedDays: [TripDay] {
        store.days.sorted { $0.dayNumber < $1.dayNumber }
    }

    private var eventCountsByDate: [Date: Int] {
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
        let key = TripDetailStore.normalizedDay(day.date)
        return (store.eventsByDay[key] ?? []).sorted { $0.sortOrder < $1.sortOrder }
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
                    List {
                        ForEach(currentEvents) { event in
                            VStack(spacing: 0) {
                                TimelineRow(event: event, isExpanded: false)

                                if let index = currentEvents.firstIndex(where: { $0.id == event.id }),
                                   index < currentEvents.count - 1 {
                                    hourDots(from: event, to: currentEvents[index + 1])
                                }
                            }
                            .listRowInsets(EdgeInsets(top: 4, leading: RoammateSpacing.md, bottom: 4, trailing: RoammateSpacing.md))
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                        }
                        .onMove { source, destination in
                            Task { await handleReorder(source: source, destination: destination) }
                        }
                    }
                    .listStyle(.plain)
                    .environment(\.editMode, .constant(.active))
                    .scrollContentBackground(.hidden)
                }
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
                let key = TripDetailStore.normalizedDay(day.date)
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
                    .fill(Color.roammateBorder)
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

    private func handleReorder(source: IndexSet, destination: Int) async {
        guard let day = currentDay else { return }
        var events = currentEvents
        events.move(fromOffsets: source, toOffset: destination)

        var updated: [Event] = []
        for (idx, event) in events.enumerated() {
            let newEvent = Event(
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
            updated.append(newEvent)
        }
        store.eventsByDay[TripDetailStore.normalizedDay(day.date)] = updated

        for event in updated {
            await store.reorderEvent(eventId: event.id, newSortOrder: event.sortOrder)
        }
    }

    private func addNextDay() async {
        let nextDate: Date
        if let lastDay = sortedDays.last {
            nextDate = Calendar.current.date(byAdding: .day, value: 1, to: lastDay.date) ?? Date()
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
