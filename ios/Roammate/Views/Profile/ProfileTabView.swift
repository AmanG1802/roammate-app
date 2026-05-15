import SwiftUI

struct ProfileTabView: View {
    @EnvironmentObject var authManager: AuthManager
    @EnvironmentObject var tabBarVisibility: TabBarVisibility

    @State private var showDeleteConfirm = false
    @State private var deleteError: String?

    var body: some View {
        NavigationStack {
            ZStack {
                Color.roammateBackground.ignoresSafeArea()
                ScrollView {
                    VStack(spacing: RoammateSpacing.md) {
                        header

                        VStack(spacing: 10) {
                            settingsRow(
                                icon: "person.crop.circle",
                                title: "Edit Profile",
                                destination: AnyView(EditProfileView().environmentObject(authManager).tabBarHiding())
                            )
                            settingsRow(
                                icon: "wand.and.stars",
                                title: "Travel Persona",
                                destination: AnyView(PersonasView().environmentObject(authManager).tabBarHiding())
                            )
                            settingsRow(
                                icon: "bell.badge",
                                title: "Notifications",
                                destination: AnyView(NotificationsSettingsView().tabBarHiding())
                            )
                            settingsRow(
                                icon: "sparkles.rectangle.stack",
                                title: "Subscription",
                                destination: AnyView(SubscriptionView().tabBarHiding())
                            )
                        }

                        SectionHeader(title: "About")
                            .padding(.top, RoammateSpacing.sm)

                        VStack(spacing: 10) {
                            settingsRow(
                                icon: "info.circle",
                                title: "About Roammate",
                                destination: AnyView(AboutView().tabBarHiding())
                            )
                        }

                        VStack(spacing: 10) {
                            actionRow(icon: "rectangle.portrait.and.arrow.right", title: "Log Out", tint: Color.roammateInk) {
                                HapticManager.medium()
                                authManager.logout()
                            }
                            actionRow(icon: "trash", title: "Delete Account", tint: Color.roammateDanger) {
                                HapticManager.warning()
                                showDeleteConfirm = true
                            }
                            if let deleteError {
                                Text(deleteError)
                                    .font(.system(.caption, design: .rounded))
                                    .foregroundStyle(Color.roammateDanger)
                            }
                        }
                        .padding(.top, RoammateSpacing.sm)
                    }
                    .padding(.horizontal, RoammateSpacing.md)
                    .padding(.top, RoammateSpacing.md)
                    .padding(.bottom, RoammateLayout.contentBottomPadding)
                }
            }
            .navigationTitle("Profile")
            .navigationBarTitleDisplayMode(.large)
            .alert("Delete account?", isPresented: $showDeleteConfirm) {
                Button("Delete", role: .destructive) {
                    Task { await deleteAccount() }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This permanently removes your account, trips, and ideas. This cannot be undone.")
            }
        }
    }

    // MARK: - Header

    private var header: some View {
        HStack(spacing: RoammateSpacing.md) {
            Group {
                if let url = authManager.currentUser?.avatarUrl,
                   !url.isEmpty,
                   let imageURL = URL(string: url) {
                    AsyncImage(url: imageURL) { phase in
                        switch phase {
                        case .success(let image):
                            image.resizable().scaledToFill()
                        default:
                            initialsAvatar
                        }
                    }
                    .frame(width: 64, height: 64)
                    .clipShape(Circle())
                } else {
                    initialsAvatar
                }
            }
            .shadow(color: Color.roammateIndigo.opacity(0.3), radius: 12, x: 0, y: 4)

            VStack(alignment: .leading, spacing: 2) {
                Text(authManager.currentUser?.name ?? "")
                    .font(.system(.title3, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.roammateInk)
                Text(authManager.currentUser?.email ?? "")
                    .font(.system(.subheadline, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
            }
            Spacer()
        }
        .padding(RoammateSpacing.md)
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.card, style: .continuous)
                .fill(Color.roammateSurface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: RoammateRadius.card, style: .continuous)
                .stroke(Color.roammateBorder, lineWidth: 1)
        )
    }

    private var initialsAvatar: some View {
        ZStack {
            Circle()
                .fill(
                    LinearGradient(
                        colors: [Color.roammateIndigo, Color.roammateIndigoDark],
                        startPoint: .topLeading, endPoint: .bottomTrailing
                    )
                )
                .frame(width: 64, height: 64)
            Text(initials(authManager.currentUser?.name ?? ""))
                .font(.system(size: 24, weight: .black, design: .rounded))
                .foregroundStyle(.white)
        }
    }

    // MARK: - Reusable rows

    private func settingsRow(icon: String, title: String, destination: AnyView) -> some View {
        NavigationLink(destination: destination) {
            HStack(spacing: RoammateSpacing.md) {
                ZStack {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(Color.roammateIndigoTint)
                    Image(systemName: icon)
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(Color.roammateIndigo)
                }
                .frame(width: 44, height: 44)

                Text(title)
                    .font(.system(.body, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateInk)

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(Color.roammateMuted)
            }
            .padding(.horizontal, RoammateSpacing.md)
            .padding(.vertical, 14)
            .background(
                RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                    .fill(Color.roammateSurface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                    .stroke(Color.roammateBorder, lineWidth: 1)
            )
        }
        .buttonStyle(RoammateRowButtonStyle())
    }

    private func actionRow(icon: String, title: String, tint: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: RoammateSpacing.md) {
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(tint)
                    .frame(width: 44, height: 44)
                Text(title)
                    .font(.system(.body, design: .rounded, weight: .semibold))
                    .foregroundStyle(tint)
                Spacer()
            }
            .padding(.horizontal, RoammateSpacing.md)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                    .fill(Color.roammateSurface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                    .stroke(Color.roammateBorder, lineWidth: 1)
            )
        }
        .buttonStyle(RoammateRowButtonStyle())
    }

    // MARK: - Actions

    private func initials(_ name: String) -> String {
        name.split(separator: " ")
            .prefix(2)
            .compactMap { $0.first.map(String.init) }
            .joined()
            .uppercased()
    }

    private func deleteAccount() async {
        do {
            try await AuthService.deleteAccount()
            authManager.logout()
        } catch let e as APIError {
            deleteError = e.errorDescription
        } catch {
            deleteError = error.localizedDescription
        }
    }
}

// MARK: - Tab Bar Hiding Wrapper

private struct TabBarHidingModifier: ViewModifier {
    @EnvironmentObject var tabBarVisibility: TabBarVisibility

    func body(content: Content) -> some View {
        content
            .onAppear {
                withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                    tabBarVisibility.isVisible = false
                }
            }
            .onDisappear {
                withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                    tabBarVisibility.isVisible = true
                }
            }
    }
}

extension View {
    func tabBarHiding() -> some View {
        modifier(TabBarHidingModifier())
    }
}
