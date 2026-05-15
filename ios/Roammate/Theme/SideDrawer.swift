import SwiftUI

struct SideDrawerModifier<DrawerContent: View>: ViewModifier {
    @Binding var isPresented: Bool
    @ViewBuilder let drawerContent: () -> DrawerContent

    private let drawerWidth: CGFloat = 320

    func body(content: Content) -> some View {
        content
            .overlay {
                if isPresented {
                    Color.black.opacity(0.3)
                        .ignoresSafeArea()
                        .onTapGesture {
                            withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                                isPresented = false
                            }
                        }
                        .transition(.opacity)
                }
            }
            .overlay(alignment: .trailing) {
                if isPresented {
                    drawerContent()
                        .frame(width: drawerWidth)
                        .frame(maxHeight: .infinity)
                        .background(Color.roammateSurface.ignoresSafeArea())
                        .transition(.move(edge: .trailing))
                }
            }
            .animation(.spring(response: 0.35, dampingFraction: 0.85), value: isPresented)
    }
}

extension View {
    func sideDrawer<Content: View>(
        isPresented: Binding<Bool>,
        @ViewBuilder content: @escaping () -> Content
    ) -> some View {
        modifier(SideDrawerModifier(isPresented: isPresented, drawerContent: content))
    }
}
