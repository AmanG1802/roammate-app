import SwiftUI

// MARK: - Message dispatcher

/// Renders one chat turn into the right bubble or rich card based on its
/// `ConciergeCard`. Used by `TripConciergeView`'s message list.
struct ConciergeMessageView: View {
    let message: ChatMessage
    @EnvironmentObject var store: ConciergeStore

    var body: some View {
        switch message.card {
        case .text:
            ConciergeBubble(role: message.role, text: message.text, authorName: message.authorName)
        case .actionCard:
            ConciergeActionCardView(message: message)
        case .placeCards(let places):
            ConciergePlaceCarousel(intro: message.text, places: places)
        case .summary(let summary):
            ConciergeSummaryCard(summary: summary)
        case .whatsNext(let next):
            ConciergeWhatsNextCard(data: next)
        case .rippleResult(let shifted, let minutes):
            ConciergeRippleResultCard(shifted: shifted, minutes: minutes)
        case .error(let retryQuery):
            ConciergeErrorCard(text: message.text, retryQuery: retryQuery)
        }
    }
}

// MARK: - Markdown helper

func conciergeMarkdown(_ raw: String) -> AttributedString {
    (try? AttributedString(markdown: raw)) ?? AttributedString(raw)
}

// MARK: - Text bubble

struct ConciergeBubble: View {
    let role: ChatMessage.Role
    let text: String
    var authorName: String? = nil

    var body: some View {
        // System turns (confirmation receipts, undo notices) render as a small
        // centered note rather than a chat bubble.
        if role == .system {
            HStack {
                Spacer()
                Text(conciergeMarkdown(text))
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
                    .padding(.horizontal, 12).padding(.vertical, 6)
                    .background(Color.roammateBackground, in: Capsule())
                Spacer()
            }
        } else {
            HStack {
                if role == .user { Spacer(minLength: 40) }
                VStack(alignment: role == .user ? .trailing : .leading, spacing: 2) {
                    // 3.1: author label in the shared trip-wide thread.
                    if role == .user, let authorName {
                        Text(authorName)
                            .font(.system(size: 11, weight: .semibold, design: .rounded))
                            .foregroundStyle(Color.roammateMuted)
                            .padding(.horizontal, 4)
                    }
                    Text(conciergeMarkdown(text))
                        .font(.system(.subheadline, design: .rounded))
                        .foregroundStyle(role == .user ? .white : Color.roammateInk)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(
                            role == .user ? Color.roammateIndigo : Color.roammateSurface,
                            in: RoundedRectangle(cornerRadius: 18, style: .continuous)
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 18, style: .continuous)
                                .stroke(role == .assistant ? Color.roammateBorder : Color.clear, lineWidth: 1)
                        )
                }
                if role == .assistant { Spacer(minLength: 40) }
            }
        }
    }
}

// MARK: - Action confirmation card

struct ConciergeActionCardView: View {
    let message: ChatMessage
    @EnvironmentObject var store: ConciergeStore

    private var icon: String {
        switch message.intent {
        case .shiftTimeline: return "clock.arrow.circlepath"
        case .moveEvent:     return "mappin.and.ellipse"
        case .addEvent:      return "plus.circle.fill"
        case .skipEvent:     return "forward.end.fill"
        case .findNearby:    return "cup.and.saucer.fill"
        case .explainPlan:   return "text.bubble.fill"
        default:             return "sparkles"
        }
    }

    private var status: ActionStatus { message.status ?? .pending }

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            ZStack {
                Circle()
                    .fill(accentTint)
                    .frame(width: 36, height: 36)
                Image(systemName: status == .confirmed ? "checkmark" : (status == .cancelled ? "xmark" : icon))
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(accent)
            }

