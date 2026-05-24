import SwiftUI

// MARK: - Mockup dispatcher

/// Renders the high-fidelity mini-mockup for a given intro card. All content
/// is static (no live stores) — these mirror the web landing page's preview
/// panels.
struct IntroMockupView: View {
    let mockup: IntroMockup
    let accent: Color

    var body: some View {
        switch mockup {
        case .welcome:    WelcomeMockup()
        case .brainstorm: BrainstormMockup()
        case .ideaBin:    IdeaBinMockup()
        case .planMode:   PlanModeMockup()
        case .concierge:  ConciergeMockup()
        case .personas:   PersonasMockup()
        case .plus:       PlusMockup()
        case .ready:      ReadyMockup()
        }
    }
}

// MARK: - Shared bits

/// A small chat bubble used by the Brainstorm + Concierge mockups.
private struct IntroChatBubble: View {
    let text: String
    let isUser: Bool
    var onDark: Bool = false

    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 28) }
            Text(text)
                .font(.system(size: 13, design: .rounded))
                .foregroundStyle(isUser ? (onDark ? Color.roammateInk : Color.white) : Color.roammateInk)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(isUser ? (onDark ? Color.white : Color.roammateIndigo) : Color.roammateSurface)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .stroke(isUser ? Color.clear : (onDark ? Color.white.opacity(0.2) : Color.roammateBorder), lineWidth: 1)
                )
            if !isUser { Spacer(minLength: 28) }
        }
    }
}

/// A single "place" row (bullet + name + optional detail) used in AI replies.
private struct PlaceLine: View {
    let name: String
    var detail: String? = nil
    var bulletColor: Color = .roammateMuted

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Circle().fill(bulletColor).frame(width: 5, height: 5)
            Group {
                Text(name).foregroundStyle(Color.roammateInk).fontWeight(.semibold)
                + Text(detail.map { " — \($0)" } ?? "").foregroundStyle(Color.roammateMuted)
            }
            .font(.system(size: 12.5, design: .rounded))
            Spacer(minLength: 0)
        }
    }
}

/// Card container matching the web's white rounded preview panels.
private extension View {
    func mockupCard(padding: CGFloat = 14) -> some View {
        self
            .padding(padding)
            .background(
                RoundedRectangle(cornerRadius: 24, style: .continuous).fill(Color.roammateSurface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .stroke(Color.roammateBorder, lineWidth: 1)
            )
            .shadow(
                color: RoammateShadow.card.color,
                radius: RoammateShadow.card.radius,
                x: RoammateShadow.card.x, y: RoammateShadow.card.y
            )
    }
}

// MARK: - 1. Welcome

private struct WelcomeMockup: View {
    var body: some View { EmptyView() }
}

// MARK: - 2. Brainstorm

private struct BrainstormMockup: View {
    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 10) {
                IntroChatBubble(text: "3 days in Lisbon, foodie vibe, no museums", isUser: true)
                aiReply(
                    header: "Here's a starting list",
                    places: [
                        ("Time Out Market", "chef stalls"),
                        ("Pastéis de Belém", "original recipe"),
                        ("Tasca da Esquina", "bistro"),
                    ],
                    showAddChip: true
                )
                IntroChatBubble(text: "Skip the markets — add something for nightlife", isUser: true)
                aiReply(
                    header: "Got it — swapped them out",
                    places: [
                        ("Tasca Bela", "late-night Fado"),
                        ("Park Bar", "rooftop sundowners"),
                        ("Pensão Amor", "old-Lisbon cocktails"),
                    ],
                    showAddChip: false
                )
            }
        }
        .mockupCard()
        .accessibilityHidden(true)
    }

    private func aiReply(
        header: String,
        places: [(String, String)],
        showAddChip: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: "sparkles").font(.system(size: 12, weight: .bold))
                Text(header).font(.system(size: 13, weight: .bold, design: .rounded))
            }
            .foregroundStyle(Color.roammateViolet)

            ForEach(places, id: \.0) { name, detail in
                PlaceLine(name: name, detail: detail, bulletColor: .roammateViolet)
            }

            if showAddChip {
                HStack(spacing: 5) {
                    Image(systemName: "sparkles").font(.system(size: 10, weight: .bold))
                    Text("Add all to Idea Bin")
                        .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                }
                .foregroundStyle(Color.roammateViolet)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Capsule().fill(Color.roammateSurface))
                .overlay(Capsule().stroke(Color.roammateViolet.opacity(0.4), lineWidth: 1))
                .padding(.top, 2)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous).fill(Color.roammateVioletTint)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Color.roammateViolet.opacity(0.18), lineWidth: 1)
        )
    }
}

