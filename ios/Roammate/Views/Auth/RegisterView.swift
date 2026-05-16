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
                ScrollView {
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

                        OAuthButtonsView(mode: .signUp)
                            .environmentObject(authManager)
                            .padding(.horizontal, RoammateSpacing.lg)

                        AuthDivider(label: "or sign up with email")
                            .padding(.horizontal, RoammateSpacing.lg)

                        VStack(spacing: RoammateSpacing.sm) {
                            TextField("Full name", text: $name)
                                .autocorrectionDisabled()
                                .authField()
                            TextField("Email", text: $email)
                                .keyboardType(.emailAddress)
                                .autocorrectionDisabled()
                                .textInputAutocapitalization(.never)
                                .authField()
                            SecureField("Password (8+ characters)", text: $password).authField()

                            if let error = authManager.error {
                                Text(error)
                                    .font(.system(.caption, design: .rounded))
                                    .foregroundStyle(Color.roammateDanger)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }

                            Button {
                                Task {
                                    await authManager.signup(name: name, email: email, password: password)
                                    if authManager.pendingVerificationEmail != nil {
                                        dismiss()
                                    }
                                }
                            } label: {
                                if authManager.isLoading {
                                    ProgressView().tint(.white)
                                } else {
                                    Text("Create Account")
                                }
                            }
                            .buttonStyle(RoammatePrimaryButtonStyle(isLoading: authManager.isLoading))
                            .disabled(authManager.isLoading || name.isEmpty || email.isEmpty || password.count < 8)
                            .padding(.top, RoammateSpacing.sm)
                        }
                        .padding(.horizontal, RoammateSpacing.lg)

                        Spacer()
                    }
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
}
