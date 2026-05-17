# Roammate iOS — Backend Layer Plan

"Backend" here means the iOS data layer: all models, networking, state
management, caching, and infrastructure that the UI sits on top of. The
FastAPI server is already built; this document is about the iOS side only.

---

## Current State (Baseline)

What exists today (see `00-overview.md` for detail):

- `APIClient` — generic HTTP client, auth injection, error handling
- `AuthService` — login, register, getMe
- `TripService` — getTrips, getTrip, createTrip, getTimeline, getIdeas (stub)
- `AuthManager` — global auth state store
- `KeychainHelper` — JWT storage
- Models: `User`, `Trip`, `TimelineItem`, `IdeaBinItem`

---

## Phase 1 — Complete API Coverage

Priority: get every existing FastAPI endpoint wired before building UI on top.
The backend has 6 domain areas. Each needs a Swift service and matching models.

---

### 1.1 Models to Add / Fix

**`TripDay.swift`** (new)
```swift
struct TripDay: Codable, Identifiable {
    let id: Int
    let tripId: Int
    let date: Date
    let dayNumber: Int
    // CodingKeys: trip_id, day_number
}
```

**`TripMember.swift`** (new)
```swift
struct TripMember: Codable, Identifiable {
    let id: Int
    let tripId: Int
    let userId: Int
    let role: String      // "admin" | "editor" | "viewer"
    let status: String    // "accepted" | "invited"
    let user: MemberUser?
}

struct MemberUser: Codable {
    let id: Int
    let name: String
    let email: String
    let avatarUrl: String?
}
```

**`Invitation.swift`** (new)
```swift
struct Invitation: Codable, Identifiable {
    let id: Int
    let tripId: Int
    let role: String
    let trip: TripSummary
    let inviter: InviterSummary?
}

struct TripSummary: Codable, Identifiable {
    let id: Int
    let name: String
    let startDate: Date?
}

struct InviterSummary: Codable {
    let name: String
    let email: String
}
```

**`Event.swift`** (rename `TimelineItem.swift`)
The events endpoint (`/events`) returns an `Event` schema that includes vote
counts. Update the model:
```swift
struct Event: Codable, Identifiable {
    // ... all place fields (same as TimelineItem) ...
    let dayDate: Date?
    let startTime: String?   // "14:30" — HH:mm string from backend
    let endTime: String?
    let up: Int              // upvote count
    let down: Int            // downvote count
    let myVote: Int          // -1 | 0 | 1
    // CodingKeys: day_date, start_time, end_time, my_vote
}
```

**`IdeaBinItem.swift`** — add vote fields (same pattern as Event):
```swift
let up: Int
let down: Int
let myVote: Int
```

**`Notification.swift`** (new)
```swift
struct AppNotification: Codable, Identifiable {
    let id: Int
    let type: String
    let payload: [String: AnyCodable]   // or a typed enum
    let isRead: Bool
    let createdAt: Date
    // CodingKeys: is_read, created_at
}
```

**`Group.swift`** (new)
```swift
struct Group: Codable, Identifiable {
    let id: Int
    let name: String
    let description: String?
    let memberCount: Int?
}
```

---

### 1.2 Services to Add

#### `EventService.swift`

Maps to `POST/GET/PATCH/DELETE /events` (note: events router is mounted
directly, not under `/trips`):

```swift
enum EventService {
    // GET /events/?trip_id={id}&day_date={date}
    static func getEvents(tripId: Int, dayDate: Date?) async throws -> [Event]

    // POST /events/
    static func createEvent(_ event: EventCreate) async throws -> Event

    // PATCH /events/{id}
    static func updateEvent(id: Int, update: EventUpdate) async throws -> Event

    // DELETE /events/{id}
    static func deleteEvent(id: Int) async throws

    // POST /events/{id}/move-to-bin
    static func moveToBin(eventId: Int) async throws -> IdeaBinItem

    // POST /events/ripple/{trip_id}   ← smart schedule reflow
    static func ripple(tripId: Int, request: RippleRequest) async throws -> [Event]
}
```

