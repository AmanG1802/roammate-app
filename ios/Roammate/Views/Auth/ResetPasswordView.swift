import SwiftUI

/// Presented when a universal-link `…/reset?token=…` arrives.
/// Listens on `.authResetTokenReceived` and shows a sheet with a new-password form.
struct ResetPasswordView: View {
    let token: String
    @EnvironmentObject var authManager: AuthManager
    @Environment(\.dismiss) private var dismiss

    @State private var password = ""
    @State private var confirm = ""

    var body: some View {
        NavigationStack {
            ZStack {
                Color.roammateBackground.ignoresSafeArea()
                VStack(spacing: RoammateSpacing.md) {
                    VStack(spacing: 6) {
                        Text("Choose a new password")
                            .font(.system(.title2, design: .rounded, weight: .black))
                            .foregroundStyle(Color.roammateInk)
                        Text("Make it long, unique, and unforgettable.")
                            .font(.system(.subheadline, design: .rounded))
                            .multilineTextAlignment(.center)
                            .foregroundStyle(Color.roammateMuted)
                    }
                    .padding(.top, RoammateSpacing.lg)
                    .padding(.horizontal, RoammateSpacing.lg)

                    VStack(spacing: RoammateSpacing.sm) {
                        SecureField("New password", text: $password).authField()
                        SecureField("Confirm password", text: $confirm).authField()
                    }
                    .padding(.horizontal, RoammateSpacing.lg)

                    if password != confirm && !confirm.isEmpty {
                        Text("Passwords don't match")
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(Color.roammateDanger)
                    } else if let error = authManager.error {
                        Text(error)
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(Color.roammateDanger)
                            .padding(.horizontal, RoammateSpacing.lg)
                    }

                    Button {
                        Task {
                            await authManager.resetPassword(token: token, newPassword: password)
                            if authManager.isAuthenticated { dismiss() }
                        }
                    } label: {
                        if authManager.isLoading {
                            ProgressView().tint(.white)
                        } else {
                            Text("Update password")
                        }
                    }
                    .buttonStyle(RoammatePrimaryButtonStyle(isLoading: authManager.isLoading))
                    .disabled(password.count < 8 || password != confirm || authManager.isLoading)
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
