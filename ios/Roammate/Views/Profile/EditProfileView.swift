import SwiftUI
import PhotosUI

struct EditProfileView: View {
    @EnvironmentObject var authManager: AuthManager
    @Environment(\.dismiss) private var dismiss

    // Profile fields
    @State private var name: String = ""
    @State private var homeCity: String = ""
    @State private var timezone: String = "Asia/Kolkata"
    @State private var currency: String = "INR"
    @State private var travelBlurb: String = ""

    // Avatar
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var avatarImage: Image?
    @State private var avatarData: Data?

    // Password change (optional, in one screen)
    @State private var showPasswordSection = false
    @State private var currentPassword = ""
    @State private var newPassword = ""
    @State private var confirmPassword = ""

    @State private var isSaving = false
    @State private var error: String?

    // Unsaved-changes tracking
    @State private var isDirty = false
    @State private var showDiscardConfirm = false

    // Hydrated values for dirty comparison
    @State private var hydratedName: String = ""
    @State private var hydratedHomeCity: String = ""
    @State private var hydratedTimezone: String = "Asia/Kolkata"
    @State private var hydratedCurrency: String = "INR"
    @State private var hydratedTravelBlurb: String = ""

    private let currencies = ["USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD", "SGD"]

    private var canSave: Bool {
        if showPasswordSection {
            return !name.isEmpty &&
                   !currentPassword.isEmpty &&
                   newPassword.count >= 8 &&
                   newPassword == confirmPassword
        }
        return !name.isEmpty || avatarData != nil
    }

