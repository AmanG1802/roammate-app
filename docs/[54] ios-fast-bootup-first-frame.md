# [52] iOS Fast Bootup & First Frame Visibility

## Context

The iOS app shows a white screen for 20–30 seconds before the login page or intro cards appear. Two layered causes were identified via code archaeology:

1. **Synchronous DiskCache reads on the main thread block the first SwiftUI frame.** `TripStore`, `GroupStore`, and `NotificationStore` call `DiskCache.shared.load()` inside `init()`. Because `@StateObject` objects are instantiated during `RoammateApp.body`'s first evaluation — before SwiftUI commits the first frame — these synchronous `Data(contentsOf:)` file reads and JSON decodes stall the render pipeline. `DiskCache.init()` also runs `migrateFromUserDefaults()` synchronously, iterating all of `UserDefaults` on the main thread.

2. **No URLSession timeout means a slow or unreachable backend causes `checkAuth()` to hang for 60 s per attempt × 3 retries = up to 180 s worst-case.** Even though `checkAuth()` is async (so `LoginView` renders while it runs), authenticated users who open the app and immediately try to navigate see stale/empty UI for the full duration of the hanging network calls. On non-free-tier Railway but with transient network issues or cold-adjacent container warmup, a 10–20 s first-response latency is common.

**Goal:** first-paint in ≤ 1 frame after launch; authenticated users see `MainShell` with cached data instantly; all network work deferred to background.

---

## Implementation Plan

### 1. Optimistic Auth — `AuthManager.checkAuth()`
**File:** `ios/Roammate/Store/AuthManager.swift`

Replace the current blocking `checkAuth()` with a two-phase pattern:

- **Fast path (has access token):** Set `isAuthenticated = true` immediately, then validate in background via a private `_validateInBackground()` helper. No `await` in the fast path — caller returns immediately.
- **Slow path (has refresh token, no access token):** Keep current behavior (must exchange for a token before showing MainShell).
- **Background validation helper:** Call `AuthService.getMe()` with `retries: 0`. On `.unauthorized` → attempt one silent refresh; if that also fails → `logout()`. On any other network error → silently keep the authenticated state (user works offline with stale data; next foreground cycle retries).

```swift
func checkAuth() async {
    if KeychainHelper.loadToken() != nil {
        isAuthenticated = true          // instant — show MainShell now
        Task { await _validateInBackground() }
        return
    }
    // slow path: refresh exchange (unchanged from current)
    guard let raw = KeychainHelper.loadRefreshToken() else { return }
    do {
        let pair = try await AuthService.refresh(refreshToken: raw)
        KeychainHelper.saveToken(pair.access_token)
        KeychainHelper.saveRefreshToken(pair.refresh_token)
        currentUser = try await AuthService.getMe()
        isAuthenticated = true
    } catch { KeychainHelper.clearAll() }
}

private func _validateInBackground() async {
    do {
        currentUser = try await AuthService.getMe()
    } catch let e as APIError {
        if case .unauthorized = e {
            // expired — try one silent refresh then give up
            guard let raw = KeychainHelper.loadRefreshToken() else { logout(); return }
            do {
                let pair = try await AuthService.refresh(refreshToken: raw)
                KeychainHelper.saveToken(pair.access_token)
                KeychainHelper.saveRefreshToken(pair.refresh_token)
                currentUser = try await AuthService.getMe()
            } catch { logout() }
        }
        // network error: keep authenticated, retry on next foreground
    }
}
```

**Impact:** Authenticated users see `MainShell` in the same frame as app launch. The backend round-trip is invisible.

---

### 2. Async DiskCache Reads — stores + DiskCache itself

#### 2a. Add `loadAsync` to `DiskCache`
**File:** `ios/Roammate/Utils/DiskCache.swift`

Add an async variant that dispatches the file read onto the existing `queue` (already `.utility` QoS):

```swift
func loadAsync<T: Decodable>(_ type: T.Type, key: String) async -> T? {
    await withCheckedContinuation { cont in
        queue.async {
            let url = self.fileURL(for: key)
            guard let data = try? Data(contentsOf: url) else { cont.resume(returning: nil); return }
            cont.resume(returning: try? self.decoder.decode(type, from: data))
        }
    }
}
```

Move `migrateFromUserDefaults()` out of the synchronous `init()` into a `Task.detached`:

```swift
private init() {
    let base = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first!
    cacheDir = base.appendingPathComponent("roammate_cache", isDirectory: true)
    try? FileManager.default.createDirectory(at: cacheDir, withIntermediateDirectories: true)
    Task.detached(priority: .utility) { self.migrateFromUserDefaults() }  // off main thread
}
```

