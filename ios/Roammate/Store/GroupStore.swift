import SwiftUI

@MainActor
final class GroupStore: ObservableObject {
    @Published var groups: [TravelGroup] = []

    @Published var pendingInvitations: [GroupInvitation] = []
    @Published var isLoading = false
    @Published var error: String?

    private let cacheKey = "groups"

    init() {
        groups = DiskCache.shared.load([TravelGroup].self, key: cacheKey) ?? []
    }

    func load() async {
        isLoading = true
        error = nil
        defer { isLoading = false }
        do {
            let fresh = try await GroupService.getGroups()
            groups = fresh
            DiskCache.shared.store(fresh, key: cacheKey)
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func loadInvitations() async {
        pendingInvitations = (try? await GroupService.getPendingGroupInvitations()) ?? pendingInvitations
    }

    func create(name: String) async -> GroupDetail? {
        do {
            let created = try await GroupService.createGroup(name: name)
            await load()
            return created
        } catch let e as APIError {
            error = e.errorDescription
            return nil
        } catch {
            self.error = error.localizedDescription
            return nil
        }
    }

    func acceptInvitation(memberId: Int) async {
        do {
            _ = try await GroupService.acceptGroupInvitation(memberId: memberId)
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
            try await GroupService.declineGroupInvitation(memberId: memberId)
            pendingInvitations.removeAll { $0.id == memberId }
        } catch let e as APIError {
            error = e.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }
}
