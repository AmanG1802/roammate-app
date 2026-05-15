# Roammate iOS — Project Overview

## What Has Been Set Up

This document is a point-in-time record of what exists in the `ios/` directory
as of the initial scaffold (May 2026). Use it as a foundation before diving
deeper into any layer.

---

## Repository Structure

The iOS app lives inside the existing Roammate monorepo, alongside the web
frontend and Python backend. No separate repo is needed.

```
roammate-app/
├── backend/          # FastAPI + PostgreSQL + Redis (existing)
├── frontend/         # Next.js 14 App Router (existing)
├── ios/              # ← new
│   ├── project.yml   # xcodegen manifest — generates .xcodeproj
│   ├── .gitignore    # Excludes DerivedData, xcuserdata
│   ├── docs-ios/     # This directory
│   └── Roammate/
│       ├── App/
│       ├── Models/
│       ├── Network/
│       ├── Store/
│       ├── Utils/
│       └── Views/
```

---

## Toolchain Decisions

| Tool | Purpose | Why |
|---|---|---|
| **Swift 5.9** | Language | Current stable, ships with Xcode 15 |
| **SwiftUI** | UI framework | Declarative, first-class Apple support, suited for new projects |
| **xcodegen** | Project file generation | `project.yml` is human-readable and git-diffable; raw `.xcodeproj` XML is not |
| **URLSession + async/await** | Networking | Zero dependencies, native Swift concurrency, matches FastAPI's async model |
| **Keychain** | Token storage | Secure enclave-backed; never store JWT in UserDefaults |
| **No third-party dependencies yet** | — | Kept intentionally lean for Phase 1 |

---

## How to Generate and Open the Project

```bash
# One-time install
brew install xcodegen

# From repo root, every time project.yml changes
cd ios && xcodegen generate

# Open in Xcode
open ios/Roammate.xcodeproj
```

The generated `.xcodeproj` **should be committed** to git so teammates can
open without running xcodegen themselves. Only `DerivedData/` and
`xcuserdata/` are gitignored.

---

## Files Created and What They Do

### App Entry Point

**`App/RoammateApp.swift`**
The `@main` struct. Creates `AuthManager` as a `@StateObject`, injects it into
the SwiftUI environment, and calls `authManager.checkAuth()` on launch to
silently restore session from Keychain.

---

### Models (`Models/`)

Swift `Codable` structs that mirror the FastAPI Pydantic response schemas.
All snake_case → camelCase mapping is handled via `CodingKeys`.

| File | Maps to |
|---|---|
| `User.swift` | `UserOut` in `users.py` |
| `Trip.swift` | `TripWithRole` / `TripSchema` in `trips.py` |
| `TimelineItem.swift` | `Event` schema (place fields + trip_id) |
| `IdeaBinItem.swift` | `IdeaBinItem` schema (same place fields) |

All date fields use `.iso8601` decoding strategy configured on the shared
`JSONDecoder` in `APIClient`.

**`Trip.swift` also includes `TripCreate`** — the request body struct for
`POST /trips`.

---

### Network Layer (`Network/`)

**`APIClient.swift`** — The single HTTP entry point.
- Singleton: `APIClient.shared`
- Base URL switches between `localhost:8000` (DEBUG) and
  `api.roammate.app` (RELEASE) via compile-time `#if DEBUG`
- Generic `request<T: Decodable>()` function handles: URL building, JSON
  encoding of request bodies, Bearer token injection from Keychain, HTTP
  status checking (401 → `.unauthorized`, 4xx/5xx → `.serverError`), and
  JSON decoding into the expected type
- `APIError` enum conforms to `LocalizedError` so error messages surface
  naturally in SwiftUI

**`AuthService.swift`** — Wraps auth endpoints.
- `login(email:password:)` → `POST /api/users/login` → returns raw token string
- `register(name:email:password:)` → `POST /api/users/register` → returns `User`
- `getMe()` → `GET /api/users/me` → returns `User`

