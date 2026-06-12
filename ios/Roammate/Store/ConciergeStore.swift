import SwiftUI
import CoreLocation

/// Drives the chat-first Concierge surface: the message stream, the rich-card
/// state machine (action confirmations, place carousels, day summaries, ripple
/// results), and which full-screen destination (`.map` / `.timeline`) is shown.
///
/// Mirrors the web `ConciergeChatDrawer` + `ConciergeActionBar` behaviour, but
/// native. Mutations that touch the shared itinerary call back through
/// `onEventsChanged` so the host can reload `TripDetailStore`.
@MainActor
final class ConciergeStore: ObservableObject {
    let trip: Trip
    var tripId: Int { trip.id }

    @Published var messages: [ChatMessage] = []
    @Published var isThinking = false
    @Published var error: String?
    /// 3.1: the thread is shared by the whole trip. `canWrite` (Plus + admin)
    /// gates the composer; non-writers get a read-only/upsell state.
    @Published var canWrite = true
    private var threadLoaded = false

    /// Which full-screen destination is layered over the chat (drives the
    /// `.fullScreenCover`). `nil` = chat is showing.
    @Published var detail: ConciergeDetail?
    /// Result pins to drop on the map after a "View on map" hand-off.
    @Published var nearbyPins: [PlaceCard] = []

    /// Set by the host to reload the shared itinerary after a mutation.
    var onEventsChanged: (() async -> Void)?
    /// Fallback search origin (current/next event coordinate) used when device
    /// location is unavailable. Set by the chat view from `TripDetailStore`.
    var fallbackCoordinate: CLLocationCoordinate2D?

    private let location = ConciergeLocationProvider()

    init(trip: Trip) {
        self.trip = trip
        messages = [
            ChatMessage(
                role: .assistant,
                text: "Hey — I'm your on-trip Concierge. Ask me anything, or tap a quick action below to handle running late, skip a stop, or find something nearby."
            )
        ]
    }

    // MARK: - Shared trip-wide thread (3.1)

    /// Hydrate the shared conversation when the surface appears so every member
    /// sees the same thread (with author labels), and learn whether this member
    /// may post. Runs once per presentation.
    func loadThread() async {
        guard !threadLoaded else { return }
        threadLoaded = true
        guard let res = try? await ConciergeService.messages(tripId: tripId) else { return }
        canWrite = res.canWrite
        guard !res.messages.isEmpty else { return }
        messages = res.messages.map { m in
            let isCard = m.messageType == "action_card"
            let role: ChatMessage.Role = ChatMessage.Role(rawValue: m.role) ?? .assistant
            return ChatMessage(
                role: role,
                text: m.content,
                // Resolved history cards render confirmed, not as live prompts.
                card: .text,
                status: isCard ? .confirmed : nil,
                authorName: m.authorName
            )
        }
    }

    // MARK: - Free-text chat

    func send(_ text: String) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !isThinking else { return }

        messages.append(ChatMessage(role: .user, text: trimmed))
        isThinking = true
        error = nil

