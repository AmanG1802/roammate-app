import SwiftUI

@MainActor
final class TripDetailStore: ObservableObject {
    let tripId: Int

    @Published var trip: Trip?
    @Published var days: [TripDay] = []
    @Published var eventsByDay: [String: [Event]] = [:]
    @Published var ideas: [IdeaBinItem] = []
    @Published var members: [TripMember] = []
    @Published var isLoading = false
    @Published var error: String?

    // Route state
    @Published var routeOverlays: [RouteOverlay] = []
    @Published var routeResponse: RouteResponseDTO?
    @Published var isRouteLoading = false
    @Published var isRouteStale = false
    @Published var routeFingerprint: String?

    init(tripId: Int) {
        self.tripId = tripId
        loadFromCache()
    }

    // MARK: - Cache

    private var daysCacheKey: String { "trip_\(tripId)_days" }
    private var ideasCacheKey: String { "trip_\(tripId)_ideas" }
    private var membersCacheKey: String { "trip_\(tripId)_members" }

    private func loadFromCache() {
        days = DiskCache.shared.load([TripDay].self, key: daysCacheKey) ?? []
        ideas = DiskCache.shared.load([IdeaBinItem].self, key: ideasCacheKey) ?? []
        members = DiskCache.shared.load([TripMember].self, key: membersCacheKey) ?? []
    }

    // MARK: - Load

