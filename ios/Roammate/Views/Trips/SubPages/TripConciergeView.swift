import SwiftUI
import CoreLocation

/// Chat-first Concierge surface. The AI chat is home base; Map and Timeline are
/// full-screen destinations reached from the host top bar (pin / timeline
/// icons) via `ConciergeStore.detail`. Quick-action chips above the input cover
/// the web `ConciergeActionBar` (running late, skip next, find nearby) plus the
/// live data queries (my day, what's next).
///
/// Day-of only + admin-gated to mirror the web behaviour. The tutorial hooks
/// (`concierge-input` anchor + `.tutorialConciergeSend`) are preserved.
struct TripConciergeView: View {
    let trip: Trip

    @EnvironmentObject var store: ConciergeStore
    @EnvironmentObject var detailStore: TripDetailStore
    @EnvironmentObject var subscriptionStore: SubscriptionStore
    @EnvironmentObject var authManager: AuthManager

    @State private var inputText = ""
    @StateObject private var speech = SpeechRecognizer()

    private var isAdmin: Bool {
        if trip.myRole == "admin" { return true }
        guard let uid = authManager.currentUser?.id else { return false }
        return detailStore.members.first(where: { $0.userId == uid })?.role == "admin"
    }

    private var canUseConcierge: Bool { subscriptionStore.entitlement.canUseConcierge }

    var body: some View {
        Group {
            if isAdmin {
                chat
            } else {
                lockedState
            }
        }
        .background(Color.roammateBackground.ignoresSafeArea())
        .fullScreenCover(item: $store.detail) { detail in
            ConciergeDetailView(initial: detail)
                .environmentObject(store)
                .environmentObject(detailStore)
        }
        .onReceive(NotificationCenter.default.publisher(for: .tutorialConciergeSend)) { note in
            guard let text = note.userInfo?["message"] as? String else { return }
            Task { await store.send(text) }
        }
        .onAppear { primeFallbackCoordinate() }
    }

    // MARK: - Chat

    private var chat: some View {
        VStack(spacing: 0) {
            if let banner = store.availabilityBanner {
                availabilityBanner(banner)
            }
            if !canUseConcierge {
                plusBanner
            }
            messageList
            chipRow
            inputBar
                .tutorialAnchor("concierge-input")
        }
    }