#### 2b. Remove blocking cache loads from store `init()`s
**Files:** `TripStore.swift`, `GroupStore.swift`, `NotificationStore.swift`

Change each `init()` to start with an empty array (zero blocking work). Add a `warmFromCache()` async method:

```swift
// TripStore (same pattern for GroupStore and NotificationStore)
init() { }   // no DiskCache access

func warmFromCache() async {
    guard trips.isEmpty else { return }
    if let cached = await DiskCache.shared.loadAsync([Trip].self, key: cacheKey) {
        trips = cached
    }
}
```

`NotificationStore.warmFromCache()` also recomputes `unreadCount` after setting `notifications`.

---

### 3. Parallel Startup Tasks — `RoammateApp`
**File:** `ios/Roammate/App/RoammateApp.swift`

Replace the current sequential `.task {}` with concurrent warm + auth:

```swift
.task {
    // Warm all caches in parallel (background I/O, no main-thread block)
    async let _t = tripStore.warmFromCache()
    async let _g = groupStore.warmFromCache()
    async let _n = notificationStore.warmFromCache()
    await (_t, _g, _n)   // all three run concurrently

    await authManager.checkAuth()   // fast-path returns immediately if token present

    if authManager.isAuthenticated {
        Task { await subscriptionStore.boot() }   // fire-and-forget, don't block task
    }
}
```

`subscriptionStore.boot()` is fire-and-forget here because `isConfirmed` gates upsell UI (already handles the "not yet loaded" state gracefully via `isConfirmed = false`). No behavioral regression.

---

### 4. URLSession Timeout — `APIClient`
**File:** `ios/Roammate/Network/APIClient.swift`

Replace `URLSession.shared` with a custom session. Add `timeoutIntervalForRequest = 12`:

```swift
private let session: URLSession = {
    let cfg = URLSessionConfiguration.default
    cfg.timeoutIntervalForRequest = 12   // fail fast per-attempt
    cfg.timeoutIntervalForResource = 60  // overall cap
    return URLSession(configuration: cfg)
}()
```

Replace the single `URLSession.shared.data(for: req)` call site with `session.data(for: req)`.

**Rationale:** 12 s × 3 attempts = 36 s worst-case if all retries time out. With optimistic auth (Fix 1), the user never waits for this. But it prevents the background validation task from hanging indefinitely if the backend is unavailable.

> Note: LLM endpoints (BrainstormService, ConciergeService) already use `retries: 0` and typically stream responses. 12 s per-request is enough for initial connection; streamed chunks reset the per-chunk deadline. If specific endpoints need more time, pass a custom `URLRequest.timeoutInterval` before handing to `session.data(for:)` — that takes precedence over the session-level config.

---

## Files Changed

| File | Change |
|------|--------|
| `ios/Roammate/Store/AuthManager.swift` | Optimistic fast-path + background validation |
| `ios/Roammate/Utils/DiskCache.swift` | `loadAsync()` + background migration |
| `ios/Roammate/Store/TripStore.swift` | Empty init + `warmFromCache()` |
| `ios/Roammate/Store/GroupStore.swift` | Empty init + `warmFromCache()` |
| `ios/Roammate/Store/NotificationStore.swift` | Empty init + `warmFromCache()`, recompute unreadCount |
| `ios/Roammate/App/RoammateApp.swift` | Parallel `async let` warm + fire-and-forget subscription boot |
| `ios/Roammate/Network/APIClient.swift` | Custom URLSession with 12 s timeout |

`TripDetailStore` also does `loadFromCache()` in its `init()` but it is instantiated per-trip-detail navigation (not at app root), so it is **not** on the boot critical path. Leave it unchanged.

---

## Verification

1. **Build and run on a physical device** (not simulator — file I/O timing differs).
2. **Cold launch (no prior state):** App should paint intro cards or login within 1–2 frames. No white screen.
3. **Warm launch (authenticated user):** `MainShell` appears immediately. Trips/groups may be empty for ≤100 ms then populate from cache. Network refresh fills in fresh data in background.
4. **Network offline (airplane mode):** Authenticated user sees `MainShell` with cached trips. Unauthenticated user sees login page. No hang.
5. **Expired token (simulate by clearing Keychain, reinstalling):** App shows login page immediately (slow path triggers but returns fast since no tokens). 
6. **Token expired server-side (401):** Background validator calls logout(); user is redirected to login with a single animated transition.
7. Add a `os_signpost` or `CFAbsoluteTimeGetCurrent()` log at the top of `RoammateApp.body` and at the first `.onAppear` of `ContentView` to measure time-to-first-frame before vs. after.
