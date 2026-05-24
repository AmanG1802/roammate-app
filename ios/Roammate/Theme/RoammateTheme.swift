import SwiftUI

// MARK: - Color tokens

extension Color {
    /// #4F46E5 — primary CTA, selected nav, links
    static let roammateIndigo = Color(red: 79/255, green: 70/255, blue: 229/255)
    /// #4338CA — pressed / dark variant
    static let roammateIndigoDark = Color(red: 67/255, green: 56/255, blue: 202/255)
    /// #EDE9FE — subtle indigo tint (badges, hover states)
    static let roammateIndigoTint = Color(red: 237/255, green: 233/255, blue: 254/255)
    /// #A5B4FC — light indigo (accent text / icons on dark surfaces)
    static let roammateIndigo300 = Color(red: 165/255, green: 180/255, blue: 252/255)
    /// #C7D2FE — lighter indigo (accent text on the indigo finale card)
    static let roammateIndigo200 = Color(red: 199/255, green: 210/255, blue: 254/255)

    /// #0F172A — primary text
    static let roammateInk = Color(red: 15/255, green: 23/255, blue: 42/255)
    /// #64748B — secondary text
    static let roammateMuted = Color(red: 100/255, green: 116/255, blue: 139/255)

    /// #FFFFFF — card surface
    static let roammateSurface = Color.white
    /// #F8FAFC — app background
    static let roammateBackground = Color(red: 248/255, green: 250/255, blue: 252/255)
    /// #E2E8F0 — border / divider
    static let roammateBorder = Color(red: 226/255, green: 232/255, blue: 240/255)

    /// #10B981 — success / accepted
    static let roammateSuccess = Color(red: 16/255, green: 185/255, blue: 129/255)
    /// #F43F5E — destructive / declined
    static let roammateDanger = Color(red: 244/255, green: 63/255, blue: 94/255)
    /// #F59E0B — amber / "next up" highlights
    static let roammateAmber = Color(red: 245/255, green: 158/255, blue: 11/255)
    /// Amber tint for brainstorm bin header
    static let roammateAmberTint = Color(red: 255/255, green: 251/255, blue: 235/255)

    /// #F43F5E — rose (Idea Bin accent; same hue as danger, semantic name for marketing surfaces)
    static let roammateRose = Color(red: 244/255, green: 63/255, blue: 94/255)
    /// #FFF1F2 — rose tint (Idea Bin eyebrow pill background)
    static let roammateRoseTint = Color(red: 255/255, green: 241/255, blue: 242/255)

    /// #8B5CF6 — violet
    static let roammateViolet = Color(red: 139/255, green: 92/255, blue: 246/255)
    static let roammateVioletTint = Color(red: 245/255, green: 243/255, blue: 255/255)

    /// #10B981 — emerald
    static let roammateEmerald = Color(red: 16/255, green: 185/255, blue: 129/255)
    static let roammateEmeraldTint = Color(red: 236/255, green: 253/255, blue: 245/255)

    /// #0EA5E9 — sky
    static let roammateSky = Color(red: 14/255, green: 165/255, blue: 233/255)
    static let roammateSkyTint = Color(red: 240/255, green: 249/255, blue: 255/255)

    /// #F97316 — orange
    static let roammateOrange = Color(red: 249/255, green: 115/255, blue: 22/255)
    static let roammateOrangeTint = Color(red: 255/255, green: 247/255, blue: 237/255)

    /// #EC4899 — pink
    static let roammatePink = Color(red: 236/255, green: 72/255, blue: 153/255)
    static let roammatePinkTint = Color(red: 253/255, green: 242/255, blue: 248/255)

    /// #D946EF — fuchsia (entertainment)
    static let roammateFuchsia = Color(red: 217/255, green: 70/255, blue: 239/255)
    static let roammateFuchsiaTint = Color(red: 253/255, green: 244/255, blue: 255/255)

    /// #14B8A6 — teal (sports/adventure)
    static let roammateTeal = Color(red: 20/255, green: 184/255, blue: 166/255)
    static let roammateTealTint = Color(red: 240/255, green: 253/255, blue: 250/255)

    /// #7C3AED — purple (nightlife)
    static let roammatePurple = Color(red: 124/255, green: 58/255, blue: 237/255)
    static let roammatePurpleTint = Color(red: 245/255, green: 243/255, blue: 255/255)

    /// #78716C — stone (religious)
    static let roammateStone = Color(red: 120/255, green: 113/255, blue: 108/255)
    static let roammateStoneTint = Color(red: 245/255, green: 245/255, blue: 244/255)

