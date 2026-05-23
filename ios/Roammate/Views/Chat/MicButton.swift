import SwiftUI

/// Reusable mic button for dictating speech into a chat input. Shared by all
/// three AI chat input bars. Sits immediately before the send button.
///
/// Behaviour is fill-the-box: on start it snapshots the bound `text` as a base,
/// then mirrors `recognizer.transcript` into the binding as `base + transcript`
/// so the user can edit before sending. No auto-send.
struct MicButton: View {
    @Binding var text: String
    @ObservedObject var recognizer: SpeechRecognizer
    var disabled: Bool = false

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// Snapshot of `text` when the current dictation session began.
    @State private var base: String = ""
    /// Drives the pulsing scale while recording.
    @State private var pulse = false
    /// Set once the user denies permission, so we hide the mic gracefully.
    @State private var permissionDenied = false

    var body: some View {
        if !permissionDenied {
            Button(action: toggle) {
                Image(systemName: recognizer.isRecording ? "mic.fill" : "mic")
                    .font(.system(size: 22, weight: .medium))
                    .foregroundStyle(recognizer.isRecording ? Color.roammateDanger : Color.roammateMuted)
                    .frame(width: 36, height: 36)
                    .scaleEffect(pulse ? 1.18 : 1)
            }
            .buttonStyle(.plain)
            .disabled(disabled)
            .accessibilityLabel(recognizer.isRecording ? "Stop voice input" : "Start voice input")
            .onChange(of: recognizer.transcript) { _, newValue in
                guard recognizer.isRecording else { return }
                text = merge(base, newValue)
            }
            .onChange(of: recognizer.isRecording) { _, recording in
                updatePulse(recording: recording)
            }
        }
    }

    private func toggle() {
        if recognizer.isRecording {
            HapticManager.light()
            recognizer.stopTranscribing()
            // Commit base + final transcript (already mirrored via onChange).
            return
        }

        Task {
            if !recognizer.isAvailable {
                await recognizer.requestAuthorization()
            }
            guard recognizer.isAvailable else {
                permissionDenied = true
                return
            }
            base = text
            HapticManager.medium()
            recognizer.startTranscribing()
        }
    }

    private func updatePulse(recording: Bool) {
        guard !reduceMotion else { pulse = false; return }
        if recording {
            withAnimation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true)) {
                pulse = true
            }
        } else {
            withAnimation(.easeOut(duration: 0.2)) { pulse = false }
        }
    }

    /// Join the base string with dictated text, inserting a space if needed.
    private func merge(_ base: String, _ addition: String) -> String {
        let add = addition.trimmingCharacters(in: .whitespacesAndNewlines)
        if base.isEmpty { return add }
        if base.last?.isWhitespace == true { return base + add }
        return "\(base) \(add)"
    }
}
