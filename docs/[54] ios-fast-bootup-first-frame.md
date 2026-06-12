# [54] iOS Fast Bootup & First Frame — Investigation & Findings

## TL;DR

We suspected a 20–40s white screen on iOS launch caused by synchronous disk reads
and a slow backend. **Profiling on a physical device disproved most of it.** The
headline numbers:

| Suspected cause | Measured reality | Verdict |
|-----------------|------------------|---------|
| Synchronous DiskCache reads block first frame | **23ms total** | ❌ Irrelevant |
| `migrateFromUserDefaults` on main thread | **0ms** | ❌ Irrelevant |
| 16–40s pre-`main` launch | **Dev-loop artifact** (Debug + debugger + first-install) — Release/Profile launch is fast | ❌ Not a user problem |
| Authenticated user waits on `getMe` before `MainShell` | **5.25s real**, happens in Release too | ✅ Genuine |

**Conclusion:** the only genuinely user-facing problem is the **~5s auth-blocking
login flash**. The plan is de-scoped to **Phase 1 (optimistic auth) + Phase 4
(per-request timeouts)**. Phases 2 and 3 are dropped as measured-irrelevant.

---

## How we got here (chronological reasoning)

### Original hypothesis (pre-measurement)
Code archaeology suggested two causes for the white screen:

1. **Synchronous DiskCache reads during `@StateObject` init.** `TripStore`,
   `GroupStore`, `NotificationStore` each call `DiskCache.shared.load()` in `init()`,
   and `DiskCache.init()` runs `migrateFromUserDefaults()` synchronously — all on the
   main thread, before SwiftUI commits the first frame.
2. **No URLSession timeout** → a slow backend lets `checkAuth()`'s network calls hang
   (up to 60s × 3 retries = 180s).

This was plausible on paper but **never measured**. Three small JSON decodes causing
30s is implausible, so before implementing any fix we added instrumentation and
insisted on measuring first.

### Phase 0 — Profiling instrumentation (IMPLEMENTED)

**File:** `ios/Roammate/Utils/BootProfiler.swift` (temporary).

A lightweight profiler emitting **both** `os_signpost` intervals (Instruments →
Points of Interest, subsystem `com.roammate.boot`) and `print("[boot] … @ Nms")`
console lines. Crucially, its baseline is the **real process start time** read from
the kernel (`sysctl(KERN_PROC_PID)` → `kinfo_proc.kp_proc.p_starttime`), so the first
mark's elapsed value captures the pre-`main` launch cost that in-app signposts can't
otherwise see.

Instrumentation points:

| Location | Mark / Interval |
|----------|-----------------|
| `AppDelegate.didFinishLaunching` | `mark` |
| `RoammateApp.init` | `mark` (offset = pre-`main` time, since baseline is process start) |
| `DiskCache.init` | interval `DiskCache.migrateFromUserDefaults` |
| `TripStore` / `GroupStore` / `NotificationStore` `.init` | intervals `*.diskLoad` |
| `ContentView.onAppear` | `mark "first frame rendered"` |
| `AuthManager.checkAuth` | `mark` start/end + `getMe.start`/`getMe.done` |

`BootProfiler.swift` was registered in `Roammate.xcodeproj/project.pbxproj`
(four references) because the project does **not** use Xcode-16 synchronized file
groups, so new files need manual wiring. Build verified: `BUILD SUCCEEDED`.

### Measurement 1 — Simulator, warm launch

```
[boot] RoammateApp.init @ 0ms
[boot] AppDelegate.didFinishLaunching @ 394ms
[boot] DiskCache.migrateFromUserDefaults took 0ms
[boot] TripStore.diskLoad took 22ms
[boot] GroupStore.diskLoad took 1ms
[boot] NotificationStore.diskLoad took 0ms
[boot] ContentView.onAppear (first frame rendered) @ 1548ms
[boot] checkAuth.start @ 1548ms / checkAuth.end @ 1551ms
```

(At this point the baseline was still "now", not process start.) **Disk work = 23ms.
checkAuth = 3ms (logged out).** The disk-read hypothesis was dead on arrival. The
user noted "the app took ~10s before the logs even appeared" — i.e. the cost was
*before* `RoammateApp.init`, in the pre-`main` phase our signposts couldn't yet see.

### Tooling detour — `DYLD_PRINT_STATISTICS` doesn't work anymore

We added `DYLD_PRINT_STATISTICS=1` to the shared scheme to read dyld's pre-`main`
breakdown. It printed nothing: that variable is a **dyld2/3 feature, ignored by
dyld4** (iOS 16+/recent simulators), especially on the Simulator where launches use a
prebuilt launch closure. The modern replacement is the Instruments **App Launch**
template. The scheme entry was left in (harmless) but is effectively dead.