    /// #EAB308 — yellow (landmarks)
    static let roammateYellow = Color(red: 234/255, green: 179/255, blue: 8/255)
    static let roammateYellowTint = Color(red: 254/255, green: 252/255, blue: 232/255)

    /// #3B82F6 — blue (accommodation)
    static let roammateBlue = Color(red: 59/255, green: 130/255, blue: 246/255)
    static let roammateBlueTint = Color(red: 239/255, green: 246/255, blue: 255/255)

    /// #64748B — slate (transport)
    static let roammateSlate = Color(red: 100/255, green: 116/255, blue: 139/255)
    static let roammateSlateTint = Color(red: 241/255, green: 245/255, blue: 249/255)

    // MARK: - Category keyword groups (matches web categoryColors.ts)

    private static func matches(_ text: String, _ keywords: [String]) -> Bool {
        keywords.contains { text.contains($0) }
    }

    private enum CategoryGroup {
        case food, culture, nature, shopping, accommodation, transport
        case entertainment, sportsAdventure, wellnessSpa, religious
        case nightlife, landmarks, activities

        static func resolve(_ category: String?) -> CategoryGroup? {
            guard let cat = category?.lowercased() else { return nil }

            if matches(cat, ["food", "restaurant", "caf", "dining", "eat", "pub", "bistro", "bakery",
                             "cuisine", "brunch", "breakfast", "lunch", "dinner", "snack", "dessert",
                             "ice cream", "pizza", "sushi", "ramen", "noodle", "street food",
                             "seafood", "buffet"]) { return .food }

            if matches(cat, ["museum", "art", "cultur", "history", "gallery", "theater", "theatre",
                             "monument", "exhibit", "heritage", "archeolog", "archaeolog", "palace",
                             "castle", "ruin"]) { return .culture }

            if matches(cat, ["nature", "park", "beach", "outdoor", "garden", "hiking", "trail",
                             "waterfall", "lake", "forest", "mountain", "island", "canyon",
                             "reserve", "wildlife", "jungle", "cliff", "valley"]) { return .nature }

            if matches(cat, ["shop", "mall", "market", "boutique", "store", "souvenir", "retail",
                             "bazaar", "flea", "duty free"]) { return .shopping }

            if matches(cat, ["hotel", "hostel", "resort", "airbnb", "stay", "accommodation",
                             "lodg", "inn", "motel", "villa", "apartment", "rental"]) { return .accommodation }

            if matches(cat, ["airport", "train", "bus", "transport", "transit", "ferry", "port",
                             "station", "subway", "metro", "taxi", "transfer", "flight",
                             "commute"]) { return .transport }

            if matches(cat, ["entertainment", "theme park", "amusement", "cinema", "movie",
                             "concert", "show", "perform", "festival", "fair", "carnival",
                             "circus", "zoo", "aquarium"]) { return .entertainment }

            if matches(cat, ["sport", "adventure", "surf", "dive", "scuba", "snorkel", "ski",
                             "climb", "kayak", "cycle", "bike", "swim", "water sport",
                             "skydiv", "bungee", "trek", "rafting"]) { return .sportsAdventure }

            if matches(cat, ["spa", "wellness", "massage", "yoga", "meditat", "gym", "fitness",
                             "sauna", "thermal", "hot spring", "retreat"]) { return .wellnessSpa }

            if matches(cat, ["church", "cathedral", "temple", "mosque", "shrine", "monastery",
                             "chapel", "religious", "spiritual", "sacred", "pagoda",
                             "stupa"]) { return .religious }

            if matches(cat, ["nightlife", "club", "nightclub", "lounge", "rooftop", "cocktail",
                             "bar crawl", "party", "disco", "bar"]) { return .nightlife }

            if matches(cat, ["landmark", "viewpoint", "view", "lookout", "panorama", "observation",
                             "tower", "bridge", "square", "plaza", "sight"]) { return .landmarks }

            if matches(cat, ["activity", "experience", "tour", "class", "workshop", "lesson",
                             "cooking", "craft"]) { return .activities }

            return nil
        }
    }

    static func categoryColor(_ category: String?) -> Color {
        switch CategoryGroup.resolve(category) {
        case .food:             return .roammateAmber
        case .culture:          return .roammateViolet
        case .nature:           return .roammateEmerald
        case .shopping:         return .roammatePink
        case .accommodation:    return .roammateBlue
        case .transport:        return .roammateSlate
        case .entertainment:    return .roammateFuchsia
        case .sportsAdventure:  return .roammateTeal
        case .wellnessSpa:      return .roammatePink
        case .religious:        return .roammateStone
        case .nightlife:        return .roammatePurple
        case .landmarks:        return .roammateYellow
        case .activities:       return .roammateOrange
        case nil:               return .roammateMuted
        }
    }