**Request bodies to add to `Models/`:**
```swift
struct EventCreate: Encodable {
    let tripId: Int
    let title: String
    let dayDate: Date?
    let startTime: String?
    let endTime: String?
    let category: String?
    // ... place fields
}

struct EventUpdate: Encodable {
    let title: String?
    let dayDate: Date?
    let startTime: String?
    let endTime: String?
    let timeCategory: String?
}
```

---

#### `TripDayService.swift`

```swift
enum TripDayService {
    // GET /trips/{id}/days
    static func getDays(tripId: Int) async throws -> [TripDay]

    // POST /trips/{id}/days
    static func addDay(tripId: Int, date: Date) async throws -> TripDay

    // DELETE /trips/{id}/days/{dayId}?items_action=bin|delete
    static func deleteDay(tripId: Int, dayId: Int, itemsAction: String) async throws
}
```

---

#### `MemberService.swift`

```swift
enum MemberService {
    // GET /trips/{id}/members
    static func getMembers(tripId: Int) async throws -> [TripMember]

    // POST /trips/{id}/invite  body: {email, role}
    static func invite(tripId: Int, email: String, role: String) async throws -> TripMember

    // DELETE /trips/{id}/members/{memberId}
    static func removeMember(tripId: Int, memberId: Int) async throws

    // PATCH /trips/{id}/members/{memberId}/role
    static func updateRole(tripId: Int, memberId: Int, role: String) async throws -> TripMember

    // GET /trips/invitations/pending
    static func getPendingInvitations() async throws -> [Invitation]

    // POST /trips/invitations/{memberId}/accept
    static func acceptInvitation(memberId: Int) async throws -> TripMember

    // DELETE /trips/invitations/{memberId}/decline
    static func declineInvitation(memberId: Int) async throws
}
```

---

#### `IdeaService.swift` (extend `TripService` or break out)

```swift
enum IdeaService {
    // GET /trips/{id}/ideas
    static func getIdeas(tripId: Int) async throws -> [IdeaBinItem]

    // DELETE /trips/{id}/ideas/{ideaId}
    static func deleteIdea(tripId: Int, ideaId: Int) async throws

    // PATCH /trips/{id}/ideas/{ideaId}
    static func updateIdea(tripId: Int, ideaId: Int, fields: IdeaUpdate) async throws -> IdeaBinItem

    // POST /trips/{id}/ingest  body: {text, source_url?}
    static func ingest(tripId: Int, text: String, sourceUrl: String?) async throws -> [IdeaBinItem]
}
```

---

#### `VoteService.swift`

Votes exist for both events and ideas. Check the votes endpoint for exact paths.
```swift
enum VoteService {
    static func voteEvent(eventId: Int, value: Int) async throws   // value: -1|0|1
    static func voteIdea(ideaId: Int, value: Int) async throws
}
```

---

#### `NotificationService.swift`

```swift
enum NotificationService {
    // GET /notifications/
    static func getNotifications() async throws -> [AppNotification]

    // GET /notifications/unread-count
    static func getUnreadCount() async throws -> Int

    // POST /notifications/{id}/read
    static func markRead(id: Int) async throws

    // POST /notifications/mark-all-read
    static func markAllRead() async throws
}
```

---

#### `ConciergeService.swift`

The AI concierge. These are the most important endpoints for Roammate's core
value proposition.

```swift
enum ConciergeService {
    // POST /concierge/{trip_id}/chat
    static func chat(tripId: Int, message: String, history: [ChatMessage]) async throws -> ConciergeChatResponse

    // POST /concierge/{trip_id}/execute
    static func execute(tripId: Int, action: ConciergeAction) async throws -> ExecuteResponse

    // POST /concierge/{trip_id}/find-nearby
    static func findNearby(tripId: Int, request: FindNearbyRequest) async throws -> FindNearbyResponse

    // GET /concierge/{trip_id}/whats-next
    static func whatsNext(tripId: Int) async throws -> WhatsNextResponse

    // GET /concierge/{trip_id}/today-summary
    static func todaySummary(tripId: Int) async throws -> TodaySummaryResponse
}
```

