import SwiftUI

struct BrainstormMessageBubble: View {
    let message: BrainstormMessage

    private var isUser: Bool { message.role == "user" }

    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            if isUser { Spacer(minLength: 48) }

            if !isUser {
                sparkleAvatar
            }

            VStack(alignment: isUser ? .trailing : .leading, spacing: 0) {
                if isUser {
                    Text(message.content)
                        .font(.system(.body, design: .rounded))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(userBubbleBg)
                        .textSelection(.enabled)
                } else {
                    Text(parseMarkdown(message.content))
                        .font(.system(.body, design: .rounded))
                        .foregroundStyle(Color.roammateInk)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(aiBubbleBg)
                        .textSelection(.enabled)
                }
            }

            if !isUser { Spacer(minLength: 48) }
        }
    }

    private var userBubbleBg: some View {
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
    }

    private var aiBubbleBg: some View {
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

    private var sparkleAvatar: some View {
        ZStack {
            Circle()
                .fill(
                    LinearGradient(
                        colors: [Color.roammateIndigo, Color.roammateViolet],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
            Image(systemName: "sparkles")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(.white)
        }
        .frame(width: 28, height: 28)
    }

    private func parseMarkdown(_ text: String) -> AttributedString {
        do {
            var result = try AttributedString(markdown: text, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace))
            result.font = .system(.body, design: .rounded)
            return result
        } catch {
            return AttributedString(text)
        }
    }
}
