import SwiftUI

/// Compact quota indicator for the trip header. Hides for Plus users.
/// At zero remaining, swaps to a danger-toned "Get Plus" chip that opens the paywall.
struct BrainstormQuotaPill: View {
    @EnvironmentObject var subscriptionStore: SubscriptionStore

    var body: some View {
        if let remaining = subscriptionStore.entitlement.brainstormRemaining,
           let cap = subscriptionStore.entitlement.brainstormCap {
            Button {
                if remaining == 0 {
                    NotificationCenter.default.post(
                        name: .needsPlus,
                        object: nil,
                        userInfo: ["feature": PaywallFeature.brainstormQuota.rawValue]
                    )
                }
            } label: {
                HStack(spacing: 4) {
                    Image(systemName: remaining == 0 ? "bolt.fill" : "sparkles")
                        .font(.system(size: 10, weight: .bold))
                    Text(remaining == 0 ? "Get Plus" : "\(remaining)/\(cap)")
                        .font(.caption2.weight(.black))
                        .tracking(0.4)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(Capsule().fill(remaining == 0
                    ? Color(red: 254/255, green: 226/255, blue: 226/255)
                    : Color.roammateIndigoTint))
                .overlay(Capsule().stroke(remaining == 0
                    ? Color.roammateDanger.opacity(0.35)
                    : Color.roammateIndigo.opacity(0.2), lineWidth: 1))
                .foregroundStyle(remaining == 0 ? Color.roammateDanger : Color.roammateIndigo)
            }
            .buttonStyle(.plain)
        }
    }
}

struct BrainstormChatView: View {
    @EnvironmentObject var store: BrainstormStore
    @EnvironmentObject var subscriptionStore: SubscriptionStore
    @Binding var page: Int

    @State private var inputText = ""
    @StateObject private var speech = SpeechRecognizer()

    /// True when the user has run out of free brainstorms. Plus users have
    /// `brainstormRemaining == nil` (unlimited), so this stays false for them.
    private var isQuotaExhausted: Bool {
        subscriptionStore.entitlement.brainstormRemaining == 0
    }

    private let suggestedPrompts = [
        "Best restaurants in the area",
        "Must-see attractions",
        "Hidden gems off the beaten path",
        "Activities for a rainy day",
    ]

    var body: some View {
        VStack(spacing: 0) {
            if store.messages.isEmpty && !store.isSending {
                emptyState
            } else {
                messageList
            }

            if store.messages.count >= 2 && !isQuotaExhausted {
                extractButton
            }

            inputBar
                .tutorialAnchor("brainstorm-chat-input")
        }
        .background(
            LinearGradient(
                colors: [Color.roammateBackground, Color.roammateIndigoTint.opacity(0.3)],
                startPoint: .top,
                endPoint: .bottom
            )
        )
        .onReceive(NotificationCenter.default.publisher(for: .tutorialBrainstormSend)) { note in
            guard let text = note.userInfo?["message"] as? String, !store.isSending else { return }
            Task {
                await store.send(text)
                await subscriptionStore.refresh()
            }
        }
    }

    // MARK: - Empty State