// MARK: - 3. Idea Bin

private struct IntroIdeaCard: View {
    let title: String
    let category: String
    var time: String? = nil
    var up: Int = 0
    var down: Int = 0

    var body: some View {
        HStack(spacing: 0) {
            CategoryColorBar(category: category)
            VStack(alignment: .leading, spacing: 8) {
                Text(title)
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.roammateInk)

                PillLabel(
                    text: category.capitalized,
                    background: Color.categoryTint(category),
                    foreground: Color.categoryColor(category)
                )

                HStack(spacing: 8) {
                    // Always render the time row; opacity(0) when nil keeps layout consistent
                    HStack(spacing: 5) {
                        Image(systemName: "clock").font(.system(size: 11))
                        Text(time ?? " ").font(.system(size: 12, weight: .medium, design: .rounded))
                        Image(systemName: "pencil").font(.system(size: 10))
                    }
                    .foregroundStyle(Color.roammateMuted)
                    .padding(.horizontal, 9)
                    .padding(.vertical, 5)
                    .background(Capsule().fill(Color.roammateBackground))
                    .opacity(time == nil ? 0 : 1)

                    Spacer(minLength: 0)
                    voteChip(icon: "hand.thumbsup", count: up)
                    voteChip(icon: "hand.thumbsdown", count: down)
                }
            }
            .padding(12)
        }
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous).fill(Color.roammateSurface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Color.roammateBorder, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private func voteChip(icon: String, count: Int) -> some View {
        HStack(spacing: 4) {
            Image(systemName: icon).font(.system(size: 12, weight: .semibold))
            Text("\(count)").font(.system(size: 12, weight: .black, design: .rounded))
        }
        .foregroundStyle(Color.roammateMuted)
        .padding(.horizontal, 8)
        .padding(.vertical, 5)
        .background(RoundedRectangle(cornerRadius: 8).fill(Color.roammateBackground))
    }
}

private struct IdeaBinMockup: View {
    var body: some View {
        VStack(spacing: 10) {
            IntroIdeaCard(title: "Rock Bar, AYANA Resort", category: "Nightlife",
                          time: "6:00 PM – 7:00 PM", up: 0, down: 0)
            IntroIdeaCard(title: "Time Out Market", category: "Food",
                          time: "11:00 AM – 12:00 PM", up: 5, down: 0)
            IntroIdeaCard(title: "Belém Tower", category: "Landmarks",
                          time: "2:00 PM – 3:00 PM", up: 4, down: 1)
        }
        .accessibilityHidden(true)
    }
}

// MARK: - 4. Plan Mode

private struct RouteShape: Shape {
    let points: [CGPoint] // normalized 0...1
    func path(in rect: CGRect) -> Path {
        var p = Path()
        guard let first = points.first else { return p }
        p.move(to: CGPoint(x: first.x * rect.width, y: first.y * rect.height))
        for pt in points.dropFirst() {
            p.addLine(to: CGPoint(x: pt.x * rect.width, y: pt.y * rect.height))
        }
        return p
    }
}

