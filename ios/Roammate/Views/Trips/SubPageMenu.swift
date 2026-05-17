import SwiftUI

struct SubPageMenu: View {
    @Binding var currentPage: SubPage
    @Binding var isPresented: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Navigate")
                .font(.system(.headline, design: .rounded, weight: .bold))
                .foregroundStyle(Color.roammateInk)
                .padding(.horizontal, RoammateSpacing.lg)
                .padding(.top, RoammateSpacing.xl)
                .padding(.bottom, RoammateSpacing.md)

            ForEach(SubPage.allCases) { page in
                Button {
                    HapticManager.selection()
                    currentPage = page
                    withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                        isPresented = false
                    }
                } label: {
                    HStack(spacing: RoammateSpacing.md) {
                        Image(systemName: page.icon)
                            .font(.system(size: 18, weight: .medium))
                            .frame(width: 24)
                            .foregroundStyle(
                                page == currentPage ? Color.roammateIndigo : Color.roammateMuted
                            )

                        Text(page.rawValue)
                            .font(.system(.body, design: .rounded, weight: .medium))
                            .foregroundStyle(
                                page == currentPage ? Color.roammateIndigo : Color.roammateInk
                            )

                        Spacer()

                        if page == currentPage {
                            Image(systemName: "checkmark")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(Color.roammateIndigo)
                        } else {
                            Image(systemName: "chevron.right")
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(Color.roammateMuted.opacity(0.5))
                        }
                    }
                    .padding(.horizontal, RoammateSpacing.lg)
                    .padding(.vertical, 14)
                    .background(
                        page == currentPage
                            ? Color.roammateIndigoTint
                            : Color.clear
                    )
                }
                .buttonStyle(.plain)
            }

            Spacer()
        }
    }
}
