import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authManager: AuthManager

    @State private var email = ""
    @State private var password = ""
    @State private var showRegister = false
    @State private var showForgot = false

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color.roammateBackground, Color.roammateIndigoTint],
                startPoint: .topLeading, endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            ScrollView {
                VStack(spacing: 0) {
                    Spacer(minLength: RoammateSpacing.xxl)

                    VStack(spacing: 8) {
                        Image(systemName: "airplane.circle.fill")
                            .font(.system(size: 56))
                            .foregroundStyle(Color.roammateIndigo)
                        Text("Roammate")
                            .font(.system(.largeTitle, design: .rounded, weight: .black))
                            .foregroundStyle(Color.roammateInk)
                        Text("Plan trips. Together.")
                            .font(.system(.subheadline, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.roammateMuted)
                    }

                    Spacer(minLength: RoammateSpacing.xl)

                    VStack(spacing: RoammateSpacing.md) {
                        OAuthButtonsView(mode: .signIn)
                            .environmentObject(authManager)

                        AuthDivider(label: "or sign in with email")

                        TextField("Email", text: $email)
                            .keyboardType(.emailAddress)
                            .autocorrectionDisabled()
                            .textInputAutocapitalization(.never)
                            .authField()

                        SecureField("Password", text: $password).authField()

                        if let error = authManager.error {
                            Text(error)
                                .font(.system(.caption, design: .rounded))
                                .foregroundStyle(Color.roammateDanger)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }

                        HStack {
                            Spacer()
                            Button("Forgot password?") {
                                HapticManager.light()
                                showForgot = true
                            }
                            .font(.system(.footnote, design: .rounded, weight: .bold))
                            .foregroundStyle(Color.roammateIndigo)
                        }

                        Button {
                            Task { await authManager.login(email: email, password: password) }
                        } label: {
                            if authManager.isLoading {
                                ProgressView().tint(.white)
                            } else {
                                Text("Sign In")
                            }
                        }
                        .buttonStyle(RoammatePrimaryButtonStyle(isLoading: authManager.isLoading))
                        .disabled(authManager.isLoading || email.isEmpty || password.isEmpty)

                        Button {
                            HapticManager.light()
                            showRegister = true
                        } label: {
                            Text("Don't have an account? ").foregroundStyle(Color.roammateMuted)
                            + Text("Sign up").foregroundStyle(Color.roammateIndigo).bold()
                        }
                        .font(.system(.footnote, design: .rounded))
                        .padding(.top, RoammateSpacing.sm)
                    }
                    .padding(.horizontal, RoammateSpacing.lg)

                    Spacer(minLength: RoammateSpacing.xl)
                }
            }
        }
        .sheet(isPresented: $showRegister) {
            RegisterView()
        }
        .sheet(isPresented: $showForgot) {
            ForgotPasswordView()
        }
        .sheet(item: pendingVerification) { binding in
            VerifyEmailView(email: binding.email)
        }
    }

    /// Wrap pendingVerificationEmail so `.sheet(item:)` triggers when set.
    private var pendingVerification: Binding<VerificationEmail?> {
        Binding<VerificationEmail?>(
            get: { authManager.pendingVerificationEmail.map(VerificationEmail.init) },
            set: { newValue in
                if newValue == nil { authManager.pendingVerificationEmail = nil }
            }
        )
    }
}

struct VerificationEmail: Identifiable {
    let email: String
    var id: String { email }
}

struct AuthDivider: View {
    let label: String
    var body: some View {
        HStack(spacing: RoammateSpacing.sm) {
            Rectangle().fill(Color.roammateBorder).frame(height: 1)
            Text(label.uppercased())
                .font(.system(.caption2, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateMuted)
                .tracking(1.4)
            Rectangle().fill(Color.roammateBorder).frame(height: 1)
        }
    }
}
