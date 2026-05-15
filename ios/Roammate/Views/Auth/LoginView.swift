import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authManager: AuthManager

    @State private var email = ""
    @State private var password = ""
    @State private var showRegister = false

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color.roammateBackground, Color.roammateIndigoTint],
                startPoint: .topLeading, endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer()

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

                Spacer()

                VStack(spacing: RoammateSpacing.sm) {
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
                        Task { await authManager.login(email: email, password: password) }
                    } label: {
                        if authManager.isLoading {
                            ProgressView().tint(.white)
                        } else {
                            Text("Log In")
                        }
                    }
                    .buttonStyle(RoammatePrimaryButtonStyle(isLoading: authManager.isLoading))
                    .disabled(authManager.isLoading || email.isEmpty || password.isEmpty)
                    .padding(.top, RoammateSpacing.sm)

                    Button {
                        HapticManager.light()
                        showRegister = true
                    } label: {
                        Text("Don't have an account? ")
                            .foregroundStyle(Color.roammateMuted)
                        + Text("Sign up").foregroundStyle(Color.roammateIndigo).bold()
                    }
                    .font(.system(.footnote, design: .rounded))
                    .padding(.top, RoammateSpacing.sm)
                }
                .padding(.horizontal, RoammateSpacing.lg)

                Spacer()
            }
        }
        .sheet(isPresented: $showRegister) {
            RegisterView()
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
