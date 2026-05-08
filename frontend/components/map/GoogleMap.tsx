'use client';

import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Loader } from '@googlemaps/js-api-loader';
import {
  RefreshCw, AlertTriangle, Map as MapIcon, Maximize2, Minimize2,
  Locate, Layers, Info, MapPin,
} from 'lucide-react';
import { useTripStore, Event } from '@/lib/store';
import type { RouteLeg } from '@/lib/store';
import { categoryPinColor, categoryAccent } from '@/lib/categoryColors';
import { MarkerClusterer } from '@googlemaps/markerclusterer';
import { format } from 'date-fns';

const MOCK_MODE =
  (process.env.NEXT_PUBLIC_GOOGLE_MAPS_MOCK ?? 'false').toLowerCase() === 'true';
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';
const SHOW_PHOTOS =
  (process.env.NEXT_PUBLIC_GOOGLE_MAPS_FETCH_PHOTOS ?? 'true').toLowerCase() === 'true';
const MAP_ID = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID ?? 'ROAMMATE_MAP_ID';

interface GoogleMapProps {
  filterDay?: Date;
  tripId?: string | null;
}

interface RouteResponse {
  encoded_polyline: string | null;
  legs: RouteLeg[];
  total_duration_s: number;
  total_distance_m: number;
  ordered_event_ids: string[];
  unroutable: { event_id: string; reason: string }[];
  reason: 'need_two_points' | 'missing_start_times' | 'time_conflicts' | null;
}

type Toast = { kind: 'error' | 'info' | 'success'; message: string } | null;

function toLocalISODate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function hasConflict(a: Event, b: Event): boolean {
  if (!a.end_time || !b.start_time) return false;
  return a.end_time > b.start_time;
}

