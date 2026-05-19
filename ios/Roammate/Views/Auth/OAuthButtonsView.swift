import SwiftUI
import AuthenticationServices

#if canImport(GoogleSignIn)
import GoogleSignIn
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
            Button(action: signInWithGoogle) {
                HStack(spacing: 10) {
                    GoogleGLogo()
                        .frame(width: 22, height: 22)
                    Text(mode == .signUp ? "Sign up with Google" : "Sign in with Google")
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundStyle(Color(red: 60/255, green: 64/255, blue: 67/255))
                }
                .frame(maxWidth: .infinity)
                .frame(height: 48)
                .background(
                    RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                        .fill(Color.white)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                        .stroke(Color(red: 218/255, green: 220/255, blue: 224/255), lineWidth: 1)
                )
            }
            .buttonStyle(.plain)
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
            if let error = error as NSError? {
                if error.code == GIDSignInError.canceled.rawValue { return }
                authManager.error = error.localizedDescription
                return
            }
            guard let result else {
                authManager.error = "Google sign-in failed: no result"
                return
            }
            if let idToken = result.user.idToken?.tokenString {
                Task { await authManager.signInWithGoogle(idToken: idToken) }
                return
            }
            result.user.refreshTokensIfNeeded { refreshed, refreshError in
                if let refreshError {
                    authManager.error = "Google sign-in failed: \(refreshError.localizedDescription)"
                    return
                }
                guard let idToken = refreshed?.idToken?.tokenString else {
                    let hasAccess = result.user.accessToken.tokenString.isEmpty == false
                    authManager.error = "Google sign-in failed: no ID token (accessToken present: \(hasAccess))"
                    return
                }
                Task { await authManager.signInWithGoogle(idToken: idToken) }
            }
        }
    }
    #endif
}

/// Official multicolor Google "G" mark.
/// Loads `google.png` from the GoogleSignIn SPM resource bundle that's already
/// copied into the app at build time (`GoogleSignIn_GoogleSignIn.bundle`),
/// so no manual drawing or extra asset catalog is needed.
private struct GoogleGLogo: View {
    private static let bundle: Bundle? = {
        Bundle.main
            .url(forResource: "GoogleSignIn_GoogleSignIn", withExtension: "bundle")
            .flatMap { Bundle(url: $0) }
    }()

    var body: some View {
        if let bundle = Self.bundle, let ui = UIImage(named: "google", in: bundle, with: nil) {
            Image(uiImage: ui)
                .resizable()
                .scaledToFit()
        } else {
            // Fallback if the bundle layout ever changes — keeps the button usable.
            Image(systemName: "g.circle.fill")
                .resizable()
                .scaledToFit()
                .foregroundStyle(Color(red: 66/255, green: 133/255, blue: 244/255))
        }
    }
}
