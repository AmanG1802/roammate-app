import SwiftUI

/// First-time persona picker, presented from `MainShell` once per session when
/// the signed-in user has no personas set. Mirrors the web `OnboardingPersonaModal`.
///
/// On Save or Skip, calls back so the host can dismiss and chain into the Plus
/// onboarding sheet.
struct OnboardingPersonasSheet: View {
    let onComplete: (_ personas: [String]) -> Void
    let onSkip: () -> Void

    @EnvironmentObject private var authManager: AuthManager
    @State private var catalog: [PersonaItem] = []
    @State private var selected: Set<String> = []
    @State private var isLoading = true
    @State private var isSaving = false
    @State private var error: String?

    private struct PersonaItem: Codable, Identifiable, Hashable {
        let slug: String
        let label: String
        let icon: String
        let description: String?
        var id: String { slug }
    }

    var body: some View {
        VStack(spacing: 0) {
            header

            if isLoading {
                Spacer()
                ProgressView()
                Spacer()
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: RoammateSpacing.md) {
                        Text("Select your travel personas — your concierge adapts to match your style.")
                            .font(.system(.subheadline, design: .rounded))
                            .foregroundStyle(Color.roammateMuted)
                            .padding(.horizontal, RoammateSpacing.md)

                        FlowLayout(spacing: 10, rowSpacing: 10) {
                            ForEach(sortedCatalog) { item in chip(item) }
                        }
                        .padding(.horizontal, RoammateSpacing.md)

                        if let error {
                            Text(error)
                                .font(.system(.caption, design: .rounded))
                                .foregroundStyle(Color.roammateDanger)
                                .padding(.horizontal, RoammateSpacing.md)
                        }
                    }
                    .padding(.vertical, RoammateSpacing.sm)
                }
            }

            footer
        }
        .background(Color.roammateBackground.ignoresSafeArea())
        .task { await load() }
    }

    // MARK: - Sub-views

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("What kind of traveler are you?")
                .font(.system(.title2, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateInk)
            Text("Pick a few — you can change these anytime in Profile.")
                .font(.system(.subheadline, design: .rounded))
                .foregroundStyle(Color.roammateMuted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(RoammateSpacing.md)
    }

    private var footer: some View {
        HStack(spacing: 12) {
            Button {
                HapticManager.light()
                onSkip()
            } label: {
                Text("Skip")
                    .font(.system(.body, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateMuted)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(Capsule().fill(Color.roammateSurface))
                    .overlay(Capsule().stroke(Color.roammateBorder, lineWidth: 1))
            }
            .buttonStyle(.plain)
            .disabled(isSaving)

            Button {
                Task { await save() }
            } label: {
                HStack {
                    if isSaving { ProgressView().tint(.white) }
                    Text(isSaving ? "Saving…" : "Continue")
                        .font(.system(.body, design: .rounded, weight: .bold))
                }
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(Capsule().fill(selected.isEmpty ? Color.roammateMuted : Color.roammateIndigo))
            }
            .buttonStyle(.plain)
            .disabled(isSaving || selected.isEmpty)
        }
        .padding(RoammateSpacing.md)
    }

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
                Text(item.icon).font(.system(size: 16))
                Text(item.label)
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(isSelected ? .white : Color.roammateInk)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(Capsule().fill(isSelected ? Color.roammateIndigo : Color.roammateSurface))
            .overlay(Capsule().stroke(isSelected ? Color.roammateIndigo : Color.roammateBorder, lineWidth: 1))
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
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func save() async {
        isSaving = true
        defer { isSaving = false }
        do {
            let chosen = Array(selected)
            try await AuthService.updatePersonas(chosen)
            authManager.currentUser = try? await AuthService.getMe()
            HapticManager.success()
            onComplete(chosen)
        } catch {
            HapticManager.error()
            self.error = error.localizedDescription
        }
    }
}
