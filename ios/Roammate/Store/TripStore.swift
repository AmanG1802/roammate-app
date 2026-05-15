import SwiftUI

@MainActor
final class TripStore: ObservableObject {
    @Published var trips: [Trip] = []
    @Published var pendingInvitations: [Invitation] = []
    @Published var isLoading = false
    @Published var error: String?

    private let cacheKey = "trips"

    init() {
        trips = DiskCache.shared.load([Trip].self, key: cacheKey) ?? []
    }

    func load() async {
        isLoading = true
        error = nil
        defer { isLoading = false }
        do {
            let fresh = try await TripService.getTrips()
            trips = fresh
            DiskCache.shared.store(fresh, key: cacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func loadInvitations() async {
        do {
            pendingInvitations = try await MemberService.getPendingInvitations()
        } catch {
            // Non-fatal — keep current list.
        }
    }

    func create(_ trip: TripCreate) async -> Trip? {
        do {
            let created = try await TripService.createTrip(trip)
            trips.insert(created, at: 0)
            DiskCache.shared.store(trips, key: cacheKey)
            return created
        } catch let e as APIError {
            error = e.errorDescription
            return nil
        } catch {
            self.error = error.localizedDescription
            return nil
        }
    }

    func update(id: Int, _ update: TripUpdate) async {
        do {
            let updated = try await TripService.updateTrip(id: id, update: update)
            if let idx = trips.firstIndex(where: { $0.id == id }) {
                trips[idx] = updated
            }
            DiskCache.shared.store(trips, key: cacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func delete(id: Int) async {
        do {
            try await TripService.deleteTrip(id: id)
            trips.removeAll { $0.id == id }
            DiskCache.shared.store(trips, key: cacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: - Invitations

    func acceptInvitation(memberId: Int) async {
        do {
            _ = try await MemberService.acceptInvitation(memberId: memberId)
            pendingInvitations.removeAll { $0.id == memberId }
            await load()
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func declineInvitation(memberId: Int) async {
        do {
            try await MemberService.declineInvitation(memberId: memberId)
            pendingInvitations.removeAll { $0.id == memberId }
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }
}