    static func categoryTint(_ category: String?) -> Color {
        switch CategoryGroup.resolve(category) {
        case .food:             return .roammateAmberTint
        case .culture:          return .roammateVioletTint
        case .nature:           return .roammateEmeraldTint
        case .shopping:         return .roammatePinkTint
        case .accommodation:    return .roammateBlueTint
        case .transport:        return .roammateSlateTint
        case .entertainment:    return .roammateFuchsiaTint
        case .sportsAdventure:  return .roammateTealTint
        case .wellnessSpa:      return .roammatePinkTint
        case .religious:        return .roammateStoneTint
        case .nightlife:        return .roammatePurpleTint
        case .landmarks:        return .roammateYellowTint
        case .activities:       return .roammateOrangeTint
        case nil:               return .roammateSlateTint
        }
    }

    static func categoryIcon(_ category: String?) -> String {
        switch CategoryGroup.resolve(category) {
        case .food:             return "fork.knife"
        case .culture:          return "building.columns"
        case .nature:           return "leaf.fill"
        case .shopping:         return "bag.fill"
        case .accommodation:    return "bed.double.fill"
        case .transport:        return "car.fill"
        case .entertainment:    return "theatermasks.fill"
        case .sportsAdventure:  return "figure.hiking"
        case .wellnessSpa:      return "sparkles"
        case .religious:        return "building.2.fill"
        case .nightlife:        return "moon.stars.fill"
        case .landmarks:        return "binoculars.fill"
        case .activities:       return "ticket.fill"
        case nil:               return "mappin"
        }
    }
}

// MARK: - Plus brand gradient

enum RoammateGradient {
    /// The Roammate Plus brand gradient (indigo → fuchsia → amber).
    /// Reserved exclusively for Plus surfaces — never appears on free-tier
    /// elements. Apply as a fill, foregroundStyle, or angular shimmer.
    static let plus = LinearGradient(
        colors: [
            Color(red: 79/255, green: 70/255, blue: 229/255),   // indigo
            Color(red: 217/255, green: 70/255, blue: 239/255),  // fuchsia
            Color(red: 245/255, green: 158/255, blue: 11/255),  // amber
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// Angular version used by the crest shimmer.
    static func plusAngular(angle: Angle) -> AngularGradient {
        AngularGradient(
            colors: [
                Color(red: 79/255, green: 70/255, blue: 229/255),
                Color(red: 217/255, green: 70/255, blue: 239/255),
                Color(red: 245/255, green: 158/255, blue: 11/255),
                Color(red: 79/255, green: 70/255, blue: 229/255),
            ],
            center: .center,
            angle: angle
        )
    }
}

// MARK: - Sizing tokens

enum RoammateRadius {
    static let pill: CGFloat = 999      // used with Capsule()
    static let button: CGFloat = 18
    static let card: CGFloat = 32
    static let widget: CGFloat = 36
    static let small: CGFloat = 12
}

enum RoammateSpacing {
    static let xs: CGFloat = 4
    static let sm: CGFloat = 8
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
}

enum RoammateShadow {
    /// Soft indigo-tinted card shadow (matches web `shadow-xl shadow-indigo-900/5`).
    static let card = (
        color: Color.roammateIndigo.opacity(0.08),
        radius: CGFloat(24),
        x: CGFloat(0),
        y: CGFloat(8)
    )

    /// Heavier shadow for floating elements (FAB, tab bar).
    static let floating = (
        color: Color.roammateInk.opacity(0.12),
        radius: CGFloat(20),
        x: CGFloat(0),
        y: CGFloat(6)
    )

    /// Pressed-state inner glow tint (used on indigo CTAs).
    static let indigoGlow = (
        color: Color.roammateIndigo.opacity(0.35),
        radius: CGFloat(16),
        x: CGFloat(0),
        y: CGFloat(4)
    )
}

// MARK: - Layout constants

enum RoammateLayout {
    /// Visual height of the floating tab bar including its internal padding.
    static let tabBarHeight: CGFloat = 56
    /// Distance from the screen bottom inset where the pill sits.
    static let tabBarBottomInset: CGFloat = 16
    /// Bottom padding any scrollable view should add so its last row clears the tab bar.
    static let contentBottomPadding: CGFloat = tabBarHeight + tabBarBottomInset + 16
}
