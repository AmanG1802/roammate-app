import SwiftUI

struct TravellersStrip: View {
    let members: [TripMember]
    let canInvite: Bool
    let onInvite: () -> Void
    var darkBackground: Bool = false

    private let maxVisible = 5

    var body: some View {
        HStack(spacing: -10) {
            ForEach(members.prefix(maxVisible)) { member in
                AvatarCircle(name: member.user.name, avatarUrl: member.user.avatarUrl, darkBackground: darkBackground)
            }

            if members.count > maxVisible {
                ZStack {
                    Circle().fill(darkBackground ? Color.white.opacity(0.15) : Color.roammateIndigoTint)
                    Text("+\(members.count - maxVisible)")
                        .font(.system(.caption, design: .rounded, weight: .bold))
                        .foregroundStyle(darkBackground ? .white : Color.roammateIndigo)
                }
                .frame(width: 36, height: 36)
                .overlay(Circle().stroke(darkBackground ? Color.white.opacity(0.3) : Color.roammateBackground, lineWidth: 2))
            }

            if canInvite {
                Button(action: {
                    HapticManager.light()
                    onInvite()
                }) {
                    ZStack {
                        Circle().fill(Color.roammateIndigo)
                        Image(systemName: "plus")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundStyle(.white)
                    }
                    .frame(width: 36, height: 36)
                    .overlay(Circle().stroke(darkBackground ? Color.white.opacity(0.3) : Color.roammateBackground, lineWidth: 2))
                }
                .padding(.leading, 6)
                .buttonStyle(.plain)
            }
        }
    }
}

struct AvatarCircle: View {
    let name: String
    let avatarUrl: String?
    var darkBackground: Bool = false
    var size: CGFloat = 36

    private var initials: String {
        name.split(separator: " ")
            .prefix(2)
            .compactMap { $0.first.map(String.init) }
            .joined()
            .uppercased()
    }

    var body: some View {
        Group {
            if let avatarUrl, !avatarUrl.isEmpty {
                if avatarUrl.hasPrefix("data:"), let uiImage = UIImage.fromDataURI(avatarUrl) {
                    Image(uiImage: uiImage).resizable().scaledToFill()
                } else if let imageURL = URL(string: avatarUrl) {
                    AsyncImage(url: imageURL) { phase in
                        switch phase {
                        case .success(let image): image.resizable().scaledToFill()
                        default: initialsView
                        }
                    }
                } else {
                    initialsView
                }
            } else {
                initialsView
            }
        }
        .frame(width: size, height: size)
        .clipShape(Circle())
        .overlay(Circle().stroke(darkBackground ? Color.white.opacity(0.3) : Color.roammateBackground, lineWidth: 2))
    }

    private var initialsView: some View {
        ZStack {
            Circle().fill(darkBackground ? Color.white.opacity(0.15) : Color.roammateIndigoTint)
            Text(initials)
                .font(.system(size: size * 0.35, weight: .bold, design: .rounded))
                .foregroundStyle(darkBackground ? .white : Color.roammateIndigo)
        }
    }
}