            VStack(alignment: .leading, spacing: 10) {
                Text(conciergeMarkdown(message.text))
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(status == .cancelled ? Color.roammateMuted : Color.roammateInk)
                    .strikethrough(status == .cancelled)

                // 3.5/3.6/3.7: real projected impact — before→after diff + warnings.
                if let preview = message.preview,
                   !(preview.changes.isEmpty && preview.warnings.isEmpty) {
                    ConciergePreviewBlock(preview: preview)
                }

                if status == .pending {
                    HStack(spacing: 8) {
                        Button {
                            HapticManager.success()
                            Task { await store.confirm(message) }
                        } label: {
                            Text("Confirm")
                                .font(.system(.footnote, design: .rounded, weight: .heavy))
                                .foregroundStyle(.white)
                                .padding(.horizontal, 18).padding(.vertical, 8)
                                .background(Color.roammateIndigo, in: Capsule())
                        }
                        .buttonStyle(.plain)

                        Button {
                            HapticManager.light()
                            store.cancel(message)
                        } label: {
                            Text("Cancel")
                                .font(.system(.footnote, design: .rounded, weight: .heavy))
                                .foregroundStyle(Color.roammateMuted)
                                .padding(.horizontal, 18).padding(.vertical, 8)
                                .background(Color.roammateBackground, in: Capsule())
                        }
                        .buttonStyle(.plain)
                    }
                } else {
                    HStack(spacing: 12) {
                        Text(status == .confirmed ? "Confirmed" : "Cancelled")
                            .font(.system(.caption, design: .rounded, weight: .bold))
                            .foregroundStyle(accent)
                        // 3.8: revert the most recent executed action.
                        if status == .confirmed && message.canUndo {
                            Button {
                                HapticManager.light()
                                Task { await store.undo(message) }
                            } label: {
                                HStack(spacing: 4) {
                                    Image(systemName: "arrow.uturn.backward").font(.system(size: 10, weight: .bold))
                                    Text("Undo").font(.system(.caption, design: .rounded, weight: .heavy))
                                }
                                .foregroundStyle(Color.roammateMuted)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
            Spacer(minLength: 0)
        }
        .padding(14)
        .background(Color.roammateSurface, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(accent.opacity(0.25), lineWidth: 1)
        )
        .padding(.trailing, 40)
    }

    private var accent: Color {
        switch status {
        case .pending:   return .roammateIndigo
        case .confirmed: return .roammateSuccess
        case .cancelled: return .roammateMuted
        }
    }

    private var accentTint: Color {
        switch status {
        case .pending:   return .roammateIndigoTint
        case .confirmed: return Color.roammateSuccess.opacity(0.12)
        case .cancelled: return Color.roammateBackground
        }
    }
}

// MARK: - Dry-run preview block (before→after diff + warnings)

struct ConciergePreviewBlock: View {
    let preview: ConciergePreview

    private func warningIcon(_ kind: String) -> String {
        switch kind {
        case "opening_hours": return "clock.badge.exclamationmark"
        case "cross_midnight": return "moon.fill"
        case "travel": return "car.fill"
        case "overlap": return "timer"
        default: return "exclamationmark.triangle.fill"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if !preview.summary.isEmpty {
                Text(preview.summary.uppercased())
                    .font(.system(size: 10, weight: .heavy, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
            }

            if !preview.changes.isEmpty {
                VStack(spacing: 4) {
                    ForEach(preview.changes) { c in
                        HStack(spacing: 6) {
                            Text(c.title)
                                .font(.system(.caption, design: .rounded, weight: .medium))
                                .foregroundStyle(Color.roammateInk)
                                .lineLimit(1)
                            Spacer(minLength: 8)
                            if let old = c.oldStart {
                                Text(old)
                                    .font(.system(size: 11, weight: .semibold, design: .rounded))
                                    .foregroundStyle(Color.roammateMuted)
                                    .strikethrough()
                            }
                            if c.oldStart != nil && c.newStart != nil {
                                Image(systemName: "arrow.right").font(.system(size: 8, weight: .bold))
                                    .foregroundStyle(Color.roammateMuted)
                            }
                            if let new = c.newStart {
                                Text(new)
                                    .font(.system(size: 11, weight: .heavy, design: .rounded))
                                    .foregroundStyle(c.oldStart == nil ? Color.roammateSuccess : Color.roammateIndigo)
                            }
                        }
                    }
                }
            }

            if !preview.warnings.isEmpty {
                VStack(spacing: 4) {
                    ForEach(preview.warnings) { w in
                        HStack(alignment: .top, spacing: 6) {
                            Image(systemName: warningIcon(w.kind))
                                .font(.system(size: 10, weight: .bold))
                                .foregroundStyle(Color.roammateAmber)
                            Text(w.message)
                                .font(.system(.caption2, design: .rounded))
                                .foregroundStyle(Color.roammateInk)
                            Spacer(minLength: 0)
                        }
                        .padding(.horizontal, 8).padding(.vertical, 5)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.roammateAmberTint, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                    }
                }
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.roammateBackground, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

// MARK: - Place carousel

struct ConciergePlaceCarousel: View {
    let intro: String
    let places: [PlaceCard]
    @EnvironmentObject var store: ConciergeStore

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if !intro.isEmpty {
                Text(conciergeMarkdown(intro))
                    .font(.system(.subheadline, design: .rounded))
                    .foregroundStyle(Color.roammateInk)
                    .padding(.horizontal, 14).padding(.vertical, 10)
                    .background(Color.roammateSurface, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: 18, style: .continuous).stroke(Color.roammateBorder, lineWidth: 1))
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(places) { place in
                        PlaceCardCell(place: place) {
                            HapticManager.light()
                            store.selectPlace(place)
                        }
                    }
                }
                .padding(.vertical, 2)
            }

            Button {
                HapticManager.light()
                store.viewOnMap(places)
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: "map.fill").font(.system(size: 12, weight: .bold))
                    Text("View on map").font(.system(.footnote, design: .rounded, weight: .heavy))
                }
                .foregroundStyle(Color.roammateIndigo)
                .padding(.horizontal, 14).padding(.vertical, 8)
                .background(Color.roammateIndigoTint, in: Capsule())
            }
            .buttonStyle(.plain)
        }
        .padding(.trailing, 24)
    }
}

private struct PlaceCardCell: View {
    let place: PlaceCard
    let onSelect: () -> Void

    private var travelText: String? {
        guard let s = place.travelTimeS else { return nil }
        let mins = max(1, Int(round(Double(s) / 60.0)))
        return "\(mins) min away"
    }

    var body: some View {
        Button(action: onSelect) {
            VStack(alignment: .leading, spacing: 0) {
                ZStack {
                    Color.roammateIndigoTint
                    if let urlStr = place.photoUrl, let url = URL(string: urlStr) {
                        AsyncImage(url: url) { image in
                            image.resizable().aspectRatio(contentMode: .fill)
                        } placeholder: {
                            Image(systemName: Color.categoryIcon(place.category))
                                .font(.system(size: 24))
                                .foregroundStyle(Color.roammateIndigo.opacity(0.5))
                        }
                    } else {
                        Image(systemName: Color.categoryIcon(place.category))
                            .font(.system(size: 24))
                            .foregroundStyle(Color.roammateIndigo.opacity(0.5))
                    }
                }
                .frame(width: 200, height: 96)
                .clipped()

                VStack(alignment: .leading, spacing: 4) {
                    Text(place.title)
                        .font(.system(.subheadline, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.roammateInk)
                        .lineLimit(1)

                    HStack(spacing: 6) {
                        if let rating = place.rating {
                            HStack(spacing: 2) {
                                Image(systemName: "star.fill").font(.system(size: 9))
                                Text(String(format: "%.1f", rating)).font(.system(size: 11, weight: .bold))
                            }
                            .foregroundStyle(Color.roammateAmber)
                        }
                        if let price = place.priceLevel, price > 0 {
                            Text(String(repeating: "$", count: min(price, 4)))
                                .font(.system(size: 11, weight: .bold))
                                .foregroundStyle(Color.roammateMuted)
                        }
                    }

                    if let travelText {
                        HStack(spacing: 3) {
                            Image(systemName: "location.fill").font(.system(size: 9))
                            Text(travelText).font(.system(size: 11, weight: .semibold))
                        }
                        .foregroundStyle(Color.roammateIndigo)
                    }

                    Text("Tap to add")
                        .font(.system(size: 10, weight: .heavy))
                        .foregroundStyle(Color.roammateIndigo)
                        .padding(.top, 2)
                }
                .padding(10)
            }
            .frame(width: 200, alignment: .leading)
            .background(Color.roammateSurface)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(Color.roammateBorder, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Today summary card

struct ConciergeSummaryCard: View {
    let summary: TodaySummaryResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Today").font(.system(.headline, design: .rounded, weight: .heavy))
                    .foregroundStyle(Color.roammateInk)
                Spacer()
                Text("\(summary.totalEvents) stop\(summary.totalEvents == 1 ? "" : "s")")
                    .font(.system(.caption, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.roammateMuted)
            }

            HStack(spacing: 6) {
                statPill(count: summary.completed, label: "done", color: .roammateSuccess)
                statPill(count: summary.upcoming, label: "upcoming", color: .roammateIndigo)
                if summary.skipped > 0 {
                    statPill(count: summary.skipped, label: "skipped", color: .roammateMuted)
                }
            }

            VStack(spacing: 8) {
                ForEach(Array(summary.events.enumerated()), id: \.offset) { _, item in
                    if let event = Event(conciergeJSON: item.event) {
                        HStack(spacing: 10) {
                            Circle().fill(dotColor(item.status)).frame(width: 8, height: 8)
                            Text(event.title)
                                .font(.system(.subheadline, design: .rounded, weight: .medium))
                                .foregroundStyle(item.status == "skipped" ? Color.roammateMuted : Color.roammateInk)
                                .strikethrough(item.status == "skipped")
                                .lineLimit(1)
                            Spacer()
                            Text(eventTimeShort(event))
                                .font(.system(size: 11, weight: .bold))
                                .foregroundStyle(Color.roammateMuted)
                        }
                    }
                }
            }
        }
        .padding(16)
        .background(Color.roammateSurface, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 18, style: .continuous).stroke(Color.roammateBorder, lineWidth: 1))
        .padding(.trailing, 24)
    }

    private func statPill(count: Int, label: String, color: Color) -> some View {
        HStack(spacing: 4) {
            Text("\(count)").font(.system(.caption, design: .rounded, weight: .black))
            Text(label).font(.system(.caption2, design: .rounded, weight: .semibold))
        }
        .foregroundStyle(color)
        .padding(.horizontal, 10).padding(.vertical, 5)
        .background(color.opacity(0.1), in: Capsule())
    }

    private func dotColor(_ status: String) -> Color {
        switch status {
        case "completed": return .roammateSuccess
        case "ongoing":   return .roammateIndigo
        case "skipped":   return .roammateMuted
        default:          return Color.roammateMuted.opacity(0.4)
        }
    }
}

// MARK: - What's next card

struct ConciergeWhatsNextCard: View {
    let data: WhatsNextResponse

    private var current: Event? { data.currentEvent.flatMap { Event(conciergeJSON: $0) } }
    private var next: Event? { data.nextEvent.flatMap { Event(conciergeJSON: $0) } }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let current {
                row(tag: "NOW", tagColor: .roammateIndigo, event: current, trailing: nil)
            }
            if let next {
                row(
                    tag: "NEXT",
                    tagColor: .roammateAmber,
                    event: next,
                    trailing: data.timeUntilNext.map { "in \($0)" }
                )
                if let travel = data.travelTimeToNext {
                    HStack(spacing: 5) {
                        Image(systemName: "car.fill").font(.system(size: 10))
                        Text("\(max(1, travel / 60)) min travel")
                            .font(.system(size: 11, weight: .bold))
                    }
                    .foregroundStyle(Color.roammateMuted)
                    .padding(.leading, 2)
                }
            }
            if current == nil && next == nil {
                Text("Nothing scheduled for the rest of today.")
                    .font(.system(.subheadline, design: .rounded))
                    .foregroundStyle(Color.roammateMuted)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.roammateSurface, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 18, style: .continuous).stroke(Color.roammateBorder, lineWidth: 1))
        .padding(.trailing, 24)
    }

    private func row(tag: String, tagColor: Color, event: Event, trailing: String?) -> some View {
        HStack(spacing: 10) {
            Text(tag)
                .font(.system(size: 10, weight: .black))
                .foregroundStyle(tagColor)
                .padding(.horizontal, 8).padding(.vertical, 3)
                .background(tagColor.opacity(0.12), in: Capsule())
            VStack(alignment: .leading, spacing: 2) {
                Text(event.title)
                    .font(.system(.subheadline, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.roammateInk)
                    .lineLimit(1)
                Text(eventTimeShort(event))
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(Color.roammateMuted)
            }
            Spacer()
            if let trailing {
                Text(trailing)
                    .font(.system(.caption, design: .rounded, weight: .heavy))
                    .foregroundStyle(tagColor)
            }
        }
    }
}

// MARK: - Ripple result card

struct ConciergeRippleResultCard: View {
    let shifted: Int
    let minutes: Int

    private var message: String {
        shifted == 0
            ? "No events needed adjusting."
            : "Shifted \(shifted) event\(shifted == 1 ? "" : "s") by +\(minutes) min."
    }

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: shifted == 0 ? "checkmark.circle.fill" : "clock.arrow.circlepath")
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(Color.roammateSuccess)
            Text(message)
                .font(.system(.subheadline, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.roammateInk)
            Spacer(minLength: 0)
        }
        .padding(14)
        .background(Color.roammateSuccess.opacity(0.08), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(Color.roammateSuccess.opacity(0.3), lineWidth: 1))
        .padding(.trailing, 40)
    }
}

// MARK: - Error card

struct ConciergeErrorCard: View {
    let text: String
    let retryQuery: String?
    @EnvironmentObject var store: ConciergeStore

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(Color.roammateAmber)
            VStack(alignment: .leading, spacing: 8) {
                Text(text)
                    .font(.system(.subheadline, design: .rounded))
                    .foregroundStyle(Color.roammateInk)
                if let retryQuery {
                    Button {
                        HapticManager.light()
                        store.retry(retryQuery)
                    } label: {
                        HStack(spacing: 5) {
                            Image(systemName: "arrow.clockwise").font(.system(size: 11, weight: .bold))
                            Text("Try again").font(.system(.footnote, design: .rounded, weight: .heavy))
                        }
                        .foregroundStyle(Color.roammateAmber)
                    }
                    .buttonStyle(.plain)
                }
            }
            Spacer(minLength: 0)
        }
        .padding(14)
        .background(Color.roammateAmberTint, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(Color.roammateAmber.opacity(0.3), lineWidth: 1))
        .padding(.trailing, 40)
    }
}

// MARK: - Shared time helpers

/// Short "h:mm a" rendering of an event's start (– end) time.
func eventTimeShort(_ event: Event) -> String {
    guard let start = event.startTime else { return "TBD" }
    func fmt(_ tod: TimeOfDay) -> String {
        let suffix = tod.hour < 12 ? "AM" : "PM"
        let h12 = tod.hour == 0 ? 12 : (tod.hour > 12 ? tod.hour - 12 : tod.hour)
        return String(format: "%d:%02d %@", h12, tod.minute, suffix)
    }
    if let end = event.endTime {
        return "\(fmt(start)) – \(fmt(end))"
    }
    return fmt(start)
}
