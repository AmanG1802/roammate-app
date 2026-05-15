import SwiftUI

private struct PersonaItem: Codable, Identifiable, Hashable {
    let slug: String
    let label: String
    let icon: String
    let description: String?
    var id: String { slug }
}

struct PersonasView: View {
    @EnvironmentObject var authManager: AuthManager
    @Environment(\.dismiss) private var dismiss

    @State private var catalog: [PersonaItem] = []
    @State private var selected: Set<String> = []
    @State private var savedSelected: Set<String> = []
    @State private var isLoading = true
    @State private var isSaving = false
    @State private var error: String?

    private var dirty: Bool { selected != savedSelected }

    var body: some View {
        ZStack {
            Color.roammateBackground.ignoresSafeArea()

            if isLoading {
                ProgressView()
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: RoammateSpacing.md) {
                        intro

                        FlowLayout(spacing: 10, rowSpacing: 10) {
                            ForEach(sortedCatalog) { item in
                                chip(item)
                            }
                        }
                        .padding(.horizontal, RoammateSpacing.md)

                        if let error {
                            Text(error)
                                .font(.system(.caption, design: .rounded))
                                .foregroundStyle(Color.roammateDanger)
                                .padding(.horizontal, RoammateSpacing.md)
                        }
                    }
                    .padding(.top, RoammateSpacing.sm)
                    .padding(.bottom, RoammateSpacing.xl)
                }
            }
        }
        .navigationTitle("Travel Personas")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                HStack(spacing: 14) {
                    Button {
                        HapticManager.light()
                        selected = savedSelected
                    } label: {
                        Image(systemName: "arrow.counterclockwise")
                    }
                    .disabled(!dirty || isSaving)

                    Button {
                        Task { await save() }
                    } label: {
                        if isSaving { ProgressView() } else {
                            Text("Save").font(.system(.body, design: .rounded, weight: .semibold))
                        }
                    }
                    .disabled(!dirty || isSaving)
                }
            }
        }
        .task { await load() }
    }

    // MARK: - Sub-views

    private var intro: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("Pick what you love")
                .font(.system(.title3, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateInk)
            Text("These shape what your AI concierge suggests.")
                .font(.system(.subheadline, design: .rounded))
                .foregroundStyle(Color.roammateMuted)
        }
        .padding(.horizontal, RoammateSpacing.md)
    }

    /// Selected chips render first, then unselected — both in catalog order.
    private var sortedCatalog: [PersonaItem] {
        let sel = catalog.filter { selected.contains($0.slug) }
        let unsel = catalog.filter { !selected.contains($0.slug) }
        return sel + unsel
    }

    private func chip(_ item: PersonaItem) -> some View {
        let isSelected = selected.contains(item.slug)
        return Button {
            HapticManager.light()
            if isSelected { selected.remove(item.slug) } else { selected.insert(item.slug) }
        } label: {
            HStack(spacing: 6) {
                Text(item.icon)
                    .font(.system(size: 16))
                Text(item.label)
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(isSelected ? .white : Color.roammateInk)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(
                Capsule().fill(isSelected ? Color.roammateIndigo : Color.roammateSurface)
            )
            .overlay(
                Capsule().stroke(
                    isSelected ? Color.roammateIndigo : Color.roammateBorder,
                    lineWidth: 1
                )
            )
            .shadow(
                color: isSelected ? Color.roammateIndigo.opacity(0.25) : .clear,
                radius: 8, x: 0, y: 4
            )
        }
        .buttonStyle(.plain)
        .animation(.spring(response: 0.3, dampingFraction: 0.85), value: isSelected)
    }

    // MARK: - Networking

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let raw: [PersonaItem] = try await APIClient.shared.request("/users/personas/catalog")
            catalog = raw
            let current = Set(authManager.currentUser?.personas ?? [])
            selected = current
            savedSelected = current
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func save() async {
        isSaving = true
        defer { isSaving = false }
        do {
            try await AuthService.updatePersonas(Array(selected))
            savedSelected = selected
            authManager.currentUser = try? await AuthService.getMe()
            HapticManager.success()
        } catch {
            HapticManager.error()
            self.error = error.localizedDescription
        }
    }
}
