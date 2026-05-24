import SwiftUI

struct AIChatDrawer: View {
    let trip: Trip
    @StateObject private var store: ConciergeStore
    @Environment(\.dismiss) private var dismiss
    @State private var input: String = ""
    @StateObject private var speech = SpeechRecognizer()
    @FocusState private var inputFocused: Bool

    init(trip: Trip) {
        self.trip = trip
        _store = StateObject(wrappedValue: ConciergeStore(tripId: trip.id))
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider().opacity(0.5)
            chatList
            confirmationBar
            inputBar
        }
        .background(Color.roammateBackground.ignoresSafeArea())
    }

    // MARK: - Header

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                VStack(alignment: .leading, spacing: 0) {
                    Text("Concierge")
                        .font(.system(.title2, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.roammateInk)
                    Text(trip.name)
                        .font(.system(.caption, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.roammateMuted)
                }
                Spacer()
                Button {
                    HapticManager.light()
                    dismiss()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 26))
                        .foregroundStyle(Color.roammateMuted.opacity(0.7))
                }
                .buttonStyle(.plain)
            }
            QuickActionsBar(
                onMyDay: handleMyDay,
                onWhatsNext: handleWhatsNext,
                onFindNearby: handleFindNearby
            )
            .padding(.horizontal, -RoammateSpacing.md)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.top, RoammateSpacing.sm)
        .padding(.bottom, RoammateSpacing.sm)
    }

    // MARK: - Chat list

    private var chatList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 10) {
                    if store.messages.isEmpty && !store.isThinking {
                        VStack(spacing: 8) {
                            Image(systemName: "sparkles")
                                .font(.system(size: 36))
                                .foregroundStyle(Color.roammateIndigo)
                                .padding(.top, RoammateSpacing.lg)
                            Text("Ask me about your trip")
                                .font(.system(.headline, design: .rounded, weight: .bold))
                                .foregroundStyle(Color.roammateInk)
                            Text("\"Shift everything 30 minutes later\", \"What's nearby for coffee?\", or just chat.")
                                .font(.system(.subheadline, design: .rounded))
                                .foregroundStyle(Color.roammateMuted)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, RoammateSpacing.lg)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.top, RoammateSpacing.xl)
                    }

                    ForEach(store.messages) { msg in
                        ChatMessageBubble(message: msg)
                            .id(msg.id)
                    }

                    if store.isThinking {
                        HStack {
                            ThinkingBubble()
                            Spacer(minLength: 40)
                        }
                        .id("thinking")
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.vertical, RoammateSpacing.sm)
            }
            .onChange(of: store.messages.count) { _, _ in scrollToBottom(proxy) }
            .onChange(of: store.isThinking) { _, _ in scrollToBottom(proxy) }
        }
    }

    private func scrollToBottom(_ proxy: ScrollViewProxy) {
        withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
            if store.isThinking {
                proxy.scrollTo("thinking", anchor: .bottom)
            } else if let last = store.messages.last {
                proxy.scrollTo(last.id, anchor: .bottom)
            }
        }
    }

    // MARK: - Confirmation bar

    @ViewBuilder
    private var confirmationBar: some View {
        if let pending = store.pendingResponse, pending.requiresConfirmation {
            HStack(spacing: RoammateSpacing.sm) {
                Button {
                    Task { _ = await store.confirmPending(); HapticManager.success() }
                } label: { Text("Confirm") }
                .buttonStyle(RoammatePrimaryButtonStyle())

                Button { store.cancelPending() } label: { Text("Nevermind") }
                    .buttonStyle(RoammateSecondaryButtonStyle())
            }
            .padding(.horizontal, RoammateSpacing.md)
            .padding(.bottom, 8)
            .transition(.opacity.combined(with: .move(edge: .bottom)))
        }
    }

    // MARK: - Input

    private var inputBar: some View {
        HStack(spacing: RoammateSpacing.sm) {
            TextField("Ask Roammate…", text: $input, axis: .vertical)
                .lineLimit(1...4)
                .font(.system(.body, design: .rounded))
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                        .fill(Color.roammateSurface)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                        .stroke(Color.roammateBorder, lineWidth: 1)
                )
                .focused($inputFocused)
                .submitLabel(.send)
                .onSubmit(send)

            MicButton(text: $input, recognizer: speech, disabled: store.isThinking)

            Button {
                send()
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 30))
                    .foregroundStyle(input.isEmpty ? Color.roammateMuted : Color.roammateIndigo)
            }
            .disabled(input.isEmpty || store.isThinking)
            .buttonStyle(.plain)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 10)
        .background(.ultraThinMaterial)
    }

    // MARK: - Actions

    private func send() {
        let text = input
        guard !text.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        input = ""
        Task { await store.send(text) }
    }

    private func handleMyDay() {
        Task {
            guard let summary = await store.todaySummary() else { return }
            let line = "Day summary: \(summary.totalEvents) events, \(summary.completed) done, \(summary.upcoming) upcoming."
            await MainActor.run {
                store.messages.append(ChatMessage(role: .assistant, text: line))
            }
        }
    }

    private func handleWhatsNext() {
        Task {
            guard let next = await store.whatsNext() else { return }
            let text: String
            if let t = next.timeUntilNext {
                text = "Next event in \(t)."
            } else {
                text = "Nothing scheduled next."
            }
            await MainActor.run {
                store.messages.append(ChatMessage(role: .assistant, text: text))
            }
        }
    }

    private func handleFindNearby() {
        Task { await store.send("Find something good nearby") }
    }
}
