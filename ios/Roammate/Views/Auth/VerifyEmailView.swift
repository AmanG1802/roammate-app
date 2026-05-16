import SwiftUI

struct VerifyEmailView: View {
    let email: String
    @EnvironmentObject var authManager: AuthManager
    @Environment(\.dismiss) private var dismiss
    @State private var didResend = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.roammateBackground.ignoresSafeArea()
                VStack(spacing: RoammateSpacing.lg) {
                    Spacer()
                    Image(systemName: "envelope.badge.fill")
                        .font(.system(size: 56))
                        .foregroundStyle(Color.roammateIndigo)

                    VStack(spacing: RoammateSpacing.sm) {
                        Text("Check your email")
                            .font(.system(.title2, design: .rounded, weight: .black))
                            .foregroundStyle(Color.roammateInk)
                        Text("We sent a verification link to \(email). Tap it to finish setting up your account.")
                            .font(.system(.subheadline, design: .rounded))
                            .multilineTextAlignment(.center)
                            .foregroundStyle(Color.roammateMuted)
                    }
                    .padding(.horizontal, RoammateSpacing.lg)

                    if let error = authManager.error {
                        Text(error)
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(Color.roammateDanger)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, RoammateSpacing.lg)
                    }

                    if didResend {
                        Text("Verification email re-sent.")
                            .font(.system(.footnote, design: .rounded, weight: .bold))
                            .foregroundStyle(Color.roammateSuccess)
                    }

                    Button {
                        Task {
                            await authManager.resendVerification(email: email)
                            didResend = true
                        }
                    } label: {
                        if authManager.isLoading {
                            ProgressView().tint(.white)
                        } else {
                            Text("Resend email")
                        }
                    }
                    .buttonStyle(RoammatePrimaryButtonStyle(isLoading: authManager.isLoading))
                    .padding(.horizontal, RoammateSpacing.lg)

                    Button("Use a different email") { dismiss() }
                        .font(.system(.footnote, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.roammateMuted)

                    Spacer()
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .foregroundStyle(Color.roammateMuted)
                }
            }
        }
    }
}
