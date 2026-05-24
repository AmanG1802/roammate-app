import SwiftUI

/// Wraps the app shell to render the tutorial overlay over every screen.
/// Mount this once at MainShell level — it consumes anchor publications from
/// `tutorialAnchor(_:)` modifiers placed deep in the view tree.
struct TutorialCoordinator<Content: View>: View {
    @EnvironmentObject var tutorial: TutorialStore
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
            .task {
                await tutorial.loadStatus()
                evaluateWelcome()
            }
            .onChange(of: tutorial.status) { _, _ in evaluateWelcome() }
            .sheet(isPresented: $welcomeOpen) {
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
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
            }
            .sheet(isPresented: $finishPromptOpen) {
                FinishPrompt(
                    onDelete: {
                        Task {
                            await tutorial.deleteTutorialTrip()
                            finishPromptOpen = false
                        }
                    },
                    onKeep: { finishPromptOpen = false }
                )
                .presentationDetents([.fraction(0.32)])
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
        welcomeOpen = (tutorial.status == .notStarted)
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
