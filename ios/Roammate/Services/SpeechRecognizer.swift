import Foundation
import Speech
import AVFoundation

/// On-device speech-to-text for dictating into the AI chats. Wraps
/// `SFSpeechRecognizer` + `AVAudioEngine`. Free and on-device — no backend,
/// no quota gating.
///
/// Mirrors the MVVM store pattern (`@MainActor final class … ObservableObject`).
/// The caller observes `transcript` and mirrors it into its own input binding;
/// availability (`isAvailable`) gates whether the mic UI is shown at all.
@MainActor
final class SpeechRecognizer: ObservableObject {
    @Published var transcript: String = ""
    @Published var isRecording: Bool = false
    /// True only when the recognizer exists, is available, and the user has
    /// granted both speech-recognition and microphone permissions.
    @Published var isAvailable: Bool = false

    private let recognizer = SFSpeechRecognizer()
    private let audioEngine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?

    /// Requests speech-recognition + microphone authorization and updates
    /// `isAvailable`. Safe to call repeatedly (e.g. on first mic tap).
    func requestAuthorization() async {
        let speechStatus = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }

        let micGranted = await withCheckedContinuation { continuation in
            AVAudioApplication.requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }

        isAvailable = speechStatus == .authorized
            && micGranted
            && (recognizer?.isAvailable ?? false)
    }

    /// Starts capturing audio and streaming partial transcripts into
    /// `transcript`. No-op if already recording or unavailable.
    func startTranscribing() {
        guard !isRecording, let recognizer, recognizer.isAvailable else { return }

        // Tear down any stale state from a previous session.
        task?.cancel()
        task = nil

        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.record, mode: .measurement, options: .duckOthers)
            try session.setActive(true, options: .notifyOthersOnDeactivation)
        } catch {
            isRecording = false
            return
        }

        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        // Keep audio on-device where the hardware supports it.
        if recognizer.supportsOnDeviceRecognition {
            request.requiresOnDeviceRecognition = true
        }
        self.request = request

        let inputNode = audioEngine.inputNode
        let format = inputNode.outputFormat(forBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak request] buffer, _ in
            request?.append(buffer)
        }

        audioEngine.prepare()
        do {
            try audioEngine.start()
        } catch {
            stopTranscribing()
            return
        }

        transcript = ""
        isRecording = true

        task = recognizer.recognitionTask(with: request) { [weak self] result, error in
            guard let self else { return }
            Task { @MainActor in
                if let result {
                    self.transcript = result.bestTranscription.formattedString
                }
                if error != nil || (result?.isFinal ?? false) {
                    self.stopTranscribing()
                }
            }
        }
    }

    /// Stops the engine, ends the request, and deactivates the audio session.
    func stopTranscribing() {
        if audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        request?.endAudio()
        task?.cancel()
        request = nil
        task = nil
        isRecording = false

        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }
}
