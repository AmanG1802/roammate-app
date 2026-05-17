import SwiftUI

struct BrainstormBinView: View {
    @EnvironmentObject var store: BrainstormStore

    @State private var isSelecting = false
    @State private var selected: Set<Int> = []
    @State private var showClearConfirm = false
    @State private var toastMessage: String?
    @State private var expandedId: Int?
    @State private var deletingId: Int?

    private static let timeCategoryLabels: [String: String] = [
        "morning": "Morning",
        "afternoon": "Afternoon",
        "evening": "Evening",
        "night": "Night",
        "all_day": "All Day",
        "flexible": "Flexible"
    ]

    var body: some View {
        VStack(spacing: 0) {
            header

            if store.items.isEmpty {
                Spacer()
                EmptyState(
                    icon: "tray",
                    title: "Brainstorm bin is empty",
                    subtitle: "Chat with the AI and extract ideas to fill your bin."
                )
                Spacer()
            } else {
                ScrollView {
                    LazyVStack(spacing: RoammateSpacing.sm) {
                        ForEach(store.items) { item in
                            if deletingId != item.id {
                                brainstormRow(item)
                                    .transition(.asymmetric(
                                        insertion: .opacity,
                                        removal: .move(edge: .leading).combined(with: .opacity)
                                    ))
                            }
                        }
                    }
                    .animation(.spring(response: 0.15, dampingFraction: 0.9), value: store.items.map(\.id))
                    .padding(.horizontal, RoammateSpacing.md)
                    .padding(.vertical, RoammateSpacing.sm)
                    .padding(.bottom, 80)
                }
            }

            if !store.items.isEmpty {
                bottomToolbar
            }
        }
        .background(Color.roammateBackground)
        .overlay(alignment: .top) {
            if let msg = toastMessage {
                toastView(msg)
                    .transition(.move(edge: .top).combined(with: .opacity))
                    .onAppear {
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
                            withAnimation { toastMessage = nil }
                        }
                    }
            }
        }
        .confirmationDialog("Clear all items?", isPresented: $showClearConfirm, titleVisibility: .visible) {
            Button("Clear All", role: .destructive) {
                Task { await store.clearAll() }
            }
        }
    }

    private var header: some View {
        HStack {
            Text("\(store.items.count) items")
                .font(.system(.caption, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateAmber)
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(Capsule().fill(Color.roammateAmberTint))

            Spacer()

            Button {
                HapticManager.selection()
                withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                    isSelecting.toggle()
                    if !isSelecting {
                        selected.removeAll()
                        expandedId = nil
                    }
                }
            } label: {
                Text(isSelecting ? "Cancel" : "Select")
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.roammateIndigo)
            }
            .buttonStyle(.plain)

            Menu {
                Button(role: .destructive) {
                    showClearConfirm = true
                } label: {
                    Label("Clear all", systemImage: "trash")
                }
            } label: {
                Image(systemName: "ellipsis.circle")
                    .font(.system(size: 18))
                    .foregroundStyle(Color.roammateMuted)
            }
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 12)
    }

    private func brainstormRow(_ item: BrainstormItemOut) -> some View {
        VStack(spacing: 0) {
            HStack(alignment: .top, spacing: 0) {
                if isSelecting {
                    Image(systemName: selected.contains(item.id) ? "checkmark.circle.fill" : "circle")
                        .font(.system(size: 22))
                        .foregroundStyle(selected.contains(item.id) ? Color.roammateIndigo : Color.roammateMuted)
                        .transition(.scale.combined(with: .opacity))
                        .padding(.trailing, 10)
                }

                CategoryColorBar(category: item.category)
                    .padding(.trailing, 10)

                VStack(alignment: .leading, spacing: 4) {
                    Text(item.title)
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.roammateInk)
                        .lineLimit(expandedId == item.id ? nil : 2)

                    if let category = item.category {
                        PillLabel(
                            text: category.capitalized,
                            background: Color.categoryTint(category),
                            foreground: Color.categoryColor(category)
                        )
                    }

                    if let timeCategory = item.timeCategory, !timeCategory.isEmpty {
                        HStack(spacing: 4) {
                            Image(systemName: "clock")
                                .font(.system(size: 11))
                            Text(Self.timeCategoryLabels[timeCategory.lowercased()] ?? timeCategory.capitalized)
                                .font(.system(.caption, design: .rounded, weight: .medium))
                        }
                        .foregroundStyle(Color.roammateMuted)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(
                            Capsule().fill(Color.roammateBackground)
                        )
                    }
                }

                Spacer()

                if !isSelecting {
                    Button {
                        HapticManager.light()
                        withAnimation(.spring(response: 0.4, dampingFraction: 0.75)) {
                            deletingId = item.id
                        }
                        Task {
                            try? await Task.sleep(nanoseconds: 150_000_000)
                            await store.delete(itemId: item.id)
                            deletingId = nil
                        }
                    } label: {
                        Image(systemName: "trash")
                            .font(.system(size: 14))
                            .foregroundStyle(Color.roammateMuted)
                    }
                    .buttonStyle(.plain)
                }
            }

            if expandedId == item.id {
                expandedContent(for: item)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: RoammateRadius.small, style: .continuous)
                .fill(Color.roammateSurface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: RoammateRadius.small, style: .continuous)
                .stroke(
                    selected.contains(item.id) ? Color.roammateIndigo : Color.roammateBorder,
                    lineWidth: selected.contains(item.id) ? 1.5 : 0.5
                )
        )
        .contentShape(Rectangle())
        .onTapGesture {
            if isSelecting {
                HapticManager.selection()
                if selected.contains(item.id) {
                    selected.remove(item.id)
                } else {
                    selected.insert(item.id)
                }
            } else {
                HapticManager.light()
                withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                    expandedId = expandedId == item.id ? nil : item.id
                }
            }
        }
    }

    @ViewBuilder
    private func expandedContent(for item: BrainstormItemOut) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Divider().padding(.vertical, 4)

            if let desc = item.description, !desc.isEmpty {
                Text(desc)
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(Color.roammateInk.opacity(0.8))
            }

            if let address = item.address, !address.isEmpty {
                HStack(spacing: 4) {
                    Image(systemName: "mappin")
                        .font(.system(size: 11))
                        .foregroundStyle(Color.roammateMuted)
                    Text(address)
                        .font(.system(.caption, design: .rounded))
                        .foregroundStyle(Color.roammateMuted)
                }
            }

            if let rating = item.rating, rating > 0 {
                HStack(spacing: 4) {
                    Image(systemName: "star.fill")
                        .font(.system(size: 11))
                        .foregroundStyle(Color.roammateAmber)
                    Text(String(format: "%.1f", rating))
                        .font(.system(.caption, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.roammateMuted)
                }
            }

            if let addedBy = item.addedBy, !addedBy.isEmpty {
                HStack(spacing: 4) {
                    Image(systemName: "person.fill")
                        .font(.system(size: 11))
                        .foregroundStyle(Color.roammateMuted)
                    Text("Added by \(addedBy)")
                        .font(.system(.caption, design: .rounded))
                        .foregroundStyle(Color.roammateMuted)
                }
            }

            if let url = item.photoUrl, let imageURL = URL(string: url) {
                AsyncImage(url: imageURL) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFill()
                            .frame(maxWidth: .infinity)
                            .frame(height: 120)
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    default:
                        EmptyView()
                    }
                }
            }
        }
    }

    private var bottomToolbar: some View {
        HStack(spacing: RoammateSpacing.md) {
            Button {
                let count = store.items.count
                Task {
                    await store.promote(itemIds: nil)
                    HapticManager.success()
                    withAnimation { toastMessage = "Sent \(count) items to Idea Bin" }
                }
            } label: {
                Text("Send all to Idea Bin")
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
            }
            .buttonStyle(RoammatePrimaryButtonStyle())

            if isSelecting && !selected.isEmpty {
                Button {
                    let ids = Array(selected)
                    Task {
                        await store.promote(itemIds: ids)
                        HapticManager.success()
                        withAnimation {
                            toastMessage = "Sent \(ids.count) items to Idea Bin"
                            selected.removeAll()
                            isSelecting = false
                        }
                    }
                } label: {
                    Text("Send \(selected.count)")
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                }
                .buttonStyle(RoammatePrimaryButtonStyle())
            }
        }
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 12)
        .background(Color.roammateSurface.shadow(.drop(radius: 8, y: -4)))
    }

    private func toastView(_ message: String) -> some View {
        Text(message)
            .font(.system(.subheadline, design: .rounded, weight: .semibold))
            .foregroundStyle(.white)
            .padding(.horizontal, 20)
            .padding(.vertical, 10)
            .background(Capsule().fill(Color.roammateIndigo))
            .padding(.top, RoammateSpacing.md)
    }
}
