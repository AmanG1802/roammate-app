import SwiftUI

struct PlanTripDrawer: View {
    /// Fires after a successful POST /trips. Caller is expected to push the
    /// new trip onto its NavigationStack (Trip Landing View).
    let onTripCreated: (Trip) -> Void
    /// Tutorial: run the canned planning demo (typewriter prompt → preview)
    /// instead of waiting for real input.
    var demoMode: Bool = false
    /// Called once the canned preview appears (advances the tour to step 3).
    var onDemoPreviewShown: (() -> Void)? = nil
    /// Called when the user taps "Create Trip and Take Me There" in demo mode.
    var onDemoCreate: (() -> Void)? = nil

    @StateObject private var store = PlanTripStore()
    @StateObject private var speech = SpeechRecognizer()
    @Environment(\.dismiss) private var dismiss
    @FocusState private var promptFocused: Bool
    @State private var wittyIndex = 0
    @State private var wittyTimer: Task<Void, Never>?
    @State private var demoStarted = false

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider().opacity(0.3)

            chatSection
                .frame(maxWidth: .infinity, maxHeight: .infinity)

            inputArea
        }
        .background(Color.roammateBackground.ignoresSafeArea())
        .onAppear { if !demoMode { promptFocused = true } }
        .onChange(of: demoMode, initial: true) { _, newValue in
            // Start the demo exactly once — the guard prevents re-entry if demoMode
            // briefly toggles (e.g. step advances from planTrip → planPreview while
            // the sheet is still open).
            guard newValue, !demoStarted else { return }
            demoStarted = true
            Task {
                await store.runTutorialDemo()
                onDemoPreviewShown?()
            }
        }
        .onDisappear { wittyTimer?.cancel() }
        .onChange(of: store.phase) { _, newPhase in
            if newPhase == .planning { startWittyRotation() }
            else { wittyTimer?.cancel() }
        }
    }

    // MARK: - Header

    private var header: some View {
        ZStack {
            Text("Plan a new trip")
                .font(.system(.title3, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateInk)

            HStack {
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
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.top, 12)
        .padding(.bottom, 12)
    }

    // MARK: - Chat Section

    private var chatSection: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(spacing: RoammateSpacing.sm) {
                    if store.messages.isEmpty && store.phase == .idle {
                        placeholderView
                    }

                    ForEach(store.messages) { msg in
                        chatBubble(msg)
                            .id(msg.id)
                    }

                    if store.phase == .planning {
                        planningBanner
                            .id("planning-banner")
                            .transition(.opacity.combined(with: .move(edge: .bottom)))
                    }

                    if store.phase == .previewing || store.phase == .creating,
                       let preview = store.preview {
                        previewCard(preview)
                            .id("preview-card")
                            .transition(.opacity.combined(with: .scale(scale: 0.95)))
                    }

                    if let error = store.error {
                        Text(error)
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(Color.roammateDanger)
                            .padding(.horizontal, RoammateSpacing.md)
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.vertical, RoammateSpacing.md)
            }
            .onChange(of: store.messages.count) { _, _ in
                withAnimation {
                    if let last = store.messages.last {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
            .onChange(of: store.phase) { _, phase in
                withAnimation {
                    if phase == .planning {
                        proxy.scrollTo("planning-banner", anchor: .bottom)
                    } else if phase == .previewing {
                        proxy.scrollTo("preview-card", anchor: .bottom)
                    }
                }
            }
        }
    }

    private var placeholderView: some View {
        VStack(spacing: RoammateSpacing.md) {
            Spacer().frame(height: 60)
            ZStack {
                Circle()
                    .fill(Color.roammateIndigoTint)
                    .frame(width: 72, height: 72)
                Image(systemName: "sparkles")
                    .font(.system(size: 28, weight: .semibold))
                    .foregroundStyle(Color.roammateIndigo)
            }
            Text("AI turns your prompts\ninto crafted trips")
                .font(.system(.title3, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.roammateMuted)
                .multilineTextAlignment(.center)
            Spacer().frame(height: 60)
        }
        .frame(maxWidth: .infinity)
    }

    private func chatBubble(_ message: PlanTripMessage) -> some View {
        HStack {
            if message.role == "user" { Spacer(minLength: 48) }

            Group {
                if message.role == "assistant",
                   let attributed = try? AttributedString(
                    markdown: message.text,
                    options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)
                   ) {
                    Text(attributed)
                } else {
                    Text(message.text)
                }
            }
                .font(.system(.body, design: .rounded))
                .foregroundStyle(message.role == "user" ? .white : Color.roammateInk)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(
                    Group {
                        if message.role == "user" {
                            UnevenRoundedRectangle(
                                topLeadingRadius: 18,
                                bottomLeadingRadius: 18,
                                bottomTrailingRadius: 6,
                                topTrailingRadius: 18
                            )
                            .fill(
                                LinearGradient(
                                    colors: [Color.roammateIndigo, Color.roammateIndigoDark],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                        } else {
                            UnevenRoundedRectangle(
                                topLeadingRadius: 18,
                                bottomLeadingRadius: 6,
                                bottomTrailingRadius: 18,
                                topTrailingRadius: 18
                            )
                            .fill(Color.roammateSurface)
                            .overlay(
                                UnevenRoundedRectangle(
                                    topLeadingRadius: 18,
                                    bottomLeadingRadius: 6,
                                    bottomTrailingRadius: 18,
                                    topTrailingRadius: 18
                                )
                                .stroke(Color.roammateBorder, lineWidth: 0.5)
                            )
                        }
                    }
                )

            if message.role != "user" { Spacer(minLength: 48) }
        }
    }

    // MARK: - Planning Banner

    private var planningBanner: some View {
        VStack(spacing: RoammateSpacing.sm) {
            ZStack {
                Circle()
                    .fill(Color.roammateIndigoTint)
                    .frame(width: 56, height: 56)
                Image(systemName: "sparkles")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(Color.roammateIndigo)
                    .symbolEffect(.pulse)
            }

            Text("Planning your trip")
                .font(.system(.subheadline, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateInk)

            Text(store.wittyMessages[wittyIndex])
                .font(.system(.caption, design: .rounded))
                .foregroundStyle(Color.roammateMuted)
                .multilineTextAlignment(.center)
                .transition(.opacity)
                .id(wittyIndex)
                .animation(.easeInOut(duration: 0.4), value: wittyIndex)
        }
        .padding(.vertical, RoammateSpacing.md)
        .padding(.horizontal, RoammateSpacing.lg)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                .fill(Color.roammateIndigoTint.opacity(0.5))
        )
    }

    private func startWittyRotation() {
        wittyTimer?.cancel()
        wittyIndex = 0
        wittyTimer = Task { @MainActor in
            while !Task.isCancelled, store.phase == .planning {
                try? await Task.sleep(nanoseconds: 3_000_000_000)
                guard !Task.isCancelled, store.phase == .planning else { return }
                withAnimation(.easeInOut(duration: 0.4)) {
                    wittyIndex = (wittyIndex + 1) % store.wittyMessages.count
                }
            }
        }
    }

    // MARK: - Preview Card

    private func previewCard(_ preview: PlanTripPreview) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(preview.tripName)
                .font(.system(.title3, design: .rounded, weight: .black))
                .foregroundStyle(Color.roammateInk)

            HStack(spacing: 8) {
                Label(
                    "\(preview.durationDays) day\(preview.durationDays == 1 ? "" : "s")",
                    systemImage: "calendar"
                )
                .font(.system(.caption, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.roammateIndigo)
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(Capsule().fill(Color.roammateIndigoTint))

                Label(
                    "\(preview.items.count) brainstorm ideas",
                    systemImage: "lightbulb.fill"
                )
                .font(.system(.caption, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.roammateAmber)
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(Capsule().fill(Color.roammateAmberTint))
            }

            if !preview.items.isEmpty {
                Divider().padding(.vertical, 4)
                ForEach(preview.items.prefix(3)) { item in
                    HStack(spacing: 8) {
                        Image(systemName: "mappin.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(Color.categoryColor(item.category))
                        Text(item.title)
                            .font(.system(.caption, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.roammateInk)
                            .lineLimit(1)
                    }
                }
                if preview.items.count > 3 {
                    Text("+ \(preview.items.count - 3) more ideas")
                        .font(.system(.caption2, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.roammateMuted)
                }
            }
        }
        .padding(RoammateSpacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                .fill(Color.roammateSurface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: RoammateRadius.button, style: .continuous)
                .stroke(Color.roammateIndigo.opacity(0.3), lineWidth: 1)
        )
    }

    // MARK: - Tutorial Hint

    /// Inline guidance shown during the tutorial demo (Step 3). The system sheet
    /// covers the spotlight overlay, so the preview step's guidance lives here.
    private var tutorialPreviewHint: some View {
        HStack(spacing: 8) {
            Image(systemName: "sparkles")
                .font(.caption.bold())
                .foregroundStyle(Color.roammateIndigo)
            Text("Your trip preview is ready — tap **Create Trip and Take Me There** to continue the tour.")
                .font(.system(.caption, design: .rounded))
                .foregroundStyle(Color.roammateInk)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Color.roammateIndigoTint)
        )
        .transition(.opacity)
    }

    // MARK: - Input Area

    private var inputArea: some View {
        VStack(spacing: RoammateSpacing.sm) {
            HStack(spacing: RoammateSpacing.sm) {
                TextField(
                    store.messages.isEmpty
                        ? "e.g. A 5-day food + culture trip in Tokyo…"
                        : "Refine your trip idea…",
                    text: $store.prompt,
                    axis: .vertical
                )
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
                .focused($promptFocused)
                // Demo: show the typewriter prompt but block user editing.
                .disabled(demoMode)
                .allowsHitTesting(!demoMode)

                if !demoMode {
                    MicButton(
                        text: $store.prompt,
                        recognizer: speech,
                        disabled: store.phase == .planning || store.phase == .creating
                    )
                }

                if (store.phase == .previewing || store.phase == .creating) && !demoMode {
                    Button {
                        HapticManager.light()
                        Task { await store.plan() }
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 36))
                            .foregroundStyle(
                                store.prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                                    ? Color.roammateMuted
                                    : Color.roammateIndigo
                            )
                    }
                    .buttonStyle(.plain)
                    .disabled(store.prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }

            if demoMode, store.phase == .previewing {
                tutorialPreviewHint
            }

            bottomButton
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, RoammateSpacing.sm)
        .background(Color.roammateSurface.ignoresSafeArea(edges: .bottom))
        .shadow(color: .black.opacity(0.06), radius: 8, y: -4)
    }

    @ViewBuilder
    private var bottomButton: some View {
        let hasNoText = store.prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty

        switch store.phase {
        case .idle:
            Button {
                Task { await store.plan() }
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "sparkles")
                    Text("Plan")
                }
            }
            .buttonStyle(RoammatePrimaryButtonStyle())
            .disabled(hasNoText && store.messages.isEmpty)

        case .planning:
            Button {} label: {
                HStack(spacing: 8) {
                    ProgressView().tint(.white)
                    Text("Planning…")
                }
            }
            .buttonStyle(RoammatePrimaryButtonStyle(isLoading: true))
            .disabled(true)

        case .previewing:
            Button {
                if demoMode {
                    // Tutorial: don't POST — hand back to the dashboard, which
                    // navigates to the already-seeded trip and advances the tour.
                    HapticManager.success()
                    onDemoCreate?()
                    return
                }
                Task {
                    if let created = await store.createTrip() {
                        dismiss()
                        // Give the sheet a moment to dismiss before pushing
                        // the landing view onto the parent's NavigationStack.
                        try? await Task.sleep(nanoseconds: 200_000_000)
                        onTripCreated(created)
                    }
                }
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "plus.circle.fill")
                    Text(demoMode ? "Create Trip and Take Me There" : "Create Trip")
                }
            }
            .buttonStyle(RoammatePrimaryButtonStyle())

        case .creating:
            Button {} label: {
                HStack(spacing: 8) {
                    ProgressView().tint(.white)
                    Text("Creating…")
                }
            }
            .buttonStyle(RoammatePrimaryButtonStyle(isLoading: true))
            .disabled(true)
        }
    }
}