Models needed: `ChatMessage`, `ConciergeChatResponse`, `ConciergeAction`,
`ExecuteResponse`, `FindNearbyRequest`, `FindNearbyResponse`,
`WhatsNextResponse`, `TodaySummaryResponse`. These mirror the FastAPI Pydantic
schemas in `concierge.py` — map them 1:1.

---

#### `GroupService.swift`

```swift
enum GroupService {
    static func getGroups() async throws -> [Group]
    static func createGroup(name: String, description: String?) async throws -> Group
    static func getGroup(id: Int) async throws -> Group
    static func getGroupMembers(groupId: Int) async throws -> [TripMember]
    static func inviteToGroup(groupId: Int, email: String, role: String) async throws -> TripMember
    static func acceptGroupInvitation(memberId: Int) async throws -> TripMember
    static func declineGroupInvitation(memberId: Int) async throws
    static func getGroupTrips(groupId: Int) async throws -> [Trip]
    static func getGroupIdeas(groupId: Int) async throws -> [IdeaBinItem]
}
```

---

### 1.3 Update `TripService` to Cover Remaining Endpoints

```swift
// Add to TripService:
static func updateTrip(id: Int, update: TripUpdate) async throws -> Trip
static func deleteTrip(id: Int) async throws
```

---

## Phase 2 — State Stores (ViewModels)

Each major screen area needs a corresponding store that owns loading state,
error state, and the actual data. These are `@MainActor ObservableObject`
classes injected via `@StateObject` or `@EnvironmentObject`.

### Stores to build

**`TripStore.swift`**
```swift
@MainActor final class TripStore: ObservableObject {
    @Published var trips: [Trip] = []
    @Published var isLoading = false
    @Published var error: String?

    func load() async
    func create(_ trip: TripCreate) async
    func delete(id: Int) async
    func update(id: Int, update: TripUpdate) async
}
```

**`TripDetailStore.swift`**
Owns a single trip's full state: days, events per day, ideas, members.
```swift
@MainActor final class TripDetailStore: ObservableObject {
    let tripId: Int
    @Published var trip: Trip?
    @Published var days: [TripDay] = []
    @Published var eventsByDay: [Date: [Event]] = [:]
    @Published var ideas: [IdeaBinItem] = []
    @Published var members: [TripMember] = []

    func loadAll() async        // parallel: days + ideas + members
    func loadDay(_ date: Date) async
    func addDay(date: Date) async
    func deleteDay(id: Int, itemsAction: String) async
    func moveEventToBin(eventId: Int) async
    func voteEvent(eventId: Int, value: Int) async
    func voteIdea(ideaId: Int, value: Int) async
    func ingest(text: String, sourceUrl: String?) async
}
```

**`NotificationStore.swift`**
```swift
@MainActor final class NotificationStore: ObservableObject {
    @Published var notifications: [AppNotification] = []
    @Published var unreadCount: Int = 0

    func load() async
    func markRead(id: Int) async
    func markAllRead() async
}
```

**`ConciergeStore.swift`**
```swift
@MainActor final class ConciergeStore: ObservableObject {
    let tripId: Int
    @Published var messages: [ChatMessage] = []
    @Published var isThinking = false

    func send(message: String) async
    func whatsNext() async -> WhatsNextResponse?
    func todaySummary() async -> TodaySummaryResponse?
}
```

---

## Phase 3 — Token Expiry and Session Management

**Current gap:** If the JWT expires mid-session, any API call throws
`.unauthorized` but the app doesn't handle it globally — the error surfaces
per-screen.

**Plan:**

1. Add a global 401 handler in `APIClient`. When `.unauthorized` is thrown,
   post a `Notification` (not the app model — `NotificationCenter`):
   ```swift
   NotificationCenter.default.post(name: .sessionExpired, object: nil)
   ```

2. `AuthManager` observes this notification and calls `logout()`:
   ```swift
   .onReceive(NotificationCenter.default.publisher(for: .sessionExpired)) { _ in
       authManager.logout()
   }
   ```

