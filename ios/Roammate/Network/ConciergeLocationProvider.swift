import Foundation
import CoreLocation

/// One-shot device-location helper for the Concierge "Find nearby" flow.
///
/// Web uses the browser geolocation API; on iOS we wrap `CLLocationManager`
/// with a single async request. Callers fall back to an event coordinate when
/// this returns `nil` (permission denied or a fix can't be obtained).
@MainActor
final class ConciergeLocationProvider: NSObject, ObservableObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    private var continuation: CheckedContinuation<CLLocationCoordinate2D?, Never>?

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
    }

    /// Request a single location fix. Prompts for When-In-Use permission the
    /// first time. Returns `nil` if permission is denied/restricted or no fix
    /// arrives. Never throws — the caller decides the fallback.
    func currentCoordinate() async -> CLLocationCoordinate2D? {
        switch manager.authorizationStatus {
        case .denied, .restricted:
            return nil
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        default:
            break
        }

        return await withCheckedContinuation { (cont: CheckedContinuation<CLLocationCoordinate2D?, Never>) in
            // Guard against a leftover continuation from a cancelled request.
            self.continuation?.resume(returning: nil)
            self.continuation = cont
            self.manager.requestLocation()
        }
    }

    // MARK: - CLLocationManagerDelegate

    nonisolated func locationManager(
        _ manager: CLLocationManager,
        didUpdateLocations locations: [CLLocation]
    ) {
        let coord = locations.last?.coordinate
        Task { @MainActor in
            self.continuation?.resume(returning: coord)
            self.continuation = nil
        }
    }

    nonisolated func locationManager(
        _ manager: CLLocationManager,
        didFailWithError error: Error
    ) {
        Task { @MainActor in
            self.continuation?.resume(returning: nil)
            self.continuation = nil
        }
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        // If the user just denied while a request is pending, resolve it.
        let status = manager.authorizationStatus
        guard status == .denied || status == .restricted else { return }
        Task { @MainActor in
            self.continuation?.resume(returning: nil)
            self.continuation = nil
        }
    }
}