**`TripService.swift`** — Wraps trip endpoints (initial subset).
- `getTrips()` → `GET /api/trips`
- `getTrip(id:)` → `GET /api/trips/{id}`
- `createTrip(_:)` → `POST /api/trips`
- `getTimeline(tripId:)` → `GET /api/trips/{id}/timeline` (endpoint TBD)
- `getIdeas(tripId:)` → `GET /api/trips/{id}/ideas`

---

### State Management (`Store/`)

**`AuthManager.swift`** — The global auth store. Analogous to the Zustand
auth slice in the web frontend.
- `@MainActor` class (all UI updates on main thread automatically)
- `@Published var currentUser: User?` and `@Published var isAuthenticated`
- `checkAuth()` — called on app launch; loads token from Keychain, calls
  `GET /users/me`, sets state or clears token on failure
- `login()`, `register()`, `logout()` — each wraps the appropriate
  `AuthService` call and updates published state

---

### Utils (`Utils/`)

**`KeychainHelper.swift`** — Static helper for JWT storage.
- `saveToken(_:)` — deletes existing entry then writes new one (no-update
  path avoids Keychain collision errors)
- `loadToken()` — returns `String?`, nil if nothing stored
- `deleteToken()` — called on logout

Uses `kSecClassGenericPassword` with `service = "com.roammate.app"` and
`account = "auth_token"`.

---

### Views (`Views/`)

Intentionally minimal placeholders — enough to prove auth flow and API
connectivity. Visual design will be defined separately.

| File | Role |
|---|---|
| `ContentView.swift` | Auth gate: if authenticated → `MainTabView`, else → `LoginView`. Animated transition. |
| `Auth/LoginView.swift` | Email + password form. Calls `authManager.login()`. Sheet to `RegisterView`. |
| `Auth/RegisterView.swift` | Name + email + password form. Calls `authManager.register()`. |
| `Main/MainTabView.swift` | Two-tab shell: Trips + Profile. Profile tab has logout. |
| `Trips/TripListView.swift` | Fetches and lists trips. Pull-to-refresh. Empty state. `+` → `CreateTripView`. |
| `Trips/TripDetailView.swift` | Fetches timeline and ideas in parallel (`async let`). |
| `Trips/CreateTripView.swift` | Name + date picker form. `POST /trips`. Calls `onCreated` closure on success. |

---

## Architecture Pattern

The app uses a lightweight **MVVM** pattern:

```
View → ViewModel (@StateObject) → Service (enum with static funcs) → APIClient
                                                                          ↓
                                                                    URLSession
```

- **Views** own their ViewModel via `@StateObject` or read global state from
  `@EnvironmentObject`
- **ViewModels** are `@MainActor` classes with `@Published` properties
- **Services** are stateless `enum` namespaces with `static async throws` functions
- **APIClient** is a singleton with the generic `request<T>()` method

This mirrors the structure of the web frontend (component → Zustand store →
fetch call) in a way that will feel familiar.

---

## Connection to the FastAPI Backend

The iOS app is a native client for the **same REST API** the web frontend uses.
No backend changes are needed to support the iOS app in Phase 1.

- In DEBUG (Simulator): connects to `http://localhost:8000/api` — same
  machine, same network
- On a physical device during dev: change `baseURL` in `APIClient.swift`
  to your Mac's local IP (e.g. `http://192.168.1.x:8000/api`)
- In RELEASE: `https://api.roammate.app/api` (domain TBD at deploy time)

`NSAllowsLocalNetworking: true` is set in `project.yml` so the iOS simulator
can reach `http://localhost` without App Transport Security blocking it.

---

## What Is NOT Yet Done

- Complete API surface coverage (only auth + trips stubbed; events, days,
  members, invitations, notifications, groups, concierge not yet wired)
- Caching / offline support
- Push notifications (APNs)
- MapKit integration
- Visual design / UI polish
- Token expiry handling / silent refresh
- App icon and splash screen
- TestFlight / App Store deployment setup

All of the above is covered in `01-backend-plan.md`.