private struct PlanModeMockup: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var selectedDay: Int = 0
    @State private var routeProgress: CGFloat = 0

    private struct TripItem: Identifiable {
        let name: String
        let category: String
        let time: String
        var id: String { name }
    }

    private let dayLabels = ["Day 1 · Thu", "Day 2", "Day 3"]

    private let dayPins: [[CGPoint]] = [
        [CGPoint(x: 0.20, y: 0.75), CGPoint(x: 0.50, y: 0.45), CGPoint(x: 0.78, y: 0.22)],
        [CGPoint(x: 0.15, y: 0.65), CGPoint(x: 0.70, y: 0.30), CGPoint(x: 0.85, y: 0.72)],
        [CGPoint(x: 0.30, y: 0.60), CGPoint(x: 0.55, y: 0.25), CGPoint(x: 0.80, y: 0.65)],
    ]

    private let dayItems: [[TripItem]] = [
        [TripItem(name: "Pastéis de Belém",    category: "Food",          time: "09:00"),
         TripItem(name: "Jerónimos Monastery",  category: "Landmarks",     time: "11:30"),
         TripItem(name: "Alfama Viewpoint",     category: "Culture & Arts",time: "15:00")],
        [TripItem(name: "Belém Tower",          category: "Landmarks",     time: "10:00"),
         TripItem(name: "LX Factory",           category: "Shopping",      time: "14:00"),
         TripItem(name: "Fado Dinner",          category: "Entertainment", time: "20:00")],
        [TripItem(name: "Alfama Walk",          category: "Culture & Arts",time: "10:30"),
         TripItem(name: "Pastelaria Versailles",category: "Food",          time: "16:30"),
         TripItem(name: "Fado Show",            category: "Entertainment", time: "20:00")],
    ]

    var body: some View {
        VStack(spacing: 0) {
            // Map — top half
            ZStack {
                LinearGradient(
                    colors: [Color.roammateIndigoTint, Color.roammateEmeraldTint],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                GeometryReader { geo in
                    let pins = dayPins[selectedDay]
                    RouteShape(points: pins)
                        .trim(from: 0, to: routeProgress)
                        .stroke(Color.roammatePurple,
                                style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round))
                    ForEach(Array(pins.enumerated()), id: \.offset) { i, pt in
                        numberedPin(i + 1)
                            .position(x: pt.x * geo.size.width, y: pt.y * geo.size.height)
                            .opacity(routeProgress > CGFloat(i) / CGFloat(pins.count) ? 1 : 0)
                    }
                }
                .padding(14)
            }
            .frame(height: 160)

            // Drawer — white sheet below
            VStack(alignment: .leading, spacing: 10) {
                Text("Try it yourself")
                    .font(.system(.caption2, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.roammateMuted)
                    .padding(.bottom, 2)

                HStack(spacing: 8) {
                    ForEach(0..<dayLabels.count, id: \.self) { idx in
                        Button {
                            selectedDay = idx
                            routeProgress = 0
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                                withAnimation(.easeInOut(duration: 1.1)) { routeProgress = 1 }
                            }
                        } label: {
                            Text(dayLabels[idx])
                                .font(.system(size: 12, weight: .bold, design: .rounded))
                                .foregroundStyle(selectedDay == idx ? .white : Color.roammateMuted)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 7)
                                .background(
                                    Capsule().fill(selectedDay == idx
                                                   ? Color.roammateIndigo
                                                   : Color.roammateBackground)
                                )
                        }
                        .buttonStyle(.plain)
                        .animation(.spring(response: 0.4), value: selectedDay)
                    }
                }

                ForEach(dayItems[selectedDay]) { item in
                    timelineRow(name: item.name, category: item.category, time: item.time)
                }
            }
            .padding(14)
            .background(Color.roammateSurface)
        }
        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .stroke(Color.roammateBorder, lineWidth: 1)
        )
        .shadow(
            color: RoammateShadow.card.color,
            radius: RoammateShadow.card.radius,
            x: RoammateShadow.card.x,
            y: RoammateShadow.card.y
        )
        .onAppear { triggerRouteAnimation() }
        .accessibilityHidden(true)
    }

    private func triggerRouteAnimation() {
        if reduceMotion {
            routeProgress = 1
        } else {
            withAnimation(.easeInOut(duration: 1.1).delay(0.25)) { routeProgress = 1 }
        }
    }

    private func numberedPin(_ n: Int) -> some View {
        let color: Color = n < 3 ? .roammateAmber : .roammatePurple
        return ZStack {
            Circle().fill(color)
            Text("\(n)").font(.system(size: 11, weight: .black)).foregroundStyle(.white)
        }
        .frame(width: 22, height: 22)
        .shadow(color: color.opacity(0.4), radius: 4, y: 2)
    }

    private func timelineRow(name: String, category: String, time: String) -> some View {
        HStack(spacing: 10) {
            CategoryColorBar(category: category).frame(height: 30)
            Text(name)
                .font(.system(size: 13, weight: .semibold, design: .rounded))
                .foregroundStyle(Color.roammateInk)
            Spacer(minLength: 0)
            Text(time)
                .font(.system(size: 11, weight: .bold, design: .rounded))
                .foregroundStyle(Color.roammateIndigo)
                .padding(.horizontal, 8).padding(.vertical, 4)
                .background(Capsule().fill(Color.roammateIndigoTint))
        }
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(Color.roammateBackground))
    }
}

