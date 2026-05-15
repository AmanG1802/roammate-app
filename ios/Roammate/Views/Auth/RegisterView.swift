import SwiftUI

struct RegisterView: View {
    @EnvironmentObject var authManager: AuthManager
    @Environment(\.dismiss) private var dismiss

    @State private var name = ""
    @State private var email = ""
    @State private var password = ""

    var body: some View {
        NavigationStack {
            ZStack {
                Color.roammateBackground.ignoresSafeArea()
                VStack(spacing: RoammateSpacing.md) {
                    VStack(spacing: 4) {
                        Text("Create an account")
                            .font(.system(.title2, design: .rounded, weight: .bold))
                            .foregroundStyle(Color.roammateInk)
                        Text("It takes about 10 seconds.")
                            .font(.system(.subheadline, design: .rounded))
                            .foregroundStyle(Color.roammateMuted)
                    }
                    .padding(.top, RoammateSpacing.lg)

                    VStack(spacing: RoammateSpacing.sm) {
                        field("Full name", text: $name, isSecure: false)
                            .autocorrectionDisabled()
                        field("Email", text: $email, isSecure: false)
                            .keyboardType(.emailAddress)
                            .autocorrectionDisabled()
                            .textInputAutocapitalization(.never)
                        field("Password", text: $password, isSecure: true)

                        if let error = authManager.error {
                            Text(error)
                                .font(.system(.caption, design: .rounded))
                                .foregroundStyle(Color.roammateDanger)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }

                        Button {
                            Task { await authManager.register(name: name, email: email, password: password) }
                        } label: {
                            if authManager.isLoading {
                                ProgressView().tint(.white)
                            } else {
                                Text("Create Account")
                            }
                        }
                        .buttonStyle(RoammatePrimaryButtonStyle(isLoading: authManager.isLoading))
                        .disabled(authManager.isLoading || name.isEmpty || email.isEmpty || password.isEmpty)
                        .padding(.top, RoammateSpacing.sm)
                    }
                    .padding(.horizontal, RoammateSpacing.lg)

                    Spacer()
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .foregroundStyle(Color.roammateMuted)
                }
            }
        }
    }

    @ViewBuilder
    private func field(_ placeholder: String, text: Binding<String>, isSecure: Bool) -> some View {
        Group {
            if isSecure {
                SecureField(placeholder, text: text)
            } else {
                TextField(placeholder, text: text)
            }
        }
        .font(.system(.body, design: .rounded))
        .padding(.horizontal, 16)
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
}