        do {
            let res = try await ConciergeService.chat(tripId: tripId, message: trimmed)

            if res.intent == .findNearby {
                if !res.userMessage.isEmpty {
                    messages.append(ChatMessage(role: .assistant, text: res.userMessage))
                }
                isThinking = false
                let query = res.params["query"]?.stringValue ?? trimmed
                await findNearby(query: query, category: res.params["category"]?.stringValue)
                return
            }

            if res.requiresConfirmation {
                messages.append(ChatMessage(
                    role: .assistant,
                    text: res.userMessage,
                    card: .actionCard,
                    status: .pending,
                    intent: res.intent,
                    params: res.params,
                    preview: res.preview
                ))
            } else {
                let card: ConciergeCard = res.messageType == "error" ? .error(retryQuery: trimmed) : .text
                messages.append(ChatMessage(role: .assistant, text: res.userMessage, card: card))
            }
        } catch let e as APIError {
            handle(e, retryQuery: trimmed)
        } catch {
            messages.append(ChatMessage(
                role: .assistant,
                text: "Something went wrong. Try again in a moment.",
                card: .error(retryQuery: trimmed)
            ))
        }
        isThinking = false
    }

    func retry(_ query: String) {
        Task { await send(query) }
    }

    // MARK: - Action confirmation

    func confirm(_ message: ChatMessage) async {
        guard let intent = message.intent else { return }
        setStatus(message.id, .confirmed)
        isThinking = true
        defer { isThinking = false }

        do {
            let exec = try await ConciergeService.execute(
                tripId: tripId,
                intent: intent.rawValue,
                params: message.params
            )
            if exec.success {
                messages.append(ChatMessage(role: .assistant, text: exec.message))
                await onEventsChanged?()
                // 3.8: only the most recent executed action is undoable.
                for i in messages.indices { messages[i].canUndo = false }
                if let idx = messages.firstIndex(where: { $0.id == message.id }) {
                    messages[idx].canUndo = true
                }
            } else {
                messages.append(ChatMessage(
                    role: .assistant,
                    text: exec.message.isEmpty ? "I couldn't complete that." : exec.message,
                    card: .error(retryQuery: nil)
                ))
            }
        } catch let e as APIError {
            setStatus(message.id, .pending)
            handle(e, retryQuery: nil)
        } catch {
            setStatus(message.id, .pending)
            messages.append(ChatMessage(role: .assistant, text: "That didn't go through. Try again.", card: .error(retryQuery: nil)))
        }
    }

    func cancel(_ message: ChatMessage) {
        setStatus(message.id, .cancelled)
    }

    // MARK: - Undo last action (3.8)

    func undo(_ message: ChatMessage) async {
        isThinking = true
        defer { isThinking = false }
        do {
            let res = try await ConciergeService.undo(tripId: tripId)
            if let idx = messages.firstIndex(where: { $0.id == message.id }) {
                messages[idx].canUndo = false
                messages[idx].status = .cancelled
            }
            messages.append(ChatMessage(role: .system, text: "↩️ \(res.message)"))
            if res.success { await onEventsChanged?() }
        } catch let e as APIError {
            handle(e, retryQuery: nil)
        } catch {
            messages.append(ChatMessage(role: .assistant, text: "Couldn't undo that. Try again.", card: .error(retryQuery: nil)))
        }
    }

    // MARK: - Find nearby

    func findNearby(query: String, category: String? = nil) async {
        isThinking = true
        defer { isThinking = false }

        guard let coord = await location.currentCoordinate() ?? fallbackCoordinate else {
            messages.append(ChatMessage(
                role: .assistant,
                text: "I need your location to find places nearby. Enable location for Roammate in Settings, then try again.",
                card: .error(retryQuery: nil)
            ))
            return
        }

        do {
            let res = try await ConciergeService.findNearby(
                tripId: tripId,
                request: FindNearbyRequest(
                    query: query, lat: coord.latitude, lng: coord.longitude,
                    category: category, limit: 3
                )
            )
            if res.places.isEmpty {
                messages.append(ChatMessage(role: .assistant, text: "I couldn't find any \(query) nearby."))
            } else {
                messages.append(ChatMessage(
                    role: .assistant,
                    text: "Found \(res.places.count) option\(res.places.count == 1 ? "" : "s") nearby:",
                    card: .placeCards(res.places)
                ))
            }
        } catch let e as APIError {
            handle(e, retryQuery: nil)
        } catch {
            messages.append(ChatMessage(role: .assistant, text: "Search failed. Try again.", card: .error(retryQuery: nil)))
        }
    }

    /// Show "View on map" for a set of place results.
    func viewOnMap(_ places: [PlaceCard]) {
        nearbyPins = places
        detail = .map
    }

    /// Selecting a place builds an add-event confirmation card (web parity).
    func selectPlace(_ place: PlaceCard) {
        let travelMin = place.travelTimeS.map { max(1, Int(ceil(Double($0) / 60.0))) } ?? 15
        let arrival = Date().addingTimeInterval(Double(travelMin) * 60)
        let tod = wallClock(arrival)

        var params: [String: JSONValue] = [
            "title": .string(place.title),
            "start_time": .string(tod.wireString),
            "place_id": .string(place.placeId),
            "lat": .double(place.lat),
            "lng": .double(place.lng),
        ]
        if let address = place.address { params["address"] = .string(address) }
        if let photo = place.photoUrl { params["photo_url"] = .string(photo) }
        if let rating = place.rating { params["rating"] = .double(rating) }
        if let price = place.priceLevel { params["price_level"] = .int(price) }
        if let types = place.types { params["types"] = .array(types.map { .string($0) }) }
        if let category = place.category { params["category"] = .string(category) }

        messages.append(ChatMessage(
            role: .assistant,
            text: "Add **\(place.title)** at \(displayTime(tod))?",
            card: .actionCard,
            status: .pending,
            intent: .addEvent,
            params: params
        ))
    }

    // MARK: - Running late (Smart Ripple)

    func runningLate(minutes: Int) async {
        isThinking = true
        defer { isThinking = false }
        do {
            let updated = try await EventService.ripple(
                tripId: tripId,
                request: RippleRequest(deltaMinutes: minutes, startFromTime: Date())
            )
            messages.append(ChatMessage(
                role: .assistant,
                card: .rippleResult(shifted: updated.count, minutes: minutes)
            ))
            await onEventsChanged?()
        } catch let e as APIError {
            handle(e, retryQuery: nil)
        } catch {
            messages.append(ChatMessage(role: .assistant, text: "Couldn't shift the timeline. Try again.", card: .error(retryQuery: nil)))
        }
    }

    // MARK: - Skip next

    func skipNext() async {
        isThinking = true
        let next = await whatsNextEvent()
        isThinking = false
        guard let next else {
            messages.append(ChatMessage(role: .assistant, text: "Nothing left to skip today — you're all caught up."))
            return
        }
        messages.append(ChatMessage(
            role: .assistant,
            text: "Skip **\(next.title)**?",
            card: .actionCard,
            status: .pending,
            intent: .skipEvent,
            params: ["event_id": .int(next.id)]
        ))
    }

    // MARK: - Live cards

    func whatsNext() async {
        isThinking = true
        defer { isThinking = false }
        guard let res = try? await ConciergeService.whatsNext(tripId: tripId) else {
            messages.append(ChatMessage(role: .assistant, text: "I couldn't load what's next right now."))
            return
        }
        messages.append(ChatMessage(role: .assistant, card: .whatsNext(res)))
    }

    func todaySummary() async {
        isThinking = true
        defer { isThinking = false }
        guard let res = try? await ConciergeService.todaySummary(tripId: tripId) else {
            messages.append(ChatMessage(role: .assistant, text: "I couldn't load your day right now."))
            return
        }
        messages.append(ChatMessage(role: .assistant, card: .summary(res)))
    }

    private func whatsNextEvent() async -> Event? {
        guard let res = try? await ConciergeService.whatsNext(tripId: tripId),
              let json = res.nextEvent else { return nil }
        return Event(conciergeJSON: json)
    }

    // MARK: - Availability (day-of gating)

    var todayString: String {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.timeZone = TimeZone(identifier: trip.timezone ?? "UTC") ?? .current
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: Date())
    }

    /// `nil` when the Concierge is live today; otherwise a banner explaining why
    /// actions are dormant.
    var availabilityBanner: String? {
        guard let start = trip.startDate, let end = trip.endDate else { return nil }
        let today = todayString
        let startKey = EventService.isoDateString(from: start)
        let endKey = EventService.isoDateString(from: end)
        if today < startKey {
            let fmt = DateFormatter()
            fmt.dateFormat = "EEE, MMM d"
            return "Concierge goes live on \(fmt.string(from: start)). You can still ask questions now."
        }
        if today > endKey {
            return "This trip has wrapped up — Concierge actions are paused."
        }
        return nil
    }

    var isLiveDay: Bool { availabilityBanner == nil }

    // MARK: - Helpers

    private func setStatus(_ id: UUID, _ status: ActionStatus) {
        guard let idx = messages.firstIndex(where: { $0.id == id }) else { return }
        messages[idx].status = status
    }

    private func wallClock(_ date: Date) -> TimeOfDay {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: trip.timezone ?? "UTC") ?? .current
        return TimeOfDay(date: date, calendar: cal)
    }

    private func displayTime(_ tod: TimeOfDay) -> String {
        let suffix = tod.hour < 12 ? "AM" : "PM"
        let h12 = tod.hour == 0 ? 12 : (tod.hour > 12 ? tod.hour - 12 : tod.hour)
        return String(format: "%d:%02d %@", h12, tod.minute, suffix)
    }

    /// Centralised APIError handling: 402 is already handled by `APIClient`
    /// (it posts `.needsPlus`, opening the paywall), so we stay quiet there.
    private func handle(_ e: APIError, retryQuery: String?) {
        if case .paymentRequired = e { return }
        if case .serverError(423, _) = e {
            messages.append(ChatMessage(
                role: .assistant,
                text: "Concierge is part of the guided tour here — finish the tutorial to chat freely."
            ))
            return
        }
        messages.append(ChatMessage(
            role: .assistant,
            text: e.errorDescription ?? "Something went wrong.",
            card: .error(retryQuery: retryQuery)
        ))
    }
}
