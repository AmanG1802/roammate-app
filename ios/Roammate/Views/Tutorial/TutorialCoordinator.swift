import SwiftUI

/// Wraps the app shell to render the tutorial overlay over every screen.
/// Mount this once at MainShell level — it consumes anchor publications from
/// `tutorialAnchor(_:)` modifiers placed deep in the view tree.
struct TutorialCoordinator<Content: View>: View {
    @EnvironmentObject var tutorial: TutorialStore
    @EnvironmentObject var tripStore: TripStore
    @State private var welcomeOpen = false
    @State private var finishPromptOpen = false
    @State private var tryItLoading = false
    let content: () -> Content

    init(@ViewBuilder content: @escaping () -> Content) {
        self.content = content
    }

    var body: some View {
        content()
            .overlayPreferenceValue(TutorialAnchorKey.self) { anchors in
                GeometryReader { geo in
                    overlayBody(anchors: anchors, geo: geo)
                }
            }
            .overlay {
                if welcomeOpen {
                    ZStack {
                        Color.black.opacity(0.45)
                            .ignoresSafeArea()
                            .onTapGesture { } // absorb taps — not dismissible by tapping outside
                        WelcomeSheet(
                            onStart: {
                                Task {
                                    await tutorial.start()
                                    welcomeOpen = false
                                }
                            },
                            onSkip: {
                                Task {
                                    await tutorial.skip()
                                    welcomeOpen = false
                                }
                            }
                        )
                    }
                    .transition(.opacity.combined(with: .scale(scale: 0.96)))
                }
            }
            .animation(.spring(response: 0.35, dampingFraction: 0.88), value: welcomeOpen)
            .task {
                await tutorial.loadStatus()
                evaluateWelcome()
            }
            .onChange(of: tutorial.status) { _, _ in evaluateWelcome() }
            .sheet(isPresented: $finishPromptOpen) {
                FinishPrompt(
                    onDelete: {
                        // Optimistically drop the seeded trip from the list so
                        // the dashboard updates instantly, delete it server-side,
                        // then reconcile against the DB.
                        let id = tutorial.tutorialTripId
                        if let id { tripStore.removeLocally(id: id) }
                        Task {
                            await tutorial.deleteTutorialTrip()
                            await tripStore.load()
                            finishPromptOpen = false
                        }
                    },
                    onKeep: { finishPromptOpen = false }
                )
                .presentationDetents([.fraction(0.32)])
                .presentationBackground(Color.roammateSurface)
            }
    }

    @ViewBuilder
    private func overlayBody(anchors: [String: Anchor<CGRect>], geo: GeometryProxy) -> some View {
        if tutorial.status == .inProgress {
            let step = TutorialScript.step(for: tutorial.currentStep)
            let isLast = step.number >= TutorialScript.total
            SpotlightOverlay(
                anchors: anchors,
                geometry: geo,
                step: step,
                isLast: isLast,
                onNext: { Task { await advance(from: step, isLast: isLast) } },
                onPrev: { Task { await tutorial.advance(to: max(1, step.backTo ?? step.number - 1)) } },
                onSkip: { Task { await tutorial.skip() } },
                onTryIt: step.tryItAction.map { action in
                    { Task { await runTryIt(action) } }
                },
                tryItLoading: tryItLoading
            )
            .transition(.opacity)
        }
    }

    private func evaluateWelcome() {
        guard !tutorial.isLoading else { return }
        if tutorial.status == .notStarted {
            // Delay so the tab-switch animation to Dashboard (triggered by the
            // same status change in MainShell, 180ms easeInOut) completes before
            // the Welcome overlay fades in.
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
                guard tutorial.status == .notStarted else { return }
                welcomeOpen = true
            }
        } else {
            welcomeOpen = false
        }
    }

    private func advance(from step: TutorialStep, isLast: Bool) async {
        if isLast {
            await tutorial.complete()
            finishPromptOpen = true
        } else {
            await tutorial.advance(to: step.number + 1)
        }
    }

    private func runTryIt(_ action: TryItAction) async {
        switch action {
        case .planTripDemo:
            // Ask the dashboard to open the planner sheet and run the canned
            // demo. The drawer advances the tour to the preview step itself.
            // The demo is fully canned and creates nothing, so it must run even
            // if the seeded trip id hasn't loaded yet — gating it on
            // `tutorialTripId` was why "Try Now" sometimes did nothing.
            NotificationCenter.default.post(name: .tutorialStartPlanDemo, object: nil)
        case .brainstormSendSample:
            // The sample-message try-its act on the live tutorial trip, so they
            // do require the seeded trip to exist.
            guard tutorial.tutorialTripId != nil else { return }
            NotificationCenter.default.post(
                name: .tutorialBrainstormSend,
                object: nil,
                userInfo: ["message": "What about a rainy-day plan for Day 2?"]
            )
        case .conciergeSendSample:
            guard tutorial.tutorialTripId != nil else { return }
            NotificationCenter.default.post(
                name: .tutorialConciergeSend,
                object: nil,
                userInfo: ["message": "What is the move tonight?"]
            )
        }
    }
}

private struct FinishPrompt: View {
    var onDelete: () -> Void
    var onKeep: () -> Void
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Tour complete")
                .font(.title3.weight(.semibold))
                .foregroundColor(.roammateInk)
            Text("Remove the tutorial trip now, or keep it around for later? You can always replay the tour from your profile.")
                .font(.subheadline)
                .foregroundColor(.roammateMuted)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
            HStack {
                Button("Keep for now", action: onKeep)
                    .foregroundColor(.roammateInk)
                Spacer()
                Button(action: onDelete) {
                    Label("Delete tutorial trip", systemImage: "trash")
                        .font(.subheadline.weight(.semibold))
                        .foregroundColor(.white)
                        .padding(.horizontal, 14).padding(.vertical, 9)
                        .background(Color.roammateDanger, in: RoundedRectangle(cornerRadius: 12))
                }
            }
        }
        .padding(22)
    }
}