function computeGateFailures(events: Event[]): {
  hasMissingTimes: boolean;
  hasConflicts: boolean;
} {
  if (events.length === 0) {
    return { hasMissingTimes: false, hasConflicts: false };
  }
  const hasMissingTimes = events.some((e) => !e.start_time);
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

function evFingerprint(events: Event[]): string {
  return [
    events.length,
    ...[...events]
      .sort((a, b) => String(a.id).localeCompare(String(b.id)))
      .map((e) => `${e.id}:${e.start_time ?? ''}:${e.end_time ?? ''}`),
  ].join('|');
}

function formatTravelTime(seconds: number): string {
  const mins = Math.max(1, Math.round(seconds / 60));
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

function travelMode(leg: { duration_s: number; distance_m: number }): 'walk' | 'drive' {
  const speed = leg.duration_s > 0 ? leg.distance_m / leg.duration_s : 0;
  return speed < 2.8 ? 'walk' : 'drive';
}

function buildInfoWindowContent(event: Event): string {
  const accent = categoryAccent(event.category);
  const timeStr = event.start_time
    ? `${format(event.start_time, 'h:mm a')}${event.end_time ? ` – ${format(event.end_time, 'h:mm a')}` : ''}`
    : 'TBD';
  const timeBg = event.start_time ? '#eef2ff' : '#fffbeb';
  const timeColor = event.start_time ? '#4f46e5' : '#d97706';

  const iw = IW_RESET_CSS;
  let html = `${iw}<div style="font-family:Inter,system-ui,sans-serif;max-width:240px;">`;
  if (SHOW_PHOTOS && event.photo_url) {
    html += `<img src="${event.photo_url}" alt="" style="width:100%;height:100px;object-fit:cover;display:block;" />`;
  }
  html += `<div style="font-weight:900;font-size:13px;color:#0f172a;line-height:1.3;margin-bottom:6px;">${event.title}</div>`;
  html += `<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:6px;">`;
  html += `<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:800;background:${timeBg};color:${timeColor};">${timeStr}</span>`;
  if (event.category) {
    html += `<span style="display:inline-flex;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;background:#f1f5f9;color:#475569;">${event.category}</span>`;
  }
  if (event.rating != null) {
    html += `<span style="display:inline-flex;align-items:center;gap:2px;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;background:#fffbeb;color:#b45309;">&#9733; ${event.rating}</span>`;
  }
  html += `</div>`;
  if (event.address) {
    html += `<div style="font-size:10px;color:#64748b;font-weight:500;line-height:1.4;">${event.address}</div>`;
  }
  html += `</div>`;
  return html;
}

// ── CSS reset injected into InfoWindow content to kill internal padding/scrollbar
const IW_RESET_CSS = `<style>.gm-style-iw-d{overflow:hidden!important;padding:0!important}.gm-style-iw.gm-style-iw-c{padding:12px!important}.gm-style-iw-chr{position:absolute;top:0;right:0;z-index:1}</style>`;

// ── Distinct, high-contrast route leg palette ──────────────────────────
const LEG_COLORS = [
  '#4f46e5', // indigo
  '#dc2626', // red
  '#059669', // emerald
  '#d97706', // amber
  '#7c3aed', // violet
  '#0891b2', // cyan
  '#c026d3', // fuchsia
  '#2563eb', // blue
];


export default function GoogleMap({ filterDay, tripId }: GoogleMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const { events, ideas, hoveredEventId, setSelectedEventId } = useTripStore();
  const markersRef = useRef<google.maps.marker.AdvancedMarkerElement[]>([]);
  const markerByEventIdRef = useRef<Map<string, google.maps.marker.AdvancedMarkerElement>>(new Map());
  const polylineRef = useRef<google.maps.Polyline | null>(null);
  const polylinesRef = useRef<google.maps.Polyline[]>([]);
  const legLabelsRef = useRef<google.maps.marker.AdvancedMarkerElement[]>([]);
  const infoWindowRef = useRef<google.maps.InfoWindow | null>(null);
  const clustererRef = useRef<MarkerClusterer | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState<Toast>(null);
  const [mockRoute, setMockRoute] = useState<RouteResponse | null>(null);
  const [routeSnapshot, setRouteSnapshot] = useState<{
    fingerprint: string;
    filterDay: string | null;
  } | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showLegend, setShowLegend] = useState(false);
  const [lastRouteData, setLastRouteData] = useState<RouteResponse | null>(null);
  const [selectedLegIdx, setSelectedLegIdx] = useState<number | null>(null);
  const legInfoWindowRef = useRef<google.maps.InfoWindow | null>(null);

  // ── Day filtering ───────────────────────────────────────────────────────
  const dayEvents = useMemo(() => {
    if (!filterDay) return events;
    const dayStr = toLocalISODate(filterDay);
    return events.filter((e) => e.day_date === dayStr);
  }, [events, filterDay]);

  const gates = useMemo(() => computeGateFailures(dayEvents), [dayEvents]);
  const gateMessage = gateFailureMessage(gates);

  const currentFingerprint = useMemo(() => evFingerprint(dayEvents), [dayEvents]);
  const currentDayKey = filterDay ? toLocalISODate(filterDay) : null;
  const stale = useMemo(() => {
    if (!routeSnapshot) return false;
    return (
      routeSnapshot.fingerprint !== currentFingerprint ||
      routeSnapshot.filterDay !== currentDayKey
    );
  }, [routeSnapshot, currentFingerprint, currentDayKey]);

  useEffect(() => {
    if (
      routeSnapshot &&
      routeSnapshot.filterDay !== currentDayKey
    ) {
      clearRouteVisuals();
      setMockRoute(null);
      setLastRouteData(null);
    }
  }, [currentDayKey, routeSnapshot]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  // ── Helper to clear route visuals ────────────────────────────────────
  const clearRouteVisuals = useCallback(() => {
    if (polylineRef.current) {
      polylineRef.current.setMap(null);
      polylineRef.current = null;
    }
    polylinesRef.current.forEach((p) => p.setMap(null));
    polylinesRef.current = [];
    legLabelsRef.current.forEach((m) => { m.map = null; });
    legLabelsRef.current = [];
  }, []);

  // ── Map init ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (MOCK_MODE) return;
    const loader = new Loader({
      apiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '',
      version: 'weekly',
      libraries: ['places', 'marker'],
    });
    loader.load().then(() => {
      if (mapRef.current && !map) {
        const newMap = new google.maps.Map(mapRef.current, {
          center: { lat: 41.8902, lng: 12.4922 },
          zoom: 13,
          mapId: MAP_ID,
          disableDefaultUI: true,
          zoomControl: true,
          zoomControlOptions: { position: google.maps.ControlPosition.LEFT_BOTTOM },
        });
        setMap(newMap);
        setMapLoaded(true);
      }
    });
  }, [map]);

  // ── Markers with info windows, category colors, clustering ──────────
  useEffect(() => {
    if (MOCK_MODE || !map) return;

    let cancelled = false;

    (async () => {
      const { AdvancedMarkerElement, PinElement } =
        (await google.maps.importLibrary('marker')) as google.maps.MarkerLibrary;

      if (cancelled) return;

      markersRef.current.forEach((m) => { m.map = null; });
      markersRef.current = [];
      markerByEventIdRef.current.clear();
      if (clustererRef.current) {
        clustererRef.current.clearMarkers();
        clustererRef.current = null;
      }

      if (!infoWindowRef.current) {
        infoWindowRef.current = new google.maps.InfoWindow({
          maxWidth: 280,
        });
      }

      const bounds = new google.maps.LatLngBounds();
      let hasMarkers = false;
      const allMarkers: google.maps.marker.AdvancedMarkerElement[] = [];

      dayEvents.forEach((event, index) => {
        if (!event.lat || !event.lng) return;
        const pinColor = categoryPinColor(event.category);
        const pin = new PinElement({
          background: pinColor,
          borderColor: '#ffffff',
          glyphText: String(index + 1),
          glyphColor: '#ffffff',
          scale: 1.1,
        });
        const marker = new AdvancedMarkerElement({
          position: { lat: event.lat, lng: event.lng },
          map,
          title: event.title,
          content: pin,
          gmpClickable: true,
        });

        marker.addEventListener('gmp-click', () => {
          if (infoWindowRef.current) {
            infoWindowRef.current.setContent(buildInfoWindowContent(event));
            infoWindowRef.current.open({ anchor: marker, map });
          }
          setSelectedEventId(event.id);
        });

        markersRef.current.push(marker);
        markerByEventIdRef.current.set(event.id, marker);
        allMarkers.push(marker);
        bounds.extend({ lat: event.lat, lng: event.lng });
        hasMarkers = true;
      });

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
            content: pin,
          });
          markersRef.current.push(marker);
          allMarkers.push(marker);
          bounds.extend({ lat: idea.lat, lng: idea.lng });
          hasMarkers = true;
        });
      }

      if (allMarkers.length > 8) {
        clustererRef.current = new MarkerClusterer({
          map,
          markers: allMarkers,
        });
      }

      if (hasMarkers) {
        map.fitBounds(bounds);
        if ((map.getZoom() ?? 0) > 15) map.setZoom(15);
      }
    })();

    return () => { cancelled = true; };
  }, [map, dayEvents, ideas, filterDay, setSelectedEventId]);

  // ── Highlight markers on hover from Timeline ────────────────────────
  useEffect(() => {
    if (MOCK_MODE || !map) return;
    markerByEventIdRef.current.forEach((marker, eventId) => {
      const el = marker.content as HTMLElement | null;
      if (!el) return;
      if (eventId === hoveredEventId) {
        el.style.transform = 'scale(1.35)';
        el.style.transition = 'transform 200ms ease-out';
        el.style.zIndex = '999';
        el.style.filter = 'drop-shadow(0 0 8px rgba(79,70,229,0.5))';
      } else {
        el.style.transform = '';
        el.style.transition = 'transform 200ms ease-out';
        el.style.zIndex = '';
        el.style.filter = '';
      }
    });
  }, [hoveredEventId, map, dayEvents]);

  // ── Fit all markers ─────────────────────────────────────────────────
  const handleFitAll = useCallback(() => {
    if (!map) return;
    const bounds = new google.maps.LatLngBounds();
    let count = 0;
    markersRef.current.forEach((m) => {
      if (m.position) {
        bounds.extend(m.position as google.maps.LatLng);
        count++;
      }
    });
    if (count > 0) {
      map.fitBounds(bounds);
      if ((map.getZoom() ?? 0) > 15) map.setZoom(15);
    }
  }, [map]);

  // ── Fullscreen toggle ───────────────────────────────────────────────
  const containerRef = useRef<HTMLDivElement>(null);
  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;
    if (!isFullscreen) {
      containerRef.current.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  }, [isFullscreen]);

  useEffect(() => {
    const onFs = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', onFs);
    return () => document.removeEventListener('fullscreenchange', onFs);
  }, []);

  // ── Map style toggle ───────────────────────────────────────────────
  const [mapTypeIdx, setMapTypeIdx] = useState(0);
  const MAP_TYPES = ['roadmap', 'satellite', 'hybrid'] as const;
  const MAP_TYPE_LABELS = ['Map', 'Satellite', 'Hybrid'];
  const cycleMapType = useCallback(() => {
    if (!map) return;
    const next = (mapTypeIdx + 1) % MAP_TYPES.length;
    setMapTypeIdx(next);
    map.setMapTypeId(MAP_TYPES[next]);
  }, [map, mapTypeIdx]);

  // ── Draw route: per-leg colored polylines, click for travel info ─────
  const drawRoute = useCallback(async (data: RouteResponse, gMap: google.maps.Map) => {
    clearRouteVisuals();
    setSelectedLegIdx(null);
    if (legInfoWindowRef.current) {
      legInfoWindowRef.current.close();
    }

    if (!data.encoded_polyline) return;
    const fullPath = decodePolyline(data.encoded_polyline);

    if (data.legs.length === 0 || data.legs.length === 1) {
      // Single-color polyline when 0 or 1 legs
      const color = LEG_COLORS[0];
      const arrowSymbol: google.maps.Symbol = {
        path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
        scale: 2.5,
        strokeColor: '#ffffff',
        strokeWeight: 1,
        fillColor: color,
        fillOpacity: 1,
      };
      const poly = new google.maps.Polyline({
        path: fullPath,
        geodesic: false,
        strokeColor: color,
        strokeOpacity: 0.85,
        strokeWeight: 5,
        icons: [{ icon: arrowSymbol, offset: '0', repeat: '120px' }],
        map: gMap,
      });

      if (data.legs.length === 1) {
        const leg = data.legs[0];
        poly.addListener('click', (e: google.maps.MapMouseEvent) => {
          showLegInfo(leg, 0, color, e, gMap);
        });
      }

      polylinesRef.current.push(poly);
    } else {
      // Split decoded polyline into segments at each waypoint
      const eventsWithPos = dayEvents.filter((e) => e.lat && e.lng);
      const posById = new Map(eventsWithPos.map((e) => [e.id, { lat: e.lat!, lng: e.lng! }]));

      // Build ordered list of waypoint positions from legs
      const waypointIds: string[] = [data.legs[0].from_event_id];
      for (const leg of data.legs) waypointIds.push(leg.to_event_id);
      const waypoints = waypointIds
        .map((id) => posById.get(id))
        .filter((p): p is { lat: number; lng: number } => !!p);

      // Find the index in fullPath closest to each waypoint
      const findNearest = (target: { lat: number; lng: number }, startFrom: number) => {
        let bestIdx = startFrom;
        let bestDist = Infinity;
        for (let j = startFrom; j < fullPath.length; j++) {
          const d = (fullPath[j].lat - target.lat) ** 2 + (fullPath[j].lng - target.lng) ** 2;
          if (d < bestDist) { bestDist = d; bestIdx = j; }
        }
        return bestIdx;
      };

      const splitIndices = [0];
      let searchFrom = 0;
      for (let w = 1; w < waypoints.length - 1; w++) {
        const idx = findNearest(waypoints[w], searchFrom);
        splitIndices.push(idx);
        searchFrom = idx;
      }
      splitIndices.push(fullPath.length - 1);

      if (!legInfoWindowRef.current) {
        legInfoWindowRef.current = new google.maps.InfoWindow({ maxWidth: 220 });
      }

      data.legs.forEach((leg, i) => {
        const segStart = splitIndices[i];
        const segEnd = splitIndices[i + 1];
        if (segStart === undefined || segEnd === undefined) return;

        const segPath = fullPath.slice(segStart, segEnd + 1);
        if (segPath.length < 2) return;

        const color = LEG_COLORS[i % LEG_COLORS.length];
        const arrowSymbol: google.maps.Symbol = {
          path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
          scale: 2.5,
          strokeColor: '#ffffff',
          strokeWeight: 1,
          fillColor: color,
          fillOpacity: 1,
        };

        const poly = new google.maps.Polyline({
          path: segPath,
          geodesic: false,
          strokeColor: color,
          strokeOpacity: 0.75,
          strokeWeight: 5,
          icons: [{ icon: arrowSymbol, offset: '50%', repeat: '100px' }],
          map: gMap,
        });

        poly.addListener('click', (e: google.maps.MapMouseEvent) => {
          showLegInfo(leg, i, color, e, gMap);
        });

        polylinesRef.current.push(poly);
      });

      gMap.addListener('click', () => {
        setSelectedLegIdx(null);
        if (legInfoWindowRef.current) legInfoWindowRef.current.close();
        polylinesRef.current.forEach((p) => {
          p.setOptions({ strokeOpacity: 0.75, strokeWeight: 5 });
        });
      });
    }

    const bounds = new google.maps.LatLngBounds();
    fullPath.forEach((p) => bounds.extend(p));
    gMap.fitBounds(bounds);
  }, [clearRouteVisuals, dayEvents]);

  /** Open an InfoWindow on a clicked leg and highlight it */
  const showLegInfo = useCallback((
    leg: RouteLeg, i: number, color: string,
    e: google.maps.MapMouseEvent, gMap: google.maps.Map,
  ) => {
    setSelectedLegIdx(i);
    const mode = travelMode(leg);
    const icon = mode === 'walk' ? '🚶' : '🚗';
    const dist = leg.distance_m >= 1000
      ? `${(leg.distance_m / 1000).toFixed(1)} km`
      : `${Math.round(leg.distance_m)} m`;
    const fromEvent = dayEvents.find((ev) => ev.id === leg.from_event_id);
    const toEvent = dayEvents.find((ev) => ev.id === leg.to_event_id);

    const html = `${IW_RESET_CSS}<div style="font-family:Inter,system-ui,sans-serif;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
        <span style="font-size:16px;line-height:1;">${icon}</span>
        <span style="font-weight:900;font-size:14px;color:${color};">${formatTravelTime(leg.duration_s)}</span>
        <span style="font-size:11px;color:#94a3b8;font-weight:600;">${dist}</span>
      </div>
      <div style="font-size:11px;color:#64748b;font-weight:600;line-height:1.5;">
        <span style="color:#0f172a;font-weight:800;">${fromEvent?.title ?? 'Start'}</span>
        <span style="margin:0 4px;">→</span>
        <span style="color:#0f172a;font-weight:800;">${toEvent?.title ?? 'End'}</span>
      </div>
    </div>`;

    if (legInfoWindowRef.current) {
      legInfoWindowRef.current.setContent(html);
      legInfoWindowRef.current.setPosition(e.latLng!);
      legInfoWindowRef.current.open(gMap);
    }

    polylinesRef.current.forEach((p, j) => {
      p.setOptions({
        strokeOpacity: j === i ? 1 : 0.25,
        strokeWeight: j === i ? 7 : 3,
      });
    });
  }, [dayEvents]);

  // ── Refresh action ─────────────────────────────────────────────────
  const handleRefresh = useCallback(async () => {
    if (!filterDay) {
      setToast({ kind: 'info', message: 'Pick a day to compute a route.' });
      return;
    }
    if (!tripId) return;

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

      if (tripId && currentDayKey) {
        useTripStore.getState().setRouteLegs(tripId, currentDayKey, data.legs);
      }

      if (data.reason === 'need_two_points') {
        setToast({
          kind: 'info',
          message: 'Add at least two items with locations to see a route.',
        });
        return;
      }

      if (MOCK_MODE) {
        setMockRoute(data);
        setLastRouteData(data);
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

      if (map) {
        await drawRoute(data, map);
      }
      setLastRouteData(data);
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
    drawRoute,
  ]);

  const refreshDisabled =
    !filterDay || dayEvents.length < 2 || gateMessage !== null;
  const disabledTooltip =
    gateMessage ??
    (!filterDay
      ? 'Pick a day first.'
      : dayEvents.length < 2
        ? 'Add at least two items on this day.'
        : 'Refresh route');

  // ── Mock-mode fallback render ──────────────────────────────────────
  if (MOCK_MODE) {
    return (
      <div ref={containerRef} className="flex-1 h-full relative bg-gradient-to-br from-slate-100 via-slate-50 to-indigo-50">
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

  // ── Real map render ────────────────────────────────────────────────
  return (
    <div ref={containerRef} className="flex-1 h-full relative">
      {/* Skeleton loading state before Google Maps SDK loads */}
      {!mapLoaded && <MapSkeleton />}

      <div ref={mapRef} className="absolute inset-0" />

      {/* Empty state overlay when no markers for this day */}
      {mapLoaded && dayEvents.filter((e) => e.lat && e.lng).length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
          <div className="bg-white/90 backdrop-blur-sm rounded-2xl border border-slate-200 shadow-lg p-8 text-center max-w-xs pointer-events-auto">
            <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <MapPin className="w-7 h-7 text-indigo-400" />
            </div>
            <p className="text-sm font-black text-slate-900 mb-1">No locations yet</p>
            <p className="text-xs text-slate-400 font-medium">Add events with addresses to see them on the map.</p>
          </div>
        </div>
      )}

      <RefreshButton
        onClick={handleRefresh}
        loading={refreshing}
        disabled={refreshDisabled}
        stale={stale}
        tooltip={disabledTooltip}
      />
      <DayBadge filterDay={filterDay} />

      {/* Map controls: fit all, map style, fullscreen, legend */}
      <div className="absolute top-4 right-4 z-20 flex flex-col gap-2">
        <MapControlButton
          onClick={handleFitAll}
          title="Fit all markers"
          icon={<Locate className="w-4 h-4" />}
        />
        <MapControlButton
          onClick={cycleMapType}
          title={`Switch to ${MAP_TYPE_LABELS[(mapTypeIdx + 1) % MAP_TYPES.length]}`}
          icon={<Layers className="w-4 h-4" />}
        />
        <MapControlButton
          onClick={toggleFullscreen}
          title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          icon={isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        />
        <MapControlButton
          onClick={() => setShowLegend(!showLegend)}
          title="Legend"
          icon={<Info className="w-4 h-4" />}
          active={showLegend}
        />
      </div>

      {/* Legend overlay */}
      <AnimatePresence>
        {showLegend && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.2 }}
            className="absolute bottom-6 left-4 z-20 bg-white/95 backdrop-blur border border-slate-200 rounded-xl shadow-lg p-3 min-w-[160px]"
          >
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Legend</p>
            <div className="space-y-1.5">
              <LegendItem color="#4f46e5" label="Planned events" />
              <LegendItem color="#94a3b8" label="Ideas (unscheduled)" />
              {lastRouteData && lastRouteData.legs.length > 0 ? (
                <>
                  <p className="text-[9px] font-black uppercase tracking-widest text-slate-300 mt-2 mb-1">Route legs (click to inspect)</p>
                  {lastRouteData.legs.map((leg, i) => {
                    const from = dayEvents.find((e) => e.id === leg.from_event_id);
                    const to = dayEvents.find((e) => e.id === leg.to_event_id);
                    return (
                      <div key={i} className="flex items-center gap-2">
                        <div className="w-5 h-1 rounded-full" style={{ backgroundColor: LEG_COLORS[i % LEG_COLORS.length] }} />
                        <span className="text-[10px] font-bold text-slate-600 truncate max-w-[120px]">
                          {from?.title ?? `Stop ${i + 1}`} → {to?.title ?? `Stop ${i + 2}`}
                        </span>
                      </div>
                    );
                  })}
                </>
              ) : (
                <div className="flex items-center gap-2">
                  <div className="w-5 h-0.5 bg-indigo-500 rounded-full" />
                  <span className="text-[10px] font-bold text-slate-600">Route path</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <ToastView toast={toast} />
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function MapSkeleton() {
  return (
    <div className="absolute inset-0 z-10 bg-slate-100 flex items-center justify-center">
      <div className="absolute inset-0 animate-pulse bg-gradient-to-br from-slate-100 via-slate-200/50 to-slate-100" />
      <div className="relative text-center">
        <div className="w-12 h-12 bg-slate-200 rounded-2xl flex items-center justify-center mx-auto mb-3">
          <MapIcon className="w-6 h-6 text-slate-400" />
        </div>
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Loading map…</p>
      </div>
    </div>
  );
}

function MapControlButton({
  onClick,
  title,
  icon,
  active = false,
}: {
  onClick: () => void;
  title: string;
  icon: React.ReactNode;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      aria-label={title}
      className={`w-10 h-10 flex items-center justify-center rounded-xl shadow-md border transition-all cursor-pointer ${
        active
          ? 'bg-indigo-600 text-white border-indigo-500'
          : 'bg-white/95 backdrop-blur text-slate-600 border-slate-200 hover:bg-indigo-50 hover:text-indigo-600 hover:border-indigo-200'
      }`}
    >
      {icon}
    </button>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-3 h-3 rounded-full border-2 border-white shadow-sm" style={{ backgroundColor: color }} />
      <span className="text-[10px] font-bold text-slate-600">{label}</span>
    </div>
  );
}

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
  return (
    <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2">
      <button
        onClick={onClick}
        aria-disabled={disabled || loading}
        title={tooltip}
        className={`flex items-center gap-2 px-4 py-2.5 bg-white/95 backdrop-blur rounded-full shadow-md border transition-all cursor-pointer active:scale-95 ${
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
      .map((e) => ({ id: e.id, lat: e.lat, lng: e.lng, title: e.title, category: e.category }));
  }, [events]);

  const decoded = useMemo(() => {
    if (!mockRoute?.encoded_polyline) return [];
    return decodePolyline(mockRoute.encoded_polyline);
  }, [mockRoute]);

  const projected = useMemo(() => {
    const all = [...points, ...decoded.map((p) => ({ id: '', ...p, title: '', category: null }))];
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
          {/* Directional arrow marker definition */}
          <defs>
            <marker id="arrowhead" markerWidth="6" markerHeight="4" refX="3" refY="2" orient="auto">
              <polygon points="0 0, 6 2, 0 4" fill="#4f46e5" opacity={stale ? 0.4 : 0.85} />
            </marker>
          </defs>
          {projected.polyline.length > 1 && (
            <polyline
              points={projected.polyline.map((p) => `${p.x},${p.y}`).join(' ')}
              fill="none"
              stroke="#4f46e5"
              strokeWidth={0.8}
              strokeLinejoin="round"
              strokeLinecap="round"
              opacity={stale ? 0.4 : 0.85}
              markerMid="url(#arrowhead)"
            />
          )}
          {projected.points.map((p, i) => (
            <g key={p.id}>
              <circle
                cx={p.x}
                cy={p.y}
                r={1.6}
                fill={categoryPinColor(p.category)}
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
