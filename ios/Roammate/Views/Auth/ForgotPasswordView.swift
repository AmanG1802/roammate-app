import SwiftUI

struct ForgotPasswordView: View {
    @EnvironmentObject var authManager: AuthManager
    @Environment(\.dismiss) private var dismiss

    @State private var email = ""
    @State private var sent = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.roammateBackground.ignoresSafeArea()
                VStack(spacing: RoammateSpacing.md) {
                    VStack(spacing: 6) {
                        Text("Reset your password")
                            .font(.system(.title2, design: .rounded, weight: .black))
                            .foregroundStyle(Color.roammateInk)
                        Text("Enter your email and we'll send you a reset link.")
                            .font(.system(.subheadline, design: .rounded))
                            .multilineTextAlignment(.center)
                            .foregroundStyle(Color.roammateMuted)
                    }
                    .padding(.top, RoammateSpacing.lg)
                    .padding(.horizontal, RoammateSpacing.lg)

                    TextField("Email", text: $email)
                        .keyboardType(.emailAddress)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                        .authField()
                        .padding(.horizontal, RoammateSpacing.lg)

                    if sent {
                        Text("If an account exists for that email, a reset link is on its way.")
                            .font(.system(.footnote, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.roammateSuccess)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, RoammateSpacing.lg)
                    }

                    if let error = authManager.error {
                        Text(error)
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(Color.roammateDanger)
                            .padding(.horizontal, RoammateSpacing.lg)
                    }

                    Button {
                        Task {
                            await authManager.forgotPassword(email: email)
                            sent = true
                        }
                    } label: {
                        if authManager.isLoading {
                            ProgressView().tint(.white)
                        } else {
                            Text("Send reset link")
                        }
                    }
                    .buttonStyle(RoammatePrimaryButtonStyle(isLoading: authManager.isLoading))
                    .disabled(email.isEmpty || authManager.isLoading)
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
}