    private var emptyState: some View {
        ScrollView {
            VStack(spacing: RoammateSpacing.lg) {
                Spacer().frame(height: 40)

                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                colors: [Color.roammateIndigo.opacity(0.15), Color.roammateViolet.opacity(0.1)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 80, height: 80)
                    Image(systemName: "sparkles")
                        .font(.system(size: 32, weight: .semibold))
                        .foregroundStyle(Color.roammateIndigo)
                }

                VStack(spacing: 6) {
                    Text("Start brainstorming")
                        .font(.system(.title3, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.roammateInk)
                    Text("Chat with AI to discover ideas for your trip")
                        .font(.system(.subheadline, design: .rounded))
                        .foregroundStyle(Color.roammateMuted)
                        .multilineTextAlignment(.center)
                }

                VStack(spacing: RoammateSpacing.sm) {
                    Text("Try asking")
                        .font(.system(.caption, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.roammateMuted)

                    FlowLayoutView {
                        ForEach(suggestedPrompts, id: \.self) { prompt in
                            Button {
                                inputText = prompt
                            } label: {
                                Text(prompt)
                                    .font(.system(.caption, design: .rounded, weight: .medium))
                                    .foregroundStyle(Color.roammateIndigo)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 8)
                                    .background(
                                        Capsule()
                                            .fill(Color.roammateIndigoTint)
                                    )
                                    .overlay(
                                        Capsule()
                                            .stroke(Color.roammateIndigo.opacity(0.2), lineWidth: 1)
                                    )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.horizontal, RoammateSpacing.lg)
                }

                Spacer()
            }
            .frame(maxWidth: .infinity)
        }
    }

    // MARK: - Message List

    private var messageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: RoammateSpacing.sm) {
                    ForEach(store.messages) { message in
                        VStack(spacing: 2) {
                            BrainstormMessageBubble(message: message)
                            if let date = message.createdAt {
                                Text(timeString(date))
                                    .font(.system(.caption2, design: .rounded))
                                    .foregroundStyle(Color.roammateMuted.opacity(0.6))
                                    .frame(
                                        maxWidth: .infinity,
                                        alignment: message.role == "user" ? .trailing : .leading
                                    )
                                    .padding(.horizontal, message.role == "user" ? 4 : 40)
                            }
                        }
                        .id(message.id)
                    }

                    if store.isSending {
                        typingIndicator
                            .id("typing")
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.vertical, RoammateSpacing.sm)
            }
            .onChange(of: store.messages.count) { _, _ in
                withAnimation {
                    if let last = store.messages.last {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
            .onChange(of: store.isSending) { _, sending in
                if sending {
                    withAnimation {
                        proxy.scrollTo("typing", anchor: .bottom)
                    }
                }
            }
        }
    }

    private var typingIndicator: some View {
        HStack {
            HStack(spacing: 4) {
                Image(systemName: "ellipsis")
                    .font(.system(size: 20, weight: .medium))
                    .foregroundStyle(Color.roammateMuted)
                    .symbolEffect(.variableColor.iterative)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(Color.roammateSurface)
            )

            Spacer()
        }
    }

    // MARK: - Extract Button

    private var extractButton: some View {
        Button {
            Task {
                let count = await store.extract()
                if count > 0 {
                    HapticManager.success()
                    withAnimation(.spring(.bouncy)) {
                        page = 1
                    }
                }
            }
        } label: {
            HStack(spacing: 8) {
                if store.isExtracting {
                    ProgressView()
                        .scaleEffect(0.8)
                        .tint(.white)
                } else {
                    Image(systemName: "sparkles")
                        .font(.system(size: 14, weight: .bold))
                        .symbolEffect(.pulse)
                }
                Text("Extract ideas from chat")
                    .font(.system(.subheadline, design: .rounded, weight: .heavy))
            }
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(
                LinearGradient(
                    colors: [Color.roammateIndigo, Color.roammateViolet],
                    startPoint: .leading,
                    endPoint: .trailing
                ),
                in: Capsule()
            )
            .shadow(color: Color.roammateIndigo.opacity(0.25), radius: 8, y: 2)
            .opacity(store.isExtracting ? 0.7 : 1)
        }
        .buttonStyle(.plain)
        .disabled(store.isExtracting)
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.top, 4)
        .padding(.bottom, 8)
    }

    // MARK: - Input Bar

    private func openPaywall() {
        NotificationCenter.default.post(
            name: .needsPlus,
            object: nil,
            userInfo: ["feature": PaywallFeature.brainstormQuota.rawValue]
        )
    }

    private var inputBar: some View {
        HStack(spacing: RoammateSpacing.sm) {
            TextField(
                isQuotaExhausted ? "Out of free brainstorms" : "Type something…",
                text: $inputText,
                axis: .vertical
            )
            .font(.system(.body, design: .rounded))
            .lineLimit(1...4)
            .disabled(isQuotaExhausted)
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(isQuotaExhausted ? Color.roammateBackground : Color.roammateSurface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .stroke(Color.roammateBorder, lineWidth: 1)
            )

            if !isQuotaExhausted {
                MicButton(text: $inputText, recognizer: speech, disabled: store.isSending)
            }

            Button {
                if isQuotaExhausted {
                    HapticManager.light()
                    openPaywall()
                    return
                }
                let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
                inputText = ""
                Task {
                    await store.send(text)
                    // Counter ticked up on the server — refresh entitlement so
                    // the header pill reflects it. (On a 402 the APIClient
                    // has already broadcast .needsPlus; the paywall will open
                    // and entitlement is refreshed on subscribe success.)
                    await subscriptionStore.refresh()
                }
            } label: {
                ZStack {
                    Circle()
                        .fill(
                            isQuotaExhausted
                                ? Color.roammateDanger
                                : (canSend
                                    ? Color.roammateIndigo
                                    : Color.roammateMuted.opacity(0.3))
                        )
                        .frame(width: 36, height: 36)
                    Image(systemName: isQuotaExhausted ? "lock.fill" : "arrow.up")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(.white)
                }
            }
            .buttonStyle(.plain)
            .disabled(!isQuotaExhausted && !canSend)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, RoammateSpacing.sm)
        .background(
            Color.roammateSurface
                .shadow(.drop(color: .black.opacity(0.06), radius: 8, y: -4))
        )
    }

    private var canSend: Bool {
        !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !store.isSending
    }

    private func timeString(_ date: Date) -> String {
        let fmt = DateFormatter()
        fmt.dateFormat = "h:mm a"
        return fmt.string(from: date)
    }
}

// Simple flow layout for suggested prompts
private struct FlowLayoutView<Content: View>: View {
    @ViewBuilder let content: () -> Content

    var body: some View {
        content()
            .fixedSize(horizontal: true, vertical: false)
    }
}
