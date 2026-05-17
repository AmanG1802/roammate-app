import SwiftUI

/// Shared rounded input style for all auth forms (login, register, forgot, reset).
struct AuthTextFieldStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(.system(.body, design: .rounded))
            .foregroundStyle(Color.roammateInk)
            .tint(Color.roammateIndigo)
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

extension View {
    func authField() -> some View { modifier(AuthTextFieldStyle()) }
}
