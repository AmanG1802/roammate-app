'use client';

import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Loader } from '@googlemaps/js-api-loader';
import { RefreshCw, AlertTriangle, Map as MapIcon } from 'lucide-react';
import { useTripStore, Event } from '@/lib/store';

const MOCK_MODE =
  (process.env.NEXT_PUBLIC_GOOGLE_MAPS_MOCK ?? 'false').toLowerCase() === 'true';
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

interface GoogleMapProps {
  /** When set, only events on this day participate in markers + route. */
  filterDay?: Date;
  /** Trip id, required for the route refresh action. */
  tripId?: string | null;
}

interface RouteResponse {
  encoded_polyline: string | null;
  legs: { from_event_id: string; to_event_id: string; distance_m: number; duration_s: number }[];
  total_duration_s: number;
  total_distance_m: number;
  ordered_event_ids: string[];
  unroutable: { event_id: string; reason: string }[];
  reason: 'need_two_points' | 'missing_start_times' | 'time_conflicts' | null;
}

type Toast = { kind: 'error' | 'info' | 'success'; message: string } | null;

/** Format YYYY-MM-DD using LOCAL date components (mirrors trips/page.tsx). */
function toLocalISODate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Mirrors Timeline.hasConflict — overlap when prev.end_time > next.start_time. */
function hasConflict(a: Event, b: Event): boolean {
  if (!a.end_time || !b.start_time) return false;
  return a.end_time > b.start_time;
}

/** Compute which gates fail for a day's events.
 *
 * Walks the events in the *same* order the Timeline UI displays them
 * (``start_time`` ASC, with TBD items pushed to the end by ``sort_order``
 * — see ``frontend/lib/store.ts:165-168``).  This means every conflict
 * we flag here corresponds to a red time icon in Timeline.tsx:277-278,
 * and conversely we never flag a pair the user can't see is red.
 *
 * The backend re-runs the same walk in ``maps.py`` as the source of
 * truth, but the frontend gate avoids burning a 422 round-trip.
 */
function computeGateFailures(events: Event[]): {
  hasMissingTimes: boolean;
  hasConflicts: boolean;
} {
  if (events.length === 0) {
    return { hasMissingTimes: false, hasConflicts: false };
  }
  const hasMissingTimes = events.some((e) => !e.start_time);
  // Mirror the visibleEvents ordering used in Timeline.tsx:
  // timed events first (sorted by start_time), then TBD by sort_order.
  const sorted = [...events].sort((a, b) => {
    if (a.start_time && b.start_time) {
      return a.start_time.getTime() - b.start_time.getTime();
    }
    if (a.start_time && !b.start_time) return -1;
    if (!a.start_time && b.start_time) return 1;
    return (a.sort_order ?? 0) - (b.sort_order ?? 0);
  });
  let hasConflicts = false;
  for (let i = 1; i < sorted.length; i++) {
    if (hasConflict(sorted[i - 1], sorted[i])) {
      hasConflicts = true;
      break;
    }
  }
  return { hasMissingTimes, hasConflicts };
}

function gateFailureMessage(gate: {
  hasMissingTimes: boolean;
  hasConflicts: boolean;
}): string | null {
  if (gate.hasMissingTimes && gate.hasConflicts) {
    return 'Add missing start times and resolve conflicts before generating the route.';
  }
  if (gate.hasMissingTimes) {
    return 'Add a start time to every item before generating the route.';
  }
  if (gate.hasConflicts) {
    return 'Resolve time conflicts in the timeline before generating the route.';
  }
  return null;
}