To measure pre-`main` from inside the app instead, we re-baselined
`BootProfiler.launchTime` to the **kernel process start time** (see Phase 0 above).
Now the first mark's offset *is* the pre-`main` cost.

### Measurement 2 — Physical device (Debug build, launched from Xcode)

```
[boot] RoammateApp.init (StateObjects constructed) @ 16040ms   ← pre-main = 16.0s
[boot] AppDelegate.didFinishLaunching @ 17194ms
[boot] DiskCache.migrateFromUserDefaults took 0ms
[boot] TripStore.diskLoad took 12ms
[boot] GroupStore.diskLoad took 2ms
[boot] NotificationStore.diskLoad took 8ms
[boot] ContentView.onAppear (first frame rendered) @ 20279ms   ← first frame at 20.3s
[boot] checkAuth.start @ 20344ms
[boot] checkAuth.getMe.start @ 20346ms
[boot] checkAuth.getMe.done @ 25594ms                          ← getMe took 5.25s
[boot] checkAuth.end @ 25594ms
[StoreKit] Loaded 2/2 products
```

Segment breakdown:

| Segment | Time |
|---------|------|
| Process start → `RoammateApp.init` (**pre-`main`**) | **16,040ms** |
| `init` → first frame (SwiftUI setup) | ~4,240ms |
| Disk loads | 22ms total |
| `getMe` network call | **5,248ms** |

Two findings:
- **Pre-`main` = 16s dominates** — but this was a **Debug build launched from Xcode
  with LLDB attached, likely first-launch-after-install.** All three inflate pre-`main`
  enormously: unoptimized Debug binary (no dyld chained-fixup optimization), debugger
  attach intercepting dyld, and one-time code-signature validation + launch-closure
  construction of the whole binary on first install.
- **`getMe` = 5.25s**, *after* first frame. With today's blocking `checkAuth`,
  `isAuthenticated` only flips to `true` once `getMe` returns — so an authenticated
  user sees the **login/intro screen from ~20.3s to ~25.6s** before `MainShell`
  appears. This is real and Release-independent.

### Linkage check — frameworks are already static

`Roammate.app` has **no embedded `Frameworks/` dir** and **no non-system dynamic
dependencies** (`otool -L`). The GoogleSignIn → AppAuth/GTMAppAuth/GTMSessionFetcher
chain is statically linked into the main binary. So the 16s is **not** "too many
dylibs to load," and the hypothesized "switch to static linking" fix is moot — it's
already static. That pointed the 16s squarely at Debug-build + debugger + first-launch
overhead rather than a structural launch problem.

### Measurement 3 — Physical device via Instruments "App Launch" (Release/Profile, no debugger)

The user ran **Product → Profile → App Launch** on the device (Release-optimized
build, no LLDB). Result: **launch was much faster.** This confirms the 16s pre-`main`
was a dev-loop artifact — a real user running the App Store (Release) build, like the
Profile build, does not experience it.

> **TODO (record the number):** capture the exact "time to first frame" / pre-`main`
> value from the App Launch trace so we have a real Release baseline on file. If the
> `init → first frame` segment is still multiple seconds in Release, that SwiftUI
> setup window may deserve a separate look; otherwise close it out.

---

## What's actually worth fixing

Only the **~5s auth-blocking login flash** survives scrutiny as a genuine,
Release-present, user-facing problem. The fixes below address it.

### Phase 1 — Optimistic Auth — `AuthManager.checkAuth()`
**File:** `ios/Roammate/Store/AuthManager.swift`

Replace the blocking `checkAuth()` with a two-phase pattern:

- **Fast path (has access token):** set `isAuthenticated = true` immediately, validate
  in background. No `await` in the fast path.
- **Slow path (refresh token only, no access token):** keep current behavior.
- **Background validation:** call `AuthService.getMe()`; handle the same error cases
  current `checkAuth()` does (corrections below).