3. The `ContentView` auth gate then automatically shows `LoginView`.

The backend uses stateless JWT (no refresh token endpoint exists yet). When
one is added, implement silent token refresh here by catching `.unauthorized`,
calling the refresh endpoint, storing the new token, and retrying the original
request once.

---

## Phase 4 — Caching and Offline Support

**Goal:** App feels instant on reopen; readable offline (no edits offline for
now).

### Strategy: In-memory + UserDefaults cache

For Phase 1 iOS, a simple `JSONEncoder`/`UserDefaults` cache is sufficient.
Do not reach for Core Data yet — the data model is not complex enough to
justify the overhead.

```swift
final class DiskCache {
    static let shared = DiskCache()
    private let defaults = UserDefaults.standard

    func store<T: Encodable>(_ value: T, key: String) {
        defaults.set(try? JSONEncoder().encode(value), forKey: key)
    }

    func load<T: Decodable>(_ type: T.Type, key: String) -> T? {
        guard let data = defaults.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(type, from: data)
    }
}
```

**Cache keys:**
- `"trips"` → `[Trip]`
- `"trip_\(id)_days"` → `[TripDay]`
- `"trip_\(id)_ideas"` → `[IdeaBinItem]`
- `"notifications"` → `[AppNotification]`

**Pattern in stores:** Load from cache first (instant display), then fetch from
network and update:
```swift
func load() async {
    if trips.isEmpty {
        trips = DiskCache.shared.load([Trip].self, key: "trips") ?? []
    }
    let fresh = try? await TripService.getTrips()
    if let fresh {
        trips = fresh
        DiskCache.shared.store(fresh, key: "trips")
    }
}
```

---

## Phase 5 — Push Notifications (APNs)

**Prerequisites:** Apple Developer Program ($99/yr), a production server with
the ability to send APNs payloads.

### Steps

1. **Enable Push capability in Xcode** (Signing & Capabilities → Push
   Notifications)

2. **Register for remote notifications** in `RoammateApp.swift`:
   ```swift
   UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, _ in
       guard granted else { return }
       DispatchQueue.main.async { UIApplication.shared.registerForRemoteNotifications() }
   }
   ```

3. **Send device token to backend** — add an endpoint to FastAPI:
   ```
   POST /users/me/device-token   body: {token: String, platform: "ios"}
   ```
   Call this from `AppDelegate.application(_:didRegisterForRemoteNotificationsWithDeviceToken:)`.

4. **Backend sends APNs payloads** using the device token when
   `notification_service.emit()` fires (the same events already wired for
   in-app notifications: `TRIP_CREATED`, `INVITE_RECEIVED`, etc.)

5. **Handle foreground notifications** — conform to
   `UNUserNotificationCenterDelegate` to show banners when app is open.

6. **Deep link from notification tap** — pass `tripId` in the APNs payload and
   navigate to `TripDetailView` on open.

---

## Phase 6 — MapKit Integration

The trip planner needs a map. Use **MapKit** (native, free, no API key for
basic display).

### Plan

**`MapService.swift`**
```swift
enum MapService {
    // Wraps backend GET /trips/{id}/map/markers (maps.py endpoint)
    static func getMarkers(tripId: Int) async throws -> [MapMarker]

    // Local geocoding (no backend call needed)
    static func geocode(query: String) async throws -> CLLocationCoordinate2D
}

struct MapMarker: Codable, Identifiable {
    let id: Int
    let title: String
    let lat: Double
    let lng: Double
    let category: String?
    let source: String    // "timeline" | "idea_bin"
}
```

**`TripMapView.swift`** — SwiftUI Map view showing all timeline + idea bin
items as pins, color-coded by source.
```swift
import MapKit

struct TripMapView: View {
    let markers: [MapMarker]

    var body: some View {
        Map {
            ForEach(markers) { marker in
                Marker(marker.title, coordinate: .init(
                    latitude: marker.lat, longitude: marker.lng
                ))
                .tint(marker.source == "timeline" ? .blue : .orange)
            }
        }
    }
}
```

---

