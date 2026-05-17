import SwiftUI
import AuthenticationServices

#if canImport(GoogleSignIn)
import GoogleSignIn
import GoogleSignInSwift
#endif

/// The "Continue with Google / Apple" stack used at the top of LoginView and RegisterView.
/// Both buttons match RoammateRadius.button (18) for visual continuity with the email CTA.
struct OAuthButtonsView: View {
    enum Mode { case signIn, signUp }

    let mode: Mode
    @EnvironmentObject var authManager: AuthManager

    var body: some View {
        VStack(spacing: RoammateSpacing.sm) {
            SignInWithAppleButton(mode == .signUp ? .signUp : .signIn,
                onRequest: { req in
                    req.requestedScopes = [.fullName, .email]
                    req.nonce = authManager.prepareAppleNonce()
                },
                onCompletion: { result in
                    switch result {
                    case .success(let auth):
                        Task { await authManager.handleAppleAuthorization(auth) }
                    case .failure(let err):
                        // User cancellations come through here too; only show real errors.
                        if (err as NSError).code != ASAuthorizationError.canceled.rawValue {
                            authManager.error = err.localizedDescription
                        }
                    }
                }
            )
            .signInWithAppleButtonStyle(.black)
            .frame(height: 48)
            .cornerRadius(RoammateRadius.button)

            #if canImport(GoogleSignIn)
            GoogleSignInButton(
                viewModel: GoogleSignInButtonViewModel(scheme: .light, style: .wide, state: .normal)
            ) {
                signInWithGoogle()
            }
            .frame(height: 48)
            .cornerRadius(RoammateRadius.button)
            #else
            // Build without GoogleSignIn SPM dep: render a styled fallback that
            // shows the button shape but is disabled until the package is added.
            Button(action: {}) {
                HStack {
                    Image(systemName: "g.circle.fill")
                    Text("Continue with Google")
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
            }
            .buttonStyle(.bordered)
            .controlSize(.large)
            .disabled(true)
            .opacity(0.5)
            #endif
        }
    }

    #if canImport(GoogleSignIn)
    private func signInWithGoogle() {
        guard let scene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let root = scene.windows.first?.rootViewController else { return }
        GIDSignIn.sharedInstance.signIn(withPresenting: root) { result, error in
            if let error = error as NSError?, error.code != GIDSignInError.canceled.rawValue {
                authManager.error = error.localizedDescription
                return
            }
            guard let idToken = result?.user.idToken?.tokenString else {
                authManager.error = "Google sign-in failed: no ID token"
                return
            }
            Task { await authManager.signInWithGoogle(idToken: idToken) }
        }
    }
    #endif
}