> **Why this is the real win:** today an authenticated user on a 5s `getMe` (measured)
> is shown the **login screen** for those 5s because `isAuthenticated` stays false
> until `getMe` returns. Optimistic auth shows `MainShell` immediately. This holds in
> Release — it's not a dev artifact.

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
    } catch let api as APIError {
        switch api {
        case .unauthorized:
            // 401 — APIClient ALREADY attempted a silent refresh internally and it
            // failed (that's the only way .unauthorized escapes). Do NOT re-refresh
            // here (the original draft's manual refresh was dead code). Token is
            // genuinely dead: log out.
            logout()
        case .serverError(403, _):
            // /users/me requires email_verified. Match current checkAuth(): route
            // through verify rather than keep an unverified session alive.
            pendingVerificationEmail = nil
            logout()
        default:
            break   // transient network error: keep authenticated, retry next foreground
        }
    } catch {
        // non-APIError network error: keep authenticated, retry next foreground
    }
}
```

**Corrections vs. the original draft:**
1. **403 handling restored** — original only handled `.unauthorized` and would keep an
   unverified-email user authenticated (a regression from current `checkAuth()`).
2. **Redundant manual refresh removed** — `APIClient.perform` already does a one-shot
   `/auth/refresh` on 401 before throwing `.unauthorized`; re-doing it here is dead code.

**Subscription-tier safety (already correct, do not regress):** `SubscriptionStore`
starts at `.freeDefault` with `isConfirmed = false`; `refresh()` only sets
`isConfirmed = true` on a successful `/billing/status`. All upsell UI must gate on
`isConfirmed` so a paying user is never pitched Plus during the load window. This
window already exists today, so optimistic auth doesn't worsen it. **Action before
shipping:** grep paywall/upsell views to confirm none gate solely on `entitlement`
while ignoring `isConfirmed`.

**Residual tradeoff (accepted):** a user whose token was revoked server-side briefly
sees `MainShell` + their own cached data until background validation runs. Data is
their own (`logout()` calls `DiskCache.clearAll()`) and it self-corrects — strictly
better than today's "logged-in user stuck on login for 5s."

### Phase 4 — Per-Request Timeouts — `APIClient`
**File:** `ios/Roammate/Network/APIClient.swift`

> **Critical:** do NOT set a global `timeoutIntervalForRequest = 12` on the session.
> The iOS app does **not stream** — every Concierge/Brainstorm call is a single
> `URLSession.data(for:)` and the server returns the whole JSON blob only after
> 15–40s of LLM compute. `timeoutIntervalForRequest` is a *between-packets* timer;
> with no streaming, no data arrives until the full response is ready, so a global
> 12s cap would kill LLM chat mid-compute.

Use **per-request** timeouts instead:
- **Auth calls → 12s** (bounds the background validation from Phase 1).
- **LLM calls → 60s** (Concierge/Brainstorm need room for server compute).
- **Everything else → system default** (unchanged).

Thread an optional `timeout: TimeInterval? = nil` through
`APIClient.request`/`perform` and apply `req.timeoutInterval = timeout` per request
(`URLRequest.timeoutInterval` overrides the session default — no global change, keep
`URLSession.shared`). Then:
- `AuthService.getMe` / `refresh` → `timeout: 12`
- `ConciergeService.chat`/`execute`/`findNearby`, `BrainstormService.chat`/`extract`
  → `timeout: 60`

---

## Dropped (measured-irrelevant)

- **Phase 2 — Async DiskCache reads / off-main migration.** Disk work is 23ms and
  migration is 0ms. Not worth the churn or risk. Stores keep their synchronous
  `init()` cache loads.
- **Phase 3 — Parallel `warmFromCache` + restructured `.task`.** Predicated on the
  disk cost being material; it isn't.
- **Pre-`main` / dyld optimization.** The 16s was a Debug + debugger + first-install
  artifact; frameworks are already statically linked; Release/Profile launch is fast.
  Nothing to do unless the Release App Launch trace says otherwise.

---

## Cleanup (do once the fix ships)

- Remove `ios/Roammate/Utils/BootProfiler.swift` and all its call sites
  (`RoammateApp`, `DiskCache`, the three stores, `ContentView`, `AuthManager`).
- Remove the four `BootProfiler.swift` references from `project.pbxproj`.
- Remove the `DYLD_PRINT_STATISTICS` env var from `Roammate.xcscheme` (dead anyway).

---

## Verification (for Phase 1 + Phase 4)

1. **Authenticated launch:** `MainShell` appears immediately; no 5s login screen.
2. **Token expired server-side (401):** background validator logs out with a single
   animated transition. **Unverified email (403):** routed to verify, not kept
   authenticated.
3. **Offline (airplane mode):** authenticated user sees cached `MainShell`,
   unauthenticated sees login, no hang.
4. **LLM regression check:** a Concierge/Brainstorm request taking 20–40s of server
   compute still succeeds (would fail under a global-12s session timeout).
5. **Subscription:** a Plus user is never shown upsell UI during the load window
   (gated on `isConfirmed`).
6. **Real-launch baseline:** record the Instruments App Launch "time to first frame"
   on a Release build so we have a true number, not the Debug/debugger-inflated one.