    func loadAll() async {
        isLoading = true
        error = nil
        defer { isLoading = false }

        async let tripTask = TripService.getTrip(id: tripId)
        async let daysTask = TripDayService.getDays(tripId: tripId)
        async let ideasTask = IdeaService.getIdeas(tripId: tripId)
        async let membersTask = MemberService.getMembers(tripId: tripId)
        async let eventsTask = EventService.getEvents(tripId: tripId, dayDate: nil)

        do {
            let (trip, days, ideas, members, events) =
                try await (tripTask, daysTask, ideasTask, membersTask, eventsTask)

            self.trip = trip
            self.days = days
            self.ideas = ideas
            self.members = members
            self.eventsByDay = Dictionary(grouping: events, by: { $0.dayDate ?? "" })

            DiskCache.shared.store(days, key: daysCacheKey)
            DiskCache.shared.store(ideas, key: ideasCacheKey)
            DiskCache.shared.store(members, key: membersCacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func loadDay(_ date: Date) async {
        let dayStr = EventService.isoDateString(from: date)
        do {
            let events = try await EventService.getEvents(tripId: tripId, dayDate: dayStr)
            eventsByDay[dayStr] = events
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: - Days

    func addDay(date: Date) async {
        do {
            let day = try await TripDayService.addDay(tripId: tripId, date: date)
            days.append(day)
            days.sort { $0.dayNumber < $1.dayNumber }
            DiskCache.shared.store(days, key: daysCacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func deleteDay(id: Int, itemsAction: String = "bin") async {
        do {
            try await TripDayService.deleteDay(tripId: tripId, dayId: id, itemsAction: itemsAction)
            days.removeAll { $0.id == id }
            DiskCache.shared.store(days, key: daysCacheKey)
        } catch let e as APIError {
            error = e.errorDescription
            return
        } catch {
            self.error = error.localizedDescription
            return
        }
        await loadAll()
        // Always reload ideas: for "bin" the backend created new ideas from the
        // deleted events; for "delete" this is a no-op but the extra @Published
        // write ensures SwiftUI flushes the updated days to the UI.
        await reloadIdeas()
    }

    // MARK: - Events

    func reorderEvent(eventId: Int, newSortOrder: Int) async {
        let update = EventUpdate(
            title: nil, dayDate: nil, startTime: nil, endTime: nil,
            sortOrder: newSortOrder, timeCategory: nil, isSkipped: nil
        )
        do {
            let updated = try await EventService.updateEvent(id: eventId, update: update)
            for (date, list) in eventsByDay {
                if let idx = list.firstIndex(where: { $0.id == eventId }) {
                    eventsByDay[date]?[idx] = updated
                }
            }
        } catch {}
    }

    /// Persist sort orders to the backend without updating local state per-call.
    /// Local state should already be set before calling this.
    func batchUpdateSortOrders(events: [Event]) async {
        for event in events {
            let update = EventUpdate(
                title: nil, dayDate: nil, startTime: nil, endTime: nil,
                sortOrder: event.sortOrder, timeCategory: nil, isSkipped: nil
            )
            _ = try? await EventService.updateEvent(id: event.id, update: update)
        }
    }

    /// Toggle an event's skipped flag (Concierge skips a stop; the Plan timeline
    /// lets the user restore it). Mirrors the web `toggleEventSkip`.
    func setEventSkipped(eventId: Int, isSkipped: Bool) async {
        let update = EventUpdate(
            title: nil, dayDate: nil, startTime: nil, endTime: nil,
            sortOrder: nil, timeCategory: nil, isSkipped: isSkipped
        )
        do {
            let updated = try await EventService.updateEvent(id: eventId, update: update)
            for (date, list) in eventsByDay {
                if let idx = list.firstIndex(where: { $0.id == eventId }) {
                    eventsByDay[date]?[idx] = updated
                }
            }
        } catch {}
    }

    func moveEventToBin(eventId: Int) async {
        do {
            let idea = try await EventService.moveToBin(eventId: eventId)
            ideas.insert(idea, at: 0)
            for (date, list) in eventsByDay {
                eventsByDay[date] = list.filter { $0.id != eventId }
            }
            DiskCache.shared.store(ideas, key: ideasCacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func deleteEvent(_ event: Event) async {
        do {
            try await EventService.deleteEvent(id: event.id)
            for (date, list) in eventsByDay {
                eventsByDay[date] = list.filter { $0.id != event.id }
            }
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: - Votes

    func voteEvent(eventId: Int, value: Int) async {
        do {
            let tally = try await VoteService.voteEvent(eventId: eventId, value: value)
            applyEventTally(eventId: eventId, tally: tally)
        } catch {}
    }

    func voteIdea(ideaId: Int, value: Int) async {
        do {
            let tally = try await VoteService.voteIdea(ideaId: ideaId, value: value)
            applyIdeaTally(ideaId: ideaId, tally: tally)
        } catch {}
    }

    private func applyEventTally(eventId: Int, tally: VoteTally) {
        for (date, list) in eventsByDay {
            if let idx = list.firstIndex(where: { $0.id == eventId }) {
                let e = list[idx]
                eventsByDay[date]?[idx] = Event(
                    id: e.id, tripId: e.tripId, title: e.title, description: e.description,
                    category: e.category, placeId: e.placeId, lat: e.lat, lng: e.lng,
                    address: e.address, photoUrl: e.photoUrl, rating: e.rating,
                    priceLevel: e.priceLevel, types: e.types, timeCategory: e.timeCategory,
                    addedBy: e.addedBy, locationName: e.locationName, dayDate: e.dayDate,
                    startTime: e.startTime, endTime: e.endTime, isLocked: e.isLocked,
                    eventType: e.eventType, sortOrder: e.sortOrder, isSkipped: e.isSkipped,
                    up: tally.up, down: tally.down, myVote: tally.myVote
                )
                return
            }
        }
    }

    private func applyIdeaTally(ideaId: Int, tally: VoteTally) {
        guard let idx = ideas.firstIndex(where: { $0.id == ideaId }) else { return }
        let i = ideas[idx]
        ideas[idx] = IdeaBinItem(
            id: i.id, tripId: i.tripId, title: i.title, description: i.description,
            category: i.category, placeId: i.placeId, lat: i.lat, lng: i.lng,
            address: i.address, photoUrl: i.photoUrl, rating: i.rating,
            priceLevel: i.priceLevel, types: i.types, timeCategory: i.timeCategory,
            addedBy: i.addedBy, startTime: i.startTime, endTime: i.endTime,
            up: tally.up, down: tally.down, myVote: tally.myVote
        )
    }

    // MARK: - Ideas

    func reloadIdeas() async {
        do {
            let freshIdeas = try await IdeaService.getIdeas(tripId: tripId)
            ideas = freshIdeas
            DiskCache.shared.store(ideas, key: ideasCacheKey)
        } catch {}
    }

    func ingest(text: String, sourceUrl: String? = nil) async {
        do {
            let newItems = try await IdeaService.ingest(tripId: tripId, text: text, sourceUrl: sourceUrl)
            ideas.insert(contentsOf: newItems, at: 0)
            DiskCache.shared.store(ideas, key: ideasCacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func deleteIdea(ideaId: Int) async {
        do {
            try await IdeaService.deleteIdea(tripId: tripId, ideaId: ideaId)
            ideas.removeAll { $0.id == ideaId }
            DiskCache.shared.store(ideas, key: ideasCacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func updateIdea(ideaId: Int, fields: IdeaUpdate) async {
        do {
            let updated = try await IdeaService.updateIdea(tripId: tripId, ideaId: ideaId, fields: fields)
            if let idx = ideas.firstIndex(where: { $0.id == ideaId }) {
                ideas[idx] = updated
            }
            DiskCache.shared.store(ideas, key: ideasCacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: - Route

    func loadStoredRoute(dayDate: String) async {
        do {
            let stored = try await RouteService.fetchStoredRoute(tripId: tripId, dayDate: dayDate)
            guard let stored else {
                routeOverlays = []
                routeResponse = nil
                isRouteStale = false
                return
            }

            routeResponse = stored
            isRouteStale = stored.isStale
            routeFingerprint = stored.waypointFingerprint

            let allEvents = eventsByDay.values.flatMap { $0 }
            routeOverlays = RouteService.decodeStoredRoute(response: stored, events: allEvents)
        } catch {
            routeOverlays = []
            routeResponse = nil
        }
    }

    func refreshRoute(dayDate: String) async {
        let events = eventsByDay[dayDate] ?? []
        isRouteLoading = true
        defer { isRouteLoading = false }

        let (overlays, saveRequest) = await RouteService.computeRoute(events: events)
        routeOverlays = overlays

        guard let saveRequest, !saveRequest.legs.isEmpty else { return }

        do {
            let saved = try await RouteService.saveRoute(tripId: tripId, request: saveRequest)
            routeResponse = saved
            isRouteStale = false
            routeFingerprint = saved.waypointFingerprint
        } catch {
            // Route was computed locally but save failed; still show overlays
        }
    }

    func checkRouteStaleness(dayDate: String) {
        let events = eventsByDay[dayDate] ?? []
        let currentFp = RouteService.computeFingerprint(events: events)
        if let stored = routeFingerprint, stored != currentFp {
            isRouteStale = true
        }
    }

    func clearRoute() {
        routeOverlays = []
        routeResponse = nil
        isRouteStale = false
        routeFingerprint = nil
    }

    // MARK: - Members

    func invite(email: String, role: String) async {
        do {
            let member = try await MemberService.invite(tripId: tripId, email: email, role: role)
            members.append(member)
            DiskCache.shared.store(members, key: membersCacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func removeMember(memberId: Int) async {
        do {
            try await MemberService.removeMember(tripId: tripId, memberId: memberId)
            members.removeAll { $0.id == memberId }
            DiskCache.shared.store(members, key: membersCacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }
}
