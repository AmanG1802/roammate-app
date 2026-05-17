import SwiftUI

/// "Have a code?" disclosure with a TextField + Apply button. Re-validates
/// automatically when `target` changes (user toggled plan after applying a
/// code). Emits the validated `CouponQuote` upward via `onApplied`.
struct CouponInputView: View {
    let target: String   // "one_time" | "subscription"
    let initialCode: String?
    let onApplied: (CouponQuote?) -> Void

    @EnvironmentObject private var subscriptionStore: SubscriptionStore
    @State private var expanded: Bool = false
    @State private var code: String = ""
    @State private var quote: CouponQuote?
    @State private var error: String?
    @State private var submitting: Bool = false

    init(target: String, initialCode: String? = nil, onApplied: @escaping (CouponQuote?) -> Void) {
        self.target = target
        self.initialCode = initialCode
        self.onApplied = onApplied
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if !expanded {
                Button {
                    expanded = true
                    if let initialCode { code = initialCode.uppercased() }
                } label: {
                    Text("HAVE A CODE?")
                        .font(.caption2.weight(.black))
                        .tracking(0.6)
                        .foregroundStyle(Color.roammateIndigo)
                }
                .buttonStyle(.plain)
            } else if let quote {
                appliedRow(quote: quote)
            } else {
                inputRow
                if let error {
                    Label(error, systemImage: "sparkles")
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(Color.roammateDanger)
                }
            }
        }
        .onChange(of: target) { _, _ in
            if let q = quote { Task { await apply(code: q.code) } }
        }
        .task {
            if let initialCode, !initialCode.isEmpty, quote == nil {
                expanded = true
                code = initialCode.uppercased()
                await apply(code: initialCode)
            }
        }
    }

    private var inputRow: some View {
        HStack(spacing: 8) {
            TextField("Enter code", text: $code)
                .textInputAutocapitalization(.characters)
                .autocorrectionDisabled()
                .font(.system(.subheadline, design: .rounded, weight: .bold))
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(Color.roammateBackground)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12, style: .continuous)
                                .stroke(Color.roammateBorder, lineWidth: 1)
                        )
                )
            Button {
                Task { await apply(code: code) }
            } label: {
                Group {
                    if submitting {
                        ProgressView().tint(.white)
                    } else {
                        Text("APPLY").font(.caption2.weight(.black)).tracking(0.5)
                    }
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(Capsule().fill(Color.roammateInk))
                .foregroundStyle(.white)
            }
            .buttonStyle(.plain)
            .disabled(submitting || code.trimmingCharacters(in: .whitespaces).isEmpty)
        }
    }

    private func appliedRow(quote: CouponQuote) -> some View {
        HStack(spacing: 10) {
            ZStack {
                Circle().fill(Color.roammateSuccess).frame(width: 22, height: 22)
                Image(systemName: "checkmark")
                    .font(.system(size: 10, weight: .black))
                    .foregroundStyle(.white)
            }
            VStack(alignment: .leading, spacing: 0) {
                Text(quote.code)
                    .font(.caption.weight(.black))
                    .tracking(0.5)
                    .foregroundStyle(Color.roammateSuccess)
                Text(quote.displayMessage)
                    .font(.caption2)
                    .foregroundStyle(Color.roammateMuted)
                    .lineLimit(1)
            }
            Spacer()
            Button {
                self.quote = nil
                code = ""
                error = nil
                onApplied(nil)
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(Color.roammateMuted)
                    .padding(6)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Color.roammateSuccess.opacity(0.08))
                .overlay(
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .stroke(Color.roammateSuccess.opacity(0.3), lineWidth: 1)
                )
        )
    }

    private func apply(code: String) async {
        let trimmed = code.trimmingCharacters(in: .whitespaces).uppercased()
        guard !trimmed.isEmpty else { return }
        submitting = true
        error = nil
        defer { submitting = false }
        do {
            let q = try await subscriptionStore.validateCoupon(trimmed, target: target)
            quote = q
            onApplied(q)
        } catch let APIError.serverError(_, message) {
            if let data = message.data(using: .utf8),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let detail = json["detail"] as? [String: Any],
               let msg = detail["message"] as? String {
                error = msg
            } else if !message.isEmpty {
                error = message
            } else {
                error = "This code isn't valid."
            }
            quote = nil
            onApplied(nil)
        } catch {
            self.error = "Could not check that code."
            quote = nil
            onApplied(nil)
        }
    }
}
