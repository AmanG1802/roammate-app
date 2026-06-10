import Foundation

enum TutorialStepID: String {
    case dashboard, planTrip, planPreview, tripOverview, timeline
    case brainstormChat, brainstormBin, ideaBin, concierge, wrapUp
}

struct TutorialStep: Identifiable {
    let id: TutorialStepID
    let number: Int    // 1-based, matches backend tutorial_step
    let title: String
    let body: String
    let anchorID: String?
    let tryItLabel: String?
    let tryItAction: TryItAction?
    // Where the popover should sit relative to the screen. `.top` keeps the
    // bottom of the screen visible (chat input + the message that was sent);
    // `.bottom` keeps the highlighted element/list near the top visible.
    let placement: PopoverPlacement
    // When set, the spotlight grows downward from the anchor's top edge to this
    // height — used to wrap a list header plus the first couple of cards.
    var spotlightHeight: CGFloat? = nil
    // When true, the "Try Now" action is the step's primary/forward control:
    // the popover hides the "Next" button and renders Try Now as the filled CTA,
    // because completing the try-it (e.g. the plan demo) advances the tour itself.
    var advanceViaTryIt: Bool = false
    // Overrides the step "Back" jumps to (1-based). Defaults to number - 1.
    var backTo: Int? = nil
}

enum PopoverPlacement {
    case top, bottom, center
}

enum TryItAction {
    case planTripDemo
    case brainstormSendSample
    case conciergeSendSample
}

enum TutorialScript {
    static let steps: [TutorialStep] = [
        .init(id: .dashboard, number: 1,
              title: "Welcome to Roammate",
              body: "Trips you create or join show up here. The tutorial trip is ready to explore.",
              anchorID: "dashboard-trips", tryItLabel: nil, tryItAction: nil,
              placement: .bottom),
        .init(id: .planTrip, number: 2,
              title: "AI-powered trip planning",
              body: "Every trip starts here — give the planner a city or a vibe and it sketches the bones. Tap Try Now to watch it work.",
              anchorID: "new-trip-btn",
              tryItLabel: "Try Now", tryItAction: .planTripDemo,
              placement: .top, advanceViaTryIt: true),
        .init(id: .planPreview, number: 3,
              title: "Your trip preview",
              body: "The planner returns a name, duration, and a set of brainstorm ideas. When you're happy, hit \"Create Trip and Take Me There\".",
              anchorID: nil, tryItLabel: nil, tryItAction: nil,
              placement: .center),
        .init(id: .tripOverview, number: 4,
              title: "Your trip at a glance",
              body: "Members, dates, and a quick summary live here.",
              anchorID: "trip-overview-header", tryItLabel: nil, tryItAction: nil,
              placement: .bottom, backTo: 2),
        .init(id: .brainstormChat, number: 5,
              title: "Brainstorm with AI",
              body: "Chat to discover places. The tutorial uses canned replies — no quota burned.",
              anchorID: "brainstorm-chat-input",
              tryItLabel: "Send a sample message", tryItAction: .brainstormSendSample,
              placement: .top),
        .init(id: .brainstormBin, number: 6,
              title: "Your brainstorm bin",
              body: "Ideas you save from brainstorming land. Tap on any item to view more details. Select and promote the good ones into the shared Idea Bin.",
              anchorID: "brainstorm-bin-list", tryItLabel: nil, tryItAction: nil,
              placement: .bottom, spotlightHeight: 330),
        .init(id: .timeline, number: 7,
              title: "Day-by-day timeline",
              body: "Your itinerary, sorted by day. Conflicts and travel times surface automatically.",
              anchorID: nil, tryItLabel: nil, tryItAction: nil,
              placement: .center),
        .init(id: .ideaBin, number: 8,
              title: "Shared ideas → timeline",
              body: "Promote a shared idea, then refresh the route to see the map redraw.",
              anchorID: nil, tryItLabel: nil, tryItAction: nil,
              placement: .center),
        .init(id: .concierge, number: 9,
              title: "Meet Concierge",
              body: "Your on-trip copilot — normally Plus, but the tour gives you a free taste.",
              anchorID: "concierge-input",
              tryItLabel: "Send a sample message", tryItAction: .conciergeSendSample,
              placement: .top),
        .init(id: .wrapUp, number: 10,
              title: "You're all set",
              body: "That's the tour. Keep the tutorial trip around or remove it now?",
              anchorID: nil, tryItLabel: nil, tryItAction: nil,
              placement: .center),
    ]

    static let total = steps.count

    static func step(for number: Int) -> TutorialStep {
        let clamped = max(1, min(total, number))
        return steps[clamped - 1]
    }

    /// 1-based step number for a step id (used to advance the tour by name).
    static func number(of id: TutorialStepID) -> Int {
        steps.first(where: { $0.id == id })?.number ?? 1
    }

    /// Where the app must be parked for a given step's anchor to resolve. The
    /// navigation-owning views read this to drive the tab / pushed trip /
    /// sub-page / pane *before* the popup is shown (see TutorialCoordinator).
    /// Steps 1–3 (dashboard, plan-trip demo, preview) all live on the dashboard;
    /// the planner runs in a sheet over it.
    static func location(for number: Int) -> TutorialLocation {
        switch number {
        case 1, 2, 3: return .init(openTrip: false, subPage: nil, paneIndex: nil)
        case 4:       return .init(openTrip: true,  subPage: nil, paneIndex: nil)
        case 5:       return .init(openTrip: true,  subPage: .brainstorm, paneIndex: 0)
        case 6:       return .init(openTrip: true,  subPage: .brainstorm, paneIndex: 1)
        case 7:       return .init(openTrip: true,  subPage: .plan, paneIndex: 0)
        case 8:       return .init(openTrip: true,  subPage: .plan, paneIndex: 1)
        default:      return .init(openTrip: true,  subPage: .concierge, paneIndex: nil) // 9 + wrap-up
        }
    }
}

/// The nested navigation state a tutorial step requires.
struct TutorialLocation: Equatable {
    var openTrip: Bool      // push the tutorial trip onto the Dashboard stack
    var subPage: SubPage?   // nil = stay on TripLanding
    var paneIndex: Int?     // 0/1 within the plan or brainstorm pane slider
}

extension Notification.Name {
    /// Posted by the tutorial "Send a sample message" buttons so the live chat
    /// surfaces send + animate the canned exchange.
    static let tutorialBrainstormSend = Notification.Name("tutorialBrainstormSend")
    static let tutorialConciergeSend = Notification.Name("tutorialConciergeSend")
    /// Posted by the tutorial "Try Now" button (Step 2) so the dashboard opens
    /// the Plan-a-trip sheet and runs the canned planning demo.
    static let tutorialStartPlanDemo = Notification.Name("tutorialStartPlanDemo")
}