## Phase 7 — Configuration and Environment

**`Config.swift`** — single source of truth for environment-specific values:
```swift
enum Config {
    static var apiBaseURL: String {
        #if DEBUG
        return ProcessInfo.processInfo.environment["API_BASE_URL"] ?? "http://localhost:8000/api"
        #else
        return "https://api.roammate.app/api"
        #endif
    }
}
```

This lets you override `API_BASE_URL` per Xcode scheme (Edit Scheme →
Run → Arguments → Environment Variables), useful for pointing a physical
device at your dev server without hardcoding your local IP.

---

## Phase 8 — Error Handling Improvements

Current `APIError` is functional but surfaces raw server messages. Improve:

1. **Parse FastAPI `detail` field** from error JSON:
   ```swift
   private struct APIErrorBody: Decodable {
       let detail: String
   }
   ```
   In `APIClient.request()`, attempt to decode this before falling back to
   raw string.

2. **Retry logic for network errors** (not server errors):
   ```swift
   func request<T>(..., retries: Int = 2) async throws -> T {
       do { return try await _request(...) }
       catch APIError.networkError where retries > 0 {
           return try await request(..., retries: retries - 1)
       }
   }
   ```

3. **User-facing error presentation** — a shared `ErrorBanner` view modifier
   that any screen can attach:
   ```swift
   .errorBanner($viewModel.error)
   ```

---

## Implementation Order (Recommended)

Work through these in sequence — each phase unblocks the next.

| # | Task | Unlocks |
|---|---|---|
| 1 | Add `TripDay`, `TripMember`, `Invitation`, `Event` (with votes) models | Services |
| 2 | `TripDayService`, `EventService`, `IdeaService`, `VoteService` | TripDetailStore |
| 3 | `MemberService` (invitations + member management) | Collaboration UI |
| 4 | `TripDetailStore` (the most complex store) | Trip planner screen |
| 5 | `NotificationService` + `NotificationStore` | Notification badge |
| 6 | `ConciergeService` + `ConciergeStore` | AI chat screen |
| 7 | `GroupService` + `GroupStore` | Groups screen |
| 8 | Global 401 handler + session expiry | Robust auth |
| 9 | `DiskCache` + stale-while-revalidate in all stores | Offline / speed |
| 10 | `Config.swift` + scheme-based URL override | Physical device dev |
| 11 | MapKit integration | Map tab |
| 12 | APNs setup | Push notifications |

---

## File Structure After Full Implementation

```
ios/Roammate/
├── App/
│   └── RoammateApp.swift
├── Models/
│   ├── User.swift
│   ├── Trip.swift             (+ TripCreate, TripUpdate, TripWithRole)
│   ├── TripDay.swift          (new)
│   ├── TripMember.swift       (new)
│   ├── Invitation.swift       (new)
│   ├── Event.swift            (replaces TimelineItem — adds votes, day_date)
│   ├── IdeaBinItem.swift      (add vote fields)
│   ├── Notification.swift     (new)
│   ├── Group.swift            (new)
│   └── Concierge.swift        (new — chat/action request+response types)
├── Network/
│   ├── APIClient.swift
│   ├── AuthService.swift
│   ├── TripService.swift
│   ├── TripDayService.swift   (new)
│   ├── EventService.swift     (new)
│   ├── IdeaService.swift      (new)
│   ├── MemberService.swift    (new)
│   ├── VoteService.swift      (new)
│   ├── NotificationService.swift (new)
│   ├── ConciergeService.swift (new)
│   ├── GroupService.swift     (new)
│   └── MapService.swift       (new)
├── Store/
│   ├── AuthManager.swift
│   ├── TripStore.swift        (new)
│   ├── TripDetailStore.swift  (new)
│   ├── NotificationStore.swift (new)
│   ├── ConciergeStore.swift   (new)
│   └── GroupStore.swift       (new)
├── Utils/
│   ├── KeychainHelper.swift
│   ├── DiskCache.swift        (new)
│   └── Config.swift           (new)
└── Views/
    └── ... (frontend, separate plan)
```