    private var messageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: RoammateSpacing.sm) {
                    ForEach(store.messages) { message in
                        ConciergeMessageView(message: message)
                            .environmentObject(store)
                            .id(message.id)
                    }
                    if store.isThinking {
                        typingIndicator.id("typing")
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
                .padding(.vertical, RoammateSpacing.sm)
            }
            .onChange(of: store.messages.count) { _, _ in
                withAnimation { proxy.scrollTo(store.messages.last?.id, anchor: .bottom) }
            }
            .onChange(of: store.isThinking) { _, thinking in
                if thinking { withAnimation { proxy.scrollTo("typing", anchor: .bottom) } }
            }
        }
    }

    private var typingIndicator: some View {
        HStack {
            Image(systemName: "ellipsis")
                .font(.system(size: 20, weight: .medium))
                .foregroundStyle(Color.roammateMuted)
                .symbolEffect(.variableColor.iterative)
                .padding(.horizontal, 16).padding(.vertical, 12)
                .background(Color.roammateSurface, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
            Spacer()
        }
    }

    // MARK: - Quick-action chips

    private var chipRow: some View {
        VStack(spacing: 8) {
            // Query / discovery actions.
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    chip("My day", "calendar") { Task { await store.todaySummary() } }
                    chip("What's next?", "arrow.right.circle") { Task { await store.whatsNext() } }
                    chip("Find nearby", "cup.and.saucer") {
                        requirePlus { Task { await store.findNearby(query: "coffee", category: "Food & Dining") } }
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
            }

            // Dedicated row: time-sensitive itinerary actions.
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    Menu {
                        Button("15 minutes") { runningLate(15) }
                        Button("30 minutes") { runningLate(30) }
                        Button("1 hour") { runningLate(60) }
                    } label: {
                        chipLabel("Running late", "clock.arrow.circlepath")
                    }
                    .disabled(!store.isLiveDay || store.isThinking)
                    .opacity(store.isLiveDay ? 1 : 0.5)

                    chip("Skip next", "forward.end") {
                        requirePlus { Task { await store.skipNext() } }
                    }
                }
                .padding(.horizontal, RoammateSpacing.md)
            }
        }
        .padding(.vertical, 8)
        .background(Color.roammateBackground)
    }

    private func chip(_ title: String, _ icon: String, action: @escaping () -> Void) -> some View {
        Button {
            HapticManager.light()
            action()
        } label: {
            chipLabel(title, icon)
        }
        .buttonStyle(.plain)
        .disabled(!store.isLiveDay || store.isThinking)
        .opacity(store.isLiveDay ? 1 : 0.5)
    }

    private func chipLabel(_ title: String, _ icon: String) -> some View {
        HStack(spacing: 5) {
            Image(systemName: icon).font(.system(size: 12, weight: .bold))
            Text(title).font(.system(.footnote, design: .rounded, weight: .heavy))
        }
        .foregroundStyle(Color.roammateIndigo)
        .padding(.horizontal, 12).padding(.vertical, 8)
        .background(Color.roammateIndigoTint, in: Capsule())
        .overlay(Capsule().stroke(Color.roammateIndigo.opacity(0.2), lineWidth: 1))
    }

    // MARK: - Input bar

    private var inputBar: some View {
        HStack(spacing: RoammateSpacing.sm) {
            TextField("Ask anything about your trip…", text: $inputText, axis: .vertical)
                .font(.system(.body, design: .rounded))
                .lineLimit(1...4)
                .padding(.horizontal, 14).padding(.vertical, 10)
                .background(Color.roammateSurface, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 22, style: .continuous).stroke(Color.roammateBorder, lineWidth: 1))

            MicButton(text: $inputText, recognizer: speech, disabled: store.isThinking)

            Button {
                let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
                inputText = ""
                Task { await store.send(text) }
            } label: {
                ZStack {
                    Circle()
                        .fill(canSend ? Color.roammateIndigo : Color.roammateMuted.opacity(0.3))
                        .frame(width: 36, height: 36)
                    Image(systemName: "arrow.up")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(.white)
                }
            }
            .buttonStyle(.plain)
            .disabled(!canSend)
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, RoammateSpacing.sm)
        .background(Color.roammateSurface.shadow(.drop(color: .black.opacity(0.06), radius: 8, y: -4)))
    }

    private var canSend: Bool {
        !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !store.isThinking
    }

    // MARK: - Banners & locked state

    private func availabilityBanner(_ text: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: "moon.zzz.fill").font(.system(size: 12, weight: .bold))
            Text(text).font(.system(.caption, design: .rounded, weight: .semibold))
            Spacer(minLength: 0)
        }
        .foregroundStyle(Color.roammateMuted)
        .padding(.horizontal, RoammateSpacing.md).padding(.vertical, 8)
        .background(Color.roammateBackground)
    }

    private var plusBanner: some View {
        Button {
            HapticManager.light()
            postNeedsPlus()
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "sparkles").font(.system(size: 12, weight: .bold))
                Text("Concierge actions need Roammate Plus")
                    .font(.system(.caption, design: .rounded, weight: .heavy))
                Spacer(minLength: 0)
                Text("Upgrade").font(.system(.caption2, design: .rounded, weight: .black))
            }
            .foregroundStyle(.white)
            .padding(.horizontal, RoammateSpacing.md).padding(.vertical, 8)
            .background(RoammateGradient.plus)
        }
        .buttonStyle(.plain)
    }

    private var lockedState: some View {
        VStack(spacing: RoammateSpacing.md) {
            Image(systemName: "sparkles")
                .font(.system(size: 30, weight: .semibold))
                .foregroundStyle(Color.roammateIndigo)
                .frame(width: 72, height: 72)
                .background(Color.roammateIndigoTint, in: Circle())
            Text("Concierge is run by trip admins")
                .font(.system(.title3, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateInk)
                .multilineTextAlignment(.center)
            Text("During the trip, an admin can ask the AI Concierge to reroute, skip stops, or find places nearby.")
                .font(.system(.subheadline, design: .rounded))
                .foregroundStyle(Color.roammateMuted)
                .multilineTextAlignment(.center)
                .padding(.horizontal, RoammateSpacing.xl)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Actions

    private func runningLate(_ minutes: Int) {
        requirePlus { Task { await store.runningLate(minutes: minutes) } }
    }

    /// Gate a Plus-only action: runs immediately if entitled, otherwise opens
    /// the paywall. (Free-text chat is intentionally not gated so the tutorial
    /// and the backend's own 402 handling still work.)
    private func requirePlus(_ action: () -> Void) {
        guard canUseConcierge else {
            HapticManager.light()
            postNeedsPlus()
            return
        }
        action()
    }

    private func postNeedsPlus() {
        NotificationCenter.default.post(
            name: .needsPlus, object: nil,
            userInfo: ["feature": PaywallFeature.concierge.rawValue]
        )
    }

    /// Seed a search origin from today's current/next event so "Find nearby"
    /// still works when device location is unavailable (e.g. the simulator).
    private func primeFallbackCoordinate() {
        let today = store.todayString
        let events = (detailStore.eventsByDay[today] ?? [])
            .filter { $0.lat != nil && $0.lng != nil && !$0.isSkipped }
            .sorted {
                if let a = $0.startTime, let b = $1.startTime { return a < b }
                return $0.sortOrder < $1.sortOrder
            }
        if let e = events.first, let lat = e.lat, let lng = e.lng {
            store.fallbackCoordinate = CLLocationCoordinate2D(latitude: lat, longitude: lng)
        }
    }
}
