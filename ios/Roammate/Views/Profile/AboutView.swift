import SwiftUI

struct AboutView: View {
    private var version: String {
        let v = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0"
        let b = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1"
        return "v\(v) (\(b))"
    }

    var body: some View {
        List {
            Section {
                HStack {
                    Text("Version").foregroundStyle(Color.roammateInk)
                    Spacer()
                    Text(version).foregroundStyle(Color.roammateMuted)
                }
            }
            Section {
                Link(destination: URL(string: "https://roammate.app/privacy")!) {
                    Label("Privacy Policy", systemImage: "lock")
                }
                Link(destination: URL(string: "https://roammate.app/terms")!) {
                    Label("Terms of Service", systemImage: "doc.text")
                }
            }
        }
        .navigationTitle("About")
        .navigationBarTitleDisplayMode(.inline)
    }
}
