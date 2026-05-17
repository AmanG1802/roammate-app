import SwiftUI

struct InviteSheet: View {
    @Environment(\.dismiss) private var dismiss
    let onInvite: (_ email: String, _ role: String) async -> Void

    @State private var email = ""
    @State private var role: String = "view_only"
    @State private var isSending = false

    private let roles: [(value: String, label: String)] = [
        ("admin", "Admin"),
        ("view_with_vote", "Can vote"),
        ("view_only", "View only"),
    ]

    var body: some View {
        NavigationStack {
            Form {
                Section("Who are you inviting?") {
                    TextField("Email address", text: $email)
                        .keyboardType(.emailAddress)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                }
                Section("Their role") {
                    Picker("Role", selection: $role) {
                        ForEach(roles, id: \.value) { r in
                            Text(r.label).tag(r.value)
                        }
                    }
                    .pickerStyle(.inline)
                    .labelsHidden()
                }
            }
            .navigationTitle("Invite traveller")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        Task { await send() }
                    } label: {
                        if isSending { ProgressView() } else { Text("Send").bold() }
                    }
                    .disabled(email.isEmpty || isSending)
                }
            }
        }
    }

    private func send() async {
        isSending = true
        defer { isSending = false }
        await onInvite(email, role)
        HapticManager.success()
        dismiss()
    }
}