/** Decode a Google encoded polyline back into [lat, lng] pairs. */
function decodePolyline(encoded: string): { lat: number; lng: number }[] {
  const points: { lat: number; lng: number }[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;
  while (index < encoded.length) {
    let result = 0;
    let shift = 0;
    let b: number;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlat = result & 1 ? ~(result >> 1) : result >> 1;
    lat += dlat;
    result = 0;
    shift = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlng = result & 1 ? ~(result >> 1) : result >> 1;
    lng += dlng;
    points.push({ lat: lat / 1e5, lng: lng / 1e5 });
  }
  return points;
}

/** Fingerprint of a day's events used to detect "stale route" state.
 *
 * Matches the plan: "current day's event-id-set + start_time values + count
 * snapshot diff".  Recomputing this on every render is cheap and lets us
 * compare with the snapshot taken at the last successful fetch.
 */
function fingerprint(events: Event[]): string {
  return [
    events.length,
    ...[...events]
      .sort((a, b) => String(a.id).localeCompare(String(b.id)))
      .map((e) => `${e.id}:${e.start_time ?? ''}:${e.end_time ?? ''}`),
  ].join('|');
}

export default function GoogleMap({ filterDay, tripId }: GoogleMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const { events, ideas } = useTripStore();
  // We use the modern AdvancedMarkerElement (the legacy google.maps.Marker
  // is deprecated as of Feb 21 2024).  The ref is intentionally typed as
  // ``any`` to avoid a hard compile-time dep on the dynamically-loaded
  // marker library typings.
  const markersRef = useRef<google.maps.marker.AdvancedMarkerElement[]>([]);
  const polylineRef = useRef<google.maps.Polyline | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState<Toast>(null);
  const [mockRoute, setMockRoute] = useState<RouteResponse | null>(null);
  const [routeSnapshot, setRouteSnapshot] = useState<{
    fingerprint: string;
    filterDay: string | null;
  } | null>(null);

  // ── Day filtering ───────────────────────────────────────────────────────
  const dayEvents = useMemo(() => {
    if (!filterDay) return events;
    const dayStr = toLocalISODate(filterDay);
    return events.filter((e) => e.day_date === dayStr);
  }, [events, filterDay]);

  // ── Gate state (drives both disabled visual + click-time toast) ────────
  const gates = useMemo(() => computeGateFailures(dayEvents), [dayEvents]);
  const gateMessage = gateFailureMessage(gates);

  // ── Stale detection (snapshot comparison, plan §6.3) ───────────────────
  const currentFingerprint = useMemo(() => fingerprint(dayEvents), [dayEvents]);
  const currentDayKey = filterDay ? toLocalISODate(filterDay) : null;
  const stale = useMemo(() => {
    if (!routeSnapshot) return false;
    return (
      routeSnapshot.fingerprint !== currentFingerprint ||
      routeSnapshot.filterDay !== currentDayKey
    );
  }, [routeSnapshot, currentFingerprint, currentDayKey]);

  // When the day switches and there's no stored snapshot for the new day,
  // clear any visible polyline so we don't show yesterday's route.
  useEffect(() => {
    if (
      routeSnapshot &&
      routeSnapshot.filterDay !== currentDayKey &&
      polylineRef.current
    ) {
      polylineRef.current.setMap(null);
      polylineRef.current = null;
      setMockRoute(null);
    }
  }, [currentDayKey, routeSnapshot]);

  // Auto-dismiss toast after ~3.5s (mirrors dashboard skip toast cadence).
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  // ── Map init (real Google JS SDK only) ─────────────────────────────────
  useEffect(() => {
    if (MOCK_MODE) return;
    const loader = new Loader({
      apiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '',
      version: 'weekly',
      // 'marker' is required for AdvancedMarkerElement / PinElement.
      libraries: ['places', 'marker'],
    });
    loader.load().then(() => {
      if (mapRef.current && !map) {
        const newMap = new google.maps.Map(mapRef.current, {
          center: { lat: 41.8902, lng: 12.4922 },
          zoom: 13,
          // mapId is required for AdvancedMarkerElement.  Override at
          // deploy time by configuring this id in Google Cloud Console
          // for custom map styling.
          mapId: 'ROAMMATE_MAP_ID',
          disableDefaultUI: true,
          zoomControl: true,
        });
        setMap(newMap);
      }
    });
  }, [map]);

  // ── Markers ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (MOCK_MODE || !map) return;

    let cancelled = false;

    (async () => {
      // Lazily import the marker library — small enough to do on every
      // render of this effect (it's cached after the first call).
      const { AdvancedMarkerElement, PinElement } =
        (await google.maps.importLibrary('marker')) as google.maps.MarkerLibrary;

      if (cancelled) return;

      // Detach previous markers before drawing the new set.
      markersRef.current.forEach((m) => {
        m.map = null;
      });
      markersRef.current = [];

      const bounds = new google.maps.LatLngBounds();
      let hasMarkers = false;

      dayEvents.forEach((event, index) => {
        if (!event.lat || !event.lng) return;
        const pin = new PinElement({
          background: '#4f46e5',
          borderColor: '#ffffff',
          glyph: String(index + 1),
          glyphColor: '#ffffff',
          scale: 1.1,
        });
        const marker = new AdvancedMarkerElement({
          position: { lat: event.lat, lng: event.lng },
          map,
          title: event.title,
          content: pin.element,
        });
        markersRef.current.push(marker);
        bounds.extend({ lat: event.lat, lng: event.lng });
        hasMarkers = true;
      });

      // Idea markers are only shown when not filtering to a single day.
      if (!filterDay) {
        ideas.forEach((idea) => {
          if (!idea.lat || !idea.lng) return;
          const pin = new PinElement({
            background: '#94a3b8',
            borderColor: '#ffffff',
            glyphColor: '#ffffff',
            scale: 0.7,
          });
          const marker = new AdvancedMarkerElement({
            position: { lat: idea.lat, lng: idea.lng },
            map,
            title: idea.title,
            content: pin.element,
          });
          markersRef.current.push(marker);
          bounds.extend({ lat: idea.lat, lng: idea.lng });
          hasMarkers = true;
        });
      }

      if (hasMarkers) {
        map.fitBounds(bounds);
        if ((map.getZoom() ?? 0) > 15) map.setZoom(15);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [map, dayEvents, ideas, filterDay]);

  // ── Refresh action ─────────────────────────────────────────────────────
  const handleRefresh = useCallback(async () => {
    if (!filterDay) {
      setToast({ kind: 'info', message: 'Pick a day to compute a route.' });
      return;
    }
    if (!tripId) return;

    // Hard pre-flight gates — never burn a backend request when we know it
    // will 422.  The button itself is also rendered with `disabled` styling
    // when these gates fail; the click-time toast handles users who don't
    // notice the disabled state.
    if (gateMessage) {
      setToast({ kind: 'error', message: gateMessage });
      return;
    }

    if (dayEvents.length === 0) {
      setToast({ kind: 'info', message: 'No items on this day to route.' });
      return;
    }

    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (!token) {
      setToast({ kind: 'error', message: 'Sign in required.' });
      return;
    }

    setRefreshing(true);
    try {
      const res = await fetch(`${API_BASE}/trips/${tripId}/route`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ day_date: toLocalISODate(filterDay) }),
      });

      // Backend 422 = a validation gate fired (race with another tab edit).
      if (res.status === 422) {
        const err = await res.json().catch(() => null);
        const detail = err?.detail;
        const code =
          (typeof detail === 'object' && detail?.detail) ||
          (typeof detail === 'string' && detail);
        if (code === 'missing_start_times') {
          setToast({
            kind: 'error',
            message: 'Add a start time to every item before generating the route.',
          });
        } else if (code === 'time_conflicts') {
          setToast({
            kind: 'error',
            message: 'Resolve time conflicts in the timeline before generating the route.',
          });
        } else {
          setToast({ kind: 'error', message: 'Could not compute route.' });
        }
        return;
      }

      if (!res.ok) {
        setToast({ kind: 'error', message: 'Could not compute route.' });
        return;
      }

      const data: RouteResponse = await res.json();

      if (data.reason === 'need_two_points') {
        setToast({
          kind: 'info',
          message: 'Add at least two items with locations to see a route.',
        });
        return;
      }

      // Mock mode: we don't have a Google JS map; we render a stylized SVG
      // in the mock branch from this state.
      if (MOCK_MODE) {
        setMockRoute(data);
        setRouteSnapshot({
          fingerprint: currentFingerprint,
          filterDay: currentDayKey,
        });
        const unrouted = data.unroutable.length;
        const suffix = unrouted > 0 ? ` (${unrouted} hidden — no location)` : '';
        setToast({
          kind: 'success',
          message:
            `Mock route: ${(data.total_distance_m / 1000).toFixed(1)} km, ` +
            `${Math.round(data.total_duration_s / 60)} min.${suffix}`,
        });
        return;
      }

      // Real mode: draw the polyline.
      if (polylineRef.current) {
        polylineRef.current.setMap(null);
        polylineRef.current = null;
      }
      if (data.encoded_polyline && map) {
        const path = decodePolyline(data.encoded_polyline);
        polylineRef.current = new google.maps.Polyline({
          path,
          geodesic: false,
          strokeColor: '#4f46e5',
          strokeOpacity: 0.85,
          strokeWeight: 4,
          map,
        });
        const bounds = new google.maps.LatLngBounds();
        path.forEach((p) => bounds.extend(p));
        map.fitBounds(bounds);
      }
      setRouteSnapshot({
        fingerprint: currentFingerprint,
        filterDay: currentDayKey,
      });
      const unrouted = data.unroutable.length;
      const suffix = unrouted > 0 ? ` (${unrouted} hidden — no location)` : '';
      setToast({
        kind: 'success',
        message:
          `Route updated: ${(data.total_distance_m / 1000).toFixed(1)} km, ` +
          `${Math.round(data.total_duration_s / 60)} min.${suffix}`,
      });
    } catch {
      setToast({ kind: 'error', message: 'Network error — try again.' });
    } finally {
      setRefreshing(false);
    }
  }, [
    filterDay,
    tripId,
    dayEvents,
    map,
    gateMessage,
    currentFingerprint,
    currentDayKey,
  ]);

  // The button is disabled (passive UX) when *any* gate would fail.  The
  // click handler still fires the toast for users who don't notice.
  const refreshDisabled =
    !filterDay || dayEvents.length < 2 || gateMessage !== null;
  const disabledTooltip =
    gateMessage ??
    (!filterDay
      ? 'Pick a day first.'
      : dayEvents.length < 2
        ? 'Add at least two items on this day.'
        : 'Refresh route');

  // ── Mock-mode fallback render (no Google JS SDK) ──────────────────────
  if (MOCK_MODE) {
    return (
      <div className="flex-1 h-full relative bg-gradient-to-br from-slate-100 via-slate-50 to-indigo-50">
        <MockMapPane
          events={dayEvents}
          mockRoute={mockRoute}
          stale={stale}
        />
        <RefreshButton
          onClick={handleRefresh}
          loading={refreshing}
          disabled={refreshDisabled}
          stale={stale}
          tooltip={disabledTooltip}
        />
        <DayBadge filterDay={filterDay} />
        <ToastView toast={toast} />
      </div>
    );
  }

  return (
    <div className="flex-1 h-full relative">
      <div ref={mapRef} className="absolute inset-0" />
      <RefreshButton
        onClick={handleRefresh}
        loading={refreshing}
        disabled={refreshDisabled}
        stale={stale}
        tooltip={disabledTooltip}
      />
      <DayBadge filterDay={filterDay} />
      <ToastView toast={toast} />
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function RefreshButton({
  onClick,
  loading,
  disabled,
  stale,
  tooltip,
}: {
  onClick: () => void;
  loading: boolean;
  disabled: boolean;
  stale: boolean;
  tooltip: string;
}) {
  // We deliberately keep `onClick` wired even when "disabled" so users who
  // don't notice the muted styling still get a toast.  The native
  // `disabled` HTML attribute would suppress that, so we use aria-disabled
  // + visual cues instead.
  return (
    <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2">
      <button
        onClick={onClick}
        aria-disabled={disabled || loading}
        title={tooltip}
        className={`flex items-center gap-2 px-4 py-2.5 bg-white/95 backdrop-blur rounded-full shadow-md border transition-all ${
          disabled
            ? 'border-slate-200 text-slate-300 cursor-not-allowed opacity-70'
            : 'border-indigo-200 text-indigo-600 hover:bg-indigo-50'
        }`}
      >
        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        <span className="text-xs font-black uppercase tracking-widest">
          {loading ? 'Routing…' : 'Refresh Route'}
        </span>
      </button>
      <AnimatePresence>
        {stale && !loading && (
          <motion.span
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            className="px-3 py-1.5 bg-amber-50 border border-amber-200 text-amber-600 rounded-full text-[10px] font-black uppercase tracking-widest"
          >
            Stale Route
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}

function DayBadge({ filterDay }: { filterDay?: Date }) {
  return (
    <div className="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur p-2 rounded-lg shadow-md border border-slate-200">
      <span className="text-xs font-bold text-slate-600 uppercase tracking-wider px-2">
        {filterDay
          ? `Day · ${filterDay.toLocaleDateString(undefined, {
              weekday: 'short',
              month: 'short',
              day: 'numeric',
            })}`
          : 'Live Route View'}
      </span>
    </div>
  );
}

/** Map toast — mirrors the dashboard skip-toast pattern at app/dashboard/page.tsx:562. */
function ToastView({ toast }: { toast: Toast }) {
  const palette = toast
    ? {
        error: 'bg-rose-50 border-rose-200 text-rose-700',
        info: 'bg-slate-50 border-slate-200 text-slate-700',
        success: 'bg-emerald-50 border-emerald-200 text-emerald-700',
      }[toast.kind]
    : '';
  return (
    <AnimatePresence>
      {toast && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 16 }}
          className="absolute top-20 left-1/2 -translate-x-1/2 z-30 max-w-md"
        >
          <div
            className={`flex items-start gap-2 px-4 py-3 rounded-xl border shadow-lg ${palette}`}
          >
            {toast.kind === 'error' && (
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            )}
            <p className="text-xs font-bold leading-relaxed">{toast.message}</p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/** Pure-CSS map pane shown when GOOGLE_MAPS_MOCK is true.
 *
 * Renders pins for the day's events on a simple normalized lat/lng grid and,
 * when a mock route response is available, draws an SVG polyline through the
 * decoded waypoints.  Good enough to verify the full pipeline without
 * touching Google.
 */
function MockMapPane({
  events,
  mockRoute,
  stale,
}: {
  events: Event[];
  mockRoute: RouteResponse | null;
  stale: boolean;
}) {
  const points = useMemo(() => {
    return events
      .filter((e) => e.lat != null && e.lng != null)
      .map((e) => ({ id: e.id, lat: e.lat, lng: e.lng, title: e.title }));
  }, [events]);

  const decoded = useMemo(() => {
    if (!mockRoute?.encoded_polyline) return [];
    return decodePolyline(mockRoute.encoded_polyline);
  }, [mockRoute]);

  // Compute a normalised viewBox 0..100 for both axes so we can draw without
  // figuring out projections.
  const projected = useMemo(() => {
    const all = [...points, ...decoded.map((p) => ({ id: '', ...p, title: '' }))];
    if (all.length === 0) return null;
    const lats = all.map((p) => p.lat);
    const lngs = all.map((p) => p.lng);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);
    const spanLat = Math.max(maxLat - minLat, 0.0001);
    const spanLng = Math.max(maxLng - minLng, 0.0001);
    const project = (lat: number, lng: number) => ({
      x: ((lng - minLng) / spanLng) * 80 + 10,
      // SVG y grows downward → invert lat.
      y: ((maxLat - lat) / spanLat) * 70 + 15,
    });
    return {
      project,
      points: points.map((p) => ({ ...p, ...project(p.lat, p.lng) })),
      polyline: decoded.map((p) => project(p.lat, p.lng)),
    };
  }, [points, decoded]);

  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <div className="absolute inset-0 opacity-30">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              'linear-gradient(rgba(99,102,241,0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.15) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />
      </div>

      {projected ? (
        <svg viewBox="0 0 100 100" className="absolute inset-0 w-full h-full">
          {projected.polyline.length > 1 && (
            <polyline
              points={projected.polyline.map((p) => `${p.x},${p.y}`).join(' ')}
              fill="none"
              stroke="#4f46e5"
              strokeWidth={0.8}
              strokeLinejoin="round"
              strokeLinecap="round"
              opacity={stale ? 0.4 : 0.85}
            />
          )}
          {projected.points.map((p, i) => (
            <g key={p.id}>
              <circle
                cx={p.x}
                cy={p.y}
                r={1.6}
                fill="#4f46e5"
                stroke="white"
                strokeWidth={0.4}
              />
              <text
                x={p.x}
                y={p.y + 0.6}
                fontSize={1.6}
                fill="white"
                fontWeight="bold"
                textAnchor="middle"
              >
                {i + 1}
              </text>
            </g>
          ))}
        </svg>
      ) : (
        <div className="text-center text-slate-400">
          <MapIcon className="w-10 h-10 mx-auto mb-2" />
          <p className="text-xs font-bold uppercase tracking-widest">
            Mock map · pick a day with items
          </p>
        </div>
      )}
    </div>
  );
}
