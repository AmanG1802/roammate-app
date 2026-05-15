import SwiftUI

struct DayTabsBar: View {
    let days: [TripDay]
    @Binding var selectedIndex: Int
    var eventCounts: [Date: Int] = [:]
    var onAddDay: (() -> Void)?

    var body: some View {
        HStack(spacing: 6) {
            Button {
                HapticManager.selection()
                withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                    selectedIndex = max(0, selectedIndex - 1)
                }
            } label: {
                Image(systemName: "chevron.left")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(selectedIndex <= 0 ? Color.roammateMuted.opacity(0.3) : Color.roammateInk)
                    .frame(width: 32, height: 36)
                    .background(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .fill(Color.roammateBackground)
                    )
            }
            .buttonStyle(.plain)
            .disabled(selectedIndex <= 0)

            ScrollViewReader { proxy in
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: RoammateSpacing.sm) {
                        ForEach(Array(days.enumerated()), id: \.element.id) { offset, day in
                            dayTab(day: day, index: offset, scrollProxy: proxy)
                                .id(offset)
                        }

                        if let onAddDay {
                            Button {
                                HapticManager.light()
                                onAddDay()
                            } label: {
                                HStack(spacing: 4) {
                                    Image(systemName: "plus")
                                        .font(.system(size: 12, weight: .bold))
                                    Text("Add Day")
                                        .font(.system(.caption, design: .rounded, weight: .semibold))
                                }
                                .foregroundStyle(Color.roammateIndigo)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(
                                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                                        .fill(Color.roammateIndigoTint)
                                )
                                .overlay(
                                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                                        .stroke(Color.roammateIndigo.opacity(0.3), lineWidth: 1)
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.horizontal, 4)
                    .padding(.vertical, RoammateSpacing.sm)
                }
                .onChange(of: selectedIndex) { _, newIdx in
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                        proxy.scrollTo(newIdx, anchor: .center)
                    }
                }
            }

            Button {
                HapticManager.selection()
                withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                    selectedIndex = min(days.count - 1, selectedIndex + 1)
                }
            } label: {
                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(selectedIndex >= days.count - 1 ? Color.roammateMuted.opacity(0.3) : Color.roammateInk)
                    .frame(width: 32, height: 36)
                    .background(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .fill(Color.roammateBackground)
                    )
            }
            .buttonStyle(.plain)
            .disabled(days.isEmpty || selectedIndex >= days.count - 1)
        }
        .padding(.horizontal, RoammateSpacing.sm)
    }

    private func dayTab(day: TripDay, index: Int, scrollProxy: ScrollViewProxy) -> some View {
        let isSelected = index == selectedIndex

        return Button {
            HapticManager.selection()
            withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                selectedIndex = index
            }
        } label: {
            Text("Day \(day.dayNumber)")
                .font(.system(.subheadline, design: .rounded, weight: .semibold))
                .foregroundStyle(isSelected ? .white : Color.roammateInk)
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
                .background(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(isSelected ? Color.roammateIndigo : Color.roammateBackground)
                )
        }
        .buttonStyle(.plain)
    }
}