// MARK: - 5. Concierge (light — matches web `bg-indigo-50` section)

private struct ConciergeMockup: View {
    var body: some View {
        VStack(spacing: 12) {
            // Storyboard — three white step cards
            HStack(alignment: .top, spacing: 8) {
                stepCard(step: 1, icon: "clock", label: "Running late")
                stepCard(step: 2, icon: "wand.and.sparkles", label: "Day reflows")
                stepCard(step: 3, icon: "bell.fill", label: "Group pinged")
            }

            chatCard
        }
        .accessibilityHidden(true)
    }

    // MARK: Step card

    private func stepCard(step: Int, icon: String, label: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            ZStack {
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(Color.roammateIndigo)
                    .frame(width: 38, height: 38)
                    .shadow(color: Color.roammateIndigo.opacity(0.4), radius: 8, y: 4)
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(.white)
            }
            Text("STEP \(step)")
                .font(.system(size: 10, weight: .bold))
                .tracking(1.3)
                .foregroundStyle(Color.roammateIndigo)
            Text(label)
                .font(.system(size: 13, weight: .bold, design: .rounded))
                .foregroundStyle(Color.roammateInk)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 16, style: .continuous).fill(Color.roammateSurface))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous)
            .stroke(Color.roammateBorder, lineWidth: 1))
    }

    // MARK: Chat card

    private var chatCard: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header: gradient avatar + "Concierge · Live" + live status
            HStack(spacing: 8) {
                ZStack {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(LinearGradient(
                            colors: [Color.roammateIndigo, Color.roammateFuchsia],
                            startPoint: .topLeading, endPoint: .bottomTrailing))
                        .frame(width: 32, height: 32)
                        .shadow(color: Color.roammateIndigo.opacity(0.3), radius: 8, y: 4)
                    Image(systemName: "wand.and.sparkles")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(.white)
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text("Concierge · Live")
                        .font(.system(size: 13, weight: .black, design: .rounded))
                        .foregroundStyle(Color.roammateInk)
                    HStack(spacing: 5) {
                        Circle().fill(Color.roammateEmerald).frame(width: 6, height: 6)
                        Text("WATCHING YOUR TRIP")
                            .font(.system(size: 10, weight: .bold))
                            .tracking(1.2)
                            .foregroundStyle(Color.roammateIndigo)
                    }
                }
                Spacer(minLength: 0)
            }
            .padding(.bottom, 12)

            Rectangle().fill(Color.roammateBorder).frame(height: 1)
                .padding(.bottom, 12)

            VStack(spacing: 8) {
                chatBubble("We're running 45 minutes late at lunch.", isUser: true)
                chatBubble("Got it — pushed your 2pm to 2:45pm. Skipped the LX Factory detour. Walking to Time Out Market is 8 min from here.", isUser: false)
                chatBubble("Find a coffee place nearby?", isUser: true)
                chatBubble("Fábrica Coffee Roasters is 2 min away, 4.6★ — added between stops.", isUser: false)
            }
        }
        .padding(16)
        .background(RoundedRectangle(cornerRadius: 20, style: .continuous).fill(Color.roammateSurface))
        .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous)
            .stroke(Color.roammateBorder, lineWidth: 1))
    }

    /// User bubbles: indigo-600 + white. AI bubbles: indigo-50 fill + indigo-200 border.
    private func chatBubble(_ text: String, isUser: Bool) -> some View {
        HStack {
            if isUser { Spacer(minLength: 32) }
            Text(text)
                .font(.system(size: 13, design: .rounded))
                .foregroundStyle(isUser ? Color.white : Color.roammateInk)
                .padding(.horizontal, 12)
                .padding(.vertical, 9)
                .background(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(isUser ? Color.roammateIndigo : Color.roammateIndigoTint)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .stroke(isUser ? Color.clear : Color.roammateIndigo200, lineWidth: 1)
                )
            if !isUser { Spacer(minLength: 32) }
        }
    }
}

// MARK: - 6. Personas