    var body: some View {
        ZStack {
            Color.roammateBackground.ignoresSafeArea()
            ScrollView {
                VStack(spacing: RoammateSpacing.lg) {
                    avatarHero(avatarUrl: authManager.currentUser?.avatarUrl)

                    nameCard
                    homeCard
                    travelStyleCard
                    if authManager.isOAuthUser {
                        oauthProviderCard
                    } else {
                        passwordCard
                    }

                    if let error {
                        Text(error)
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(Color.roammateDanger)
                            .padding(.horizontal, RoammateSpacing.md)
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.top, RoammateSpacing.md)
                .padding(.bottom, RoammateSpacing.xl)
            }
        }
        .navigationTitle("Edit Profile")
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(isDirty)
        .toolbar {
            if isDirty {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        showDiscardConfirm = true
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "chevron.left")
                                .font(.system(size: 16, weight: .semibold))
                            Text("Back")
                        }
                        .foregroundStyle(Color.roammateIndigo)
                    }
                }
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task { await save() }
                } label: {
                    if isSaving { ProgressView() } else {
                        Text("Save").font(.system(.body, design: .rounded, weight: .semibold))
                    }
                }
                .disabled(!canSave || isSaving)
            }
        }
        .confirmationDialog("Discard changes?", isPresented: $showDiscardConfirm, titleVisibility: .visible) {
            Button("Discard", role: .destructive) { dismiss() }
            Button("Keep Editing", role: .cancel) {}
        } message: {
            Text("Your unsaved changes will be lost.")
        }
        .onAppear(perform: hydrate)
        .onChange(of: name) { _, _ in markDirty() }
        .onChange(of: homeCity) { _, _ in markDirty() }
        .onChange(of: timezone) { _, _ in markDirty() }
        .onChange(of: currency) { _, _ in markDirty() }
        .onChange(of: travelBlurb) { _, _ in markDirty() }
        .onChange(of: selectedPhoto) { _, _ in markDirty() }
    }

    // MARK: - Sub-views

    // `avatarUrl` is read by the caller in `body` (main-actor-isolated) and
    // passed in, so this builder doesn't touch the main-actor-isolated
    // `authManager.currentUser` from its own nonisolated context.
    private func avatarHero(avatarUrl: String?) -> some View {
        VStack(spacing: 10) {
            PhotosPicker(selection: $selectedPhoto, matching: .images) {
                ZStack(alignment: .bottomTrailing) {
                    if let avatarImage {
                        avatarImage
                            .resizable()
                            .scaledToFill()
                            .frame(width: 96, height: 96)
                            .clipShape(Circle())
                    } else if let url = avatarUrl, !url.isEmpty {
                        if url.hasPrefix("data:"), let uiImage = UIImage.fromDataURI(url) {
                            Image(uiImage: uiImage)
                                .resizable().scaledToFill()
                                .frame(width: 96, height: 96)
                                .clipShape(Circle())
                        } else if let imageURL = URL(string: url) {
                            AsyncImage(url: imageURL) { phase in
                                switch phase {
                                case .success(let image): image.resizable().scaledToFill()
                                default: initialsCircle
                                }
                            }
                            .frame(width: 96, height: 96)
                            .clipShape(Circle())
                        } else {
                            initialsCircle
                        }
                    } else {
                        initialsCircle
                    }

                    ZStack {
                        Circle()
                            .fill(Color.roammateIndigo)
                            .frame(width: 30, height: 30)
                        Image(systemName: "camera.fill")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(.white)
                    }
                    .offset(x: 2, y: 2)
                }
            }
            .buttonStyle(.plain)
            .onChange(of: selectedPhoto) { _, newItem in
                Task {
                    if let data = try? await newItem?.loadTransferable(type: Data.self) {
                        avatarData = data
                        if let uiImage = UIImage(data: data) {
                            avatarImage = Image(uiImage: uiImage)
                        }
                    }
                }
            }
            .shadow(color: Color.roammateIndigo.opacity(0.35), radius: 16, x: 0, y: 6)

            if let displayEmail = authManager.currentUser?.displayEmail {
                Text(displayEmail)
                    .font(.system(.subheadline, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.top, RoammateSpacing.sm)
    }

    private var initialsCircle: some View {
        ZStack {
            Circle()
                .fill(
                    LinearGradient(
                        colors: [Color.roammateIndigo, Color.roammateIndigoDark],
                        startPoint: .topLeading, endPoint: .bottomTrailing
                    )
                )
                .frame(width: 96, height: 96)
            Text(initials(name))
                .font(.system(size: 38, weight: .black, design: .rounded))
                .foregroundStyle(.white)
        }
    }

    private var nameCard: some View {
        sectionCard(title: "Your name", icon: "person.fill") {
            inputField(placeholder: "Full name", text: $name)
        }
    }

    private var homeCard: some View {
        sectionCard(title: "Home base", icon: "house.fill") {
            VStack(spacing: 10) {
                inputField(placeholder: "Home city", text: $homeCity)

                rowPicker(icon: "globe", title: "Timezone", selection: $timezone, options: TimeZone.knownTimeZoneIdentifiers)
                rowPicker(icon: "creditcard", title: "Currency", selection: $currency, options: currencies)
            }
        }
    }

    private var travelStyleCard: some View {
        sectionCard(title: "How you travel", icon: "airplane") {
            ZStack(alignment: .topLeading) {
                if travelBlurb.isEmpty {
                    Text("A short line about how you like to travel…")
                        .font(.system(.body, design: .rounded))
                        .foregroundStyle(Color.roammateMuted)
                        .padding(.horizontal, 4)
                        .padding(.vertical, 8)
                }
                TextEditor(text: $travelBlurb)
                    .font(.system(.body, design: .rounded))
                    .frame(minHeight: 80)
                    .scrollContentBackground(.hidden)
            }
        }
    }

    private var oauthProviderCard: some View {
        let isApple = authManager.oauthProvider == "apple"
        let icon = isApple ? "applelogo" : "globe"
        let label = isApple ? "Signed in with Apple" : "Signed in with Google"
        return HStack(spacing: 10) {
            Image(systemName: icon)
                .foregroundStyle(Color.roammateInk)
                .frame(width: 22)
            Text(label)
                .font(.system(.subheadline, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.roammateInk)
            Spacer()
            Image(systemName: "lock.fill")
                .font(.system(size: 13))
                .foregroundStyle(Color.roammateMuted)
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

    private var passwordCard: some View {
        VStack(spacing: 0) {
            Toggle(isOn: $showPasswordSection.animation(.spring(response: 0.3, dampingFraction: 0.85))) {
                HStack(spacing: 10) {
                    Image(systemName: "key.fill")
                        .foregroundStyle(Color.roammateIndigo)
                        .frame(width: 22)
                    Text("Change password")
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.roammateInk)
                }
            }
            .tint(Color.roammateIndigo)
            .padding(RoammateSpacing.md)

            if showPasswordSection {
                VStack(spacing: 10) {
                    secureField("Current password", text: $currentPassword)
                    secureField("New password (min 8 chars)", text: $newPassword)
                    secureField("Confirm new password", text: $confirmPassword)

                    if !newPassword.isEmpty && newPassword != confirmPassword {
                        Text("Passwords don't match")
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(Color.roammateDanger)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.bottom, RoammateSpacing.md)
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.card, style: .continuous)
                .fill(Color.roammateSurface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: RoammateRadius.card, style: .continuous)
                .stroke(Color.roammateBorder, lineWidth: 1)
        )
    }

    // MARK: - Reusable helpers

    @ViewBuilder
    private func sectionCard<Content: View>(
        title: String, icon: String, @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .foregroundStyle(Color.roammateIndigo)
                    .frame(width: 22)
                Text(title)
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateInk)
            }
            content()
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

    @ViewBuilder
    private func inputField(placeholder: String, text: Binding<String>) -> some View {
        TextField(placeholder, text: text)
            .font(.system(.body, design: .rounded))
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color.roammateBackground)
            )
    }

    @ViewBuilder
    private func secureField(_ placeholder: String, text: Binding<String>) -> some View {
        SecureField(placeholder, text: text)
            .font(.system(.body, design: .rounded))
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color.roammateBackground)
            )
    }

    @ViewBuilder
    private func rowPicker(icon: String, title: String, selection: Binding<String>, options: [String]) -> some View {
        HStack {
            Image(systemName: icon)
                .foregroundStyle(Color.roammateMuted)
                .frame(width: 22)
            Text(title)
                .font(.system(.body, design: .rounded))
                .foregroundStyle(Color.roammateInk)
            Spacer()
            Picker(title, selection: selection) {
                ForEach(options, id: \.self) { Text($0).tag($0) }
            }
            .labelsHidden()
            .pickerStyle(.menu)
            .tint(Color.roammateIndigo)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 4)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color.roammateBackground)
        )
    }

    // MARK: - Data

    private func initials(_ name: String) -> String {
        let parts = name.split(separator: " ")
        return parts.prefix(2).compactMap { $0.first.map(String.init) }.joined().uppercased()
    }

    private func hydrate() {
        guard let u = authManager.currentUser else { return }
        name = u.name ?? ""
        homeCity = u.homeCity ?? ""
        timezone = u.timezone ?? "Asia/Kolkata"
        currency = u.currency ?? "INR"
        travelBlurb = u.travelBlurb ?? ""
        // Store baseline for dirty tracking and reset dirty flag
        hydratedName = name
        hydratedHomeCity = homeCity
        hydratedTimezone = timezone
        hydratedCurrency = currency
        hydratedTravelBlurb = travelBlurb
        isDirty = false
    }

    private func markDirty() {
        isDirty = name != hydratedName
            || homeCity != hydratedHomeCity
            || timezone != hydratedTimezone
            || currency != hydratedCurrency
            || travelBlurb != hydratedTravelBlurb
            || avatarData != nil
    }

    private func save() async {
        isSaving = true
        error = nil
        defer { isSaving = false }
        do {
            var avatarUrl: String? = nil
            if let avatarData {
                avatarUrl = "data:image/jpeg;base64," + avatarData.base64EncodedString()
            }
            let update = ProfileUpdate(
                name: name,
                avatarUrl: avatarUrl,
                homeCity: homeCity.isEmpty ? nil : homeCity,
                timezone: timezone,
                currency: currency,
                travelBlurb: travelBlurb.isEmpty ? nil : travelBlurb,
                password: showPasswordSection ? newPassword : nil,
                currentPassword: showPasswordSection ? currentPassword : nil
            )
            let updated = try await AuthService.updateMe(update)
            authManager.currentUser = updated
            isDirty = false
            HapticManager.success()
            dismiss()
        } catch let e as APIError {
            HapticManager.error()
            error = e.errorDescription
        } catch {
            HapticManager.error()
            self.error = error.localizedDescription
        }
    }
}
