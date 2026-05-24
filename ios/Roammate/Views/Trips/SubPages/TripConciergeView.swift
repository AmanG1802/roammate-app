import SwiftUI

/// Minimum-viable Concierge chat — list + input bar wired to /concierge/{id}/chat.
/// During the tutorial, the backend short-circuits to canned replies, so the
/// surface is fully functional without Plus and without burning quota.
struct TripConciergeView: View {
    let trip: Trip

    @State private var messages: [ConciergeChatTurn] = [
        ConciergeChatTurn(
            role: .assistant,
            text: "Hey — I'm your on-trip Concierge. Ask me about reroutes, recommendations, or running late."
        )
    ]
    @State private var input: String = ""
    @State private var sending = false
    @State private var errorText: String? = nil

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(messages) { m in
                            ConciergeBubble(turn: m)
                                .id(m.id)
                        }
                        if sending {
                            HStack(spacing: 6) {
                                ProgressView().scaleEffect(0.7)
                                Text("Thinking…")
                                    .font(.caption)
                                    .foregroundColor(.roammateMuted)
                            }
                            .padding(.leading, 12)
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 18)
                }
                .onChange(of: messages.count) { _, _ in
                    if let last = messages.last {
                        withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                    }
                }
            }
            Divider()
            inputBar
                .tutorialAnchor("concierge-input")
        }
        .background(Color.roammateBackground.ignoresSafeArea())
        .navigationTitle("Concierge")
        .navigationBarTitleDisplayMode(.inline)
        .onReceive(NotificationCenter.default.publisher(for: .tutorialConciergeSend)) { note in
            guard let text = note.userInfo?["message"] as? String else { return }
            send(preset: text)
        }
    }

    private var inputBar: some View {
        HStack(spacing: 10) {
            TextField("Ask Concierge…", text: $input, axis: .vertical)
                .lineLimit(1...4)
                .padding(.horizontal, 14).padding(.vertical, 10)
                .background(Color.roammateSurface, in: RoundedRectangle(cornerRadius: 14))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Color.roammateBorder, lineWidth: 1)
                )

            Button(action: { send() }) {
                Image(systemName: "arrow.up")
                    .font(.subheadline.weight(.bold))
                    .foregroundColor(.white)
                    .frame(width: 40, height: 40)
                    .background(Color.roammateIndigo, in: Circle())
            }
            .disabled(input.trimmingCharacters(in: .whitespaces).isEmpty || sending)
        }
        .padding(.horizontal, 14).padding(.vertical, 10)
        .background(Color.roammateSurface)
    }

    private func send(preset: String? = nil) {
        let trimmed = (preset ?? input).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !sending else { return }
        if preset == nil { input = "" }
        messages.append(ConciergeChatTurn(role: .user, text: trimmed))
        sending = true
        Task {
            defer { sending = false }
            do {
                let resp = try await ConciergeService.chat(tripId: trip.id, message: trimmed)
                messages.append(ConciergeChatTurn(role: .assistant, text: resp.userMessage))
            } catch {
                errorText = (error as? APIError)?.errorDescription ?? error.localizedDescription
                messages.append(ConciergeChatTurn(
                    role: .assistant,
                    text: errorText ?? "Sorry, I couldn't reach Concierge right now."
                ))
            }
        }
    }
}

struct ConciergeChatTurn: Identifiable, Hashable {
    let id = UUID()
    let role: Role
    let text: String
    enum Role { case user, assistant }
}

private struct ConciergeBubble: View {
    let turn: ConciergeChatTurn

    var body: some View {
        HStack {
            if turn.role == .user { Spacer(minLength: 40) }
            Text(turn.text)
                .font(.subheadline)
                .foregroundColor(turn.role == .user ? .white : .roammateInk)
                .padding(.horizontal, 14).padding(.vertical, 10)
                .background(
                    turn.role == .user ? Color.roammateIndigo : Color.roammateSurface,
                    in: RoundedRectangle(cornerRadius: 16)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(turn.role == .assistant ? Color.roammateBorder : Color.clear, lineWidth: 1)
                )
            if turn.role == .assistant { Spacer(minLength: 40) }
        }
    }
}