private struct IntroPersonaAnswer: View {
    let label: String
    let accent: Color
    let tint: Color
    let places: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label.uppercased())
                .font(.system(size: 10, weight: .bold))
                .tracking(1.2)
                .foregroundStyle(accent)
                .padding(.horizontal, 9).padding(.vertical, 4)
                .background(Capsule().fill(tint))
                .overlay(Capsule().stroke(accent.opacity(0.3), lineWidth: 1))

            IntroChatBubble(text: "3 days in Lisbon", isUser: true)

            VStack(alignment: .leading, spacing: 6) {
                ForEach(places, id: \.self) { place in
                    let parts = place.components(separatedBy: " — ")
                    PlaceLine(name: parts.first ?? place,
                              detail: parts.count > 1 ? parts[1] : nil,
                              bulletColor: accent)
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(tint))
        }
        .mockupCard()
    }
}

private struct PersonasMockup: View {
    var body: some View {
        VStack(spacing: 12) {
            IntroPersonaAnswer(
                label: "Foodie", accent: .roammateAmber, tint: .roammateAmberTint,
                places: ["Tasca da Esquina — neighborhood bistro",
                         "Pastelaria 1829 — pastéis benchmark",
                         "Time Out Market — chef-curated stalls"]
            )
            IntroPersonaAnswer(
                label: "Cultural deep-diver", accent: .roammateFuchsia, tint: .roammateFuchsiaTint,
                places: ["Jerónimos Monastery — Manueline jewel",
                         "Gulbenkian — Lalique + Ancient Egypt",
                         "Fado vadio in Alfama — no tourists"]
            )
        }
        .accessibilityHidden(true)
    }
}

// MARK: - 7. Roammate Plus

private struct PlusMockup: View {
    var body: some View {
        VStack(spacing: 12) {
            // Free
            VStack(alignment: .leading, spacing: 10) {
                Text("FREE")
                    .font(.system(size: 11, weight: .bold)).tracking(1.4)
                    .foregroundStyle(Color.roammateMuted)
                Text("Everything to plan a great trip.")
                    .font(.system(size: 16, weight: .black)).tracking(-0.3)
                    .foregroundStyle(Color.roammateInk)
                featureRow(icon: "safari", text: "2 active trips at a time", color: .roammateIndigo)
                featureRow(icon: "sparkles", text: "15 AI brainstorms / month", color: .roammateIndigo)
                featureRow(icon: "hand.thumbsup", text: "Group voting & full Plan Mode", color: .roammateIndigo)
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 20, style: .continuous).fill(Color.roammateSurface))
            .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous)
                .stroke(Color.roammateBorder, lineWidth: 1))

            // Plus
            VStack(alignment: .leading, spacing: 10) {
                Text("PLUS")
                    .font(.system(size: 11, weight: .bold)).tracking(1.4)
                    .foregroundStyle(.white.opacity(0.9))
                Text("Everything, unlimited.")
                    .font(.system(size: 16, weight: .black)).tracking(-0.3)
                    .foregroundStyle(.white)
                featureRow(icon: "infinity", text: "Unlimited trips & brainstorms", color: .white)
                featureRow(icon: "wand.and.sparkles", text: "Always-on AI Concierge", color: .white)
                featureRow(icon: "map", text: "Offline maps for the road", color: .white)
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 20, style: .continuous).fill(RoammateGradient.plus)
            )
            .shadow(color: Color.roammateIndigo.opacity(0.25), radius: 18, y: 8)
        }
        .accessibilityHidden(true)
    }

    private func featureRow(icon: String, text: String, color: Color) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(color)
                .frame(width: 22, height: 22)
                .background(Circle().fill(color.opacity(color == .white ? 0.18 : 0.12)))
            Text(text)
                .font(.system(size: 13, weight: .medium, design: .rounded))
                .foregroundStyle(color == .white ? .white : Color.roammateInk)
            Spacer(minLength: 0)
        }
    }
}

// MARK: - 8. Ready to Roam

private struct ReadyMockup: View {
    var body: some View { EmptyView() }
}

// MARK: - Previews

#Preview("Mockups") {
    ScrollView {
        VStack(spacing: 24) {
            BrainstormMockup()
            IdeaBinMockup()
            PlanModeMockup()
            PersonasMockup()
            PlusMockup()
        }
        .padding()
    }
    .background(Color.roammateBackground)
}

#Preview("Concierge (dark)") {
    ConciergeMockup().padding().background(
        LinearGradient(colors: [Color.roammateIndigo, Color.roammateIndigoDark],
                       startPoint: .topLeading, endPoint: .bottomTrailing)
    )
}
