import { create } from 'zustand';
import { getToken } from '@/lib/auth';
import { toastBus } from '@/lib/toast-bus';

const API = process.env.NEXT_PUBLIC_API_URL ?? '';

/** Create a temporary local event (used when API is unavailable). */
function makeLocalEvent(
  idea: Idea,
  startTime: Date | null | undefined,
  events: Event[],
  dayDate: string | null = null,
): Event {
  const maxOrder = events.reduce((m, e) => Math.max(m, e.sort_order), -1);
  return {
    id: `local-${Math.random().toString(36).slice(2, 9)}`,
    trip_id: '0',
    title: idea.title,
    day_date: dayDate,
    start_time: startTime ?? null,
    end_time: startTime ? new Date(startTime.getTime() + 3_600_000) : null,
    lat: idea.lat,
    lng: idea.lng,
    sort_order: maxOrder + 1,
  };
}

export interface Event {
  id: string;
  trip_id: string;
  title: string;
  day_date: string | null;   // "YYYY-MM-DD" — the day this event belongs to
  start_time: Date | null;   // null = TBD
  end_time: Date | null;     // null = TBD
  lat: number;
  lng: number;
  sort_order: number;
  added_by?: string | null;
  up?: number;
  down?: number;
  my_vote?: number;
  category?: string | null;
  description?: string | null;
  photo_url?: string | null;
  rating?: number | null;
  address?: string | null;
  place_id?: string | null;
  is_skipped?: boolean;
}

export interface Idea {
  id: string;
  title: string;
  lat: number;
  lng: number;
  place_id?: string | null;
  start_time?: Date | null;
  end_time?: Date | null;
  added_by?: string | null;
  up?: number;
  down?: number;
  my_vote?: number;
  category?: string | null;
  photo_url?: string | null;
  rating?: number | null;
  address?: string | null;
  description?: string | null;
}

export interface TripDay {
  id: string;
  trip_id: string;
  date: string;       // ISO date string "YYYY-MM-DD"
  day_number: number;
}

export interface RouteLeg {
  from_event_id: string;
  to_event_id: string;
  duration_s: number;
  distance_m: number;
}

/** Build the legsByDay key — kept here so callers can't drift on the format. */
export function legsKey(tripId: string, dayDate: string): string {
  return `${tripId}::${dayDate}`;
}

interface TripState {
  activeTripId: string | null;
  ideas: Idea[];
  events: Event[];
  tripDays: TripDay[];
  collaborators: { id: string; name: string; color: string; activeEventId?: string }[];

  setActiveTrip: (id: string) => void;
  setIdeas: (ideas: Idea[]) => void;
  setEvents: (events: Event[]) => void;
  /** Set events WITHOUT sorting — used after manual drag-to-reorder. */
  setEventsRaw: (events: Event[]) => void;
  addIdea: (idea: Idea) => void;
  addEvent: (event: Event) => void;
  removeIdea: (ideaId: string) => void;
  removeEvent: (eventId: string) => void;

  /** Load events from API and replace local state. */
  loadEvents: (tripId: string, token: string) => Promise<void>;

  /**
   * Move idea from bin → itinerary.
   * Calls POST /events/ and DELETE /trips/{id}/ideas/{id}.
   * If tripId is null, falls back to in-memory only (demo mode).
   */
  moveIdeaToTimeline: (ideaId: string, tripId: string | null, token: string | null, startTime?: Date | null, dayDate?: string | null) => Promise<void>;

  /**
   * Move event back → idea bin.
   * Calls DELETE /events/{id} and restores a local idea.
   */
  moveEventToIdea: (eventId: string, tripId: string | null, token: string | null) => Promise<void>;

  /** Persist a time update for a single event. */
  updateEventTime: (eventId: string, startTime: Date | null, endTime: Date | null, token: string | null) => Promise<void>;

  /** Toggle is_skipped for an event. */
  toggleEventSkip: (eventId: string, token: string | null) => Promise<void>;

  /** Persist sort_order after manual drag-to-reorder. */
  reorderEvent: (eventId: string, newSortOrder: number, token: string | null) => Promise<void>;

  updateCollaboratorStatus: (userId: string, activeEventId?: string) => void;

  /** Trip day management */
  setTripDays: (days: TripDay[]) => void;
  loadTripDays: (tripId: string, token: string) => Promise<void>;
  addTripDay: (tripId: string, date: string, token: string) => Promise<TripDay | null>;
  deleteTripDay: (tripId: string, dayId: string, token: string, itemsAction?: 'bin' | 'delete') => Promise<void>;

  /** Route legs — per (trip, day) bucket of consecutive driving legs. */
  legsByDay: Record<string, RouteLeg[]>;
  setRouteLegs: (tripId: string, dayDate: string, legs: RouteLeg[]) => void;
  clearRouteLegsForDay: (tripId: string, dayDate: string) => void;

  /** Route persistence metadata — staleness tracking from backend. */
  routeMetaByDay: Record<string, { fingerprint: string; computedAt: string; isStale: boolean }>;
  setRouteMeta: (tripId: string, dayDate: string, meta: { fingerprint: string; computedAt: string; isStale: boolean }) => void;
  clearRouteMetaForDay: (tripId: string, dayDate: string) => void;

  /** Timestamp incremented whenever the idea list should be re-fetched. */
  ideasLastUpdated: number;

  /** Map-Timeline bidirectional highlight. */
  hoveredEventId: string | null;
  selectedEventId: string | null;
  setHoveredEventId: (id: string | null) => void;
  setSelectedEventId: (id: string | null) => void;

  /** Concierge drawer state. */
  conciergeOpen: boolean;
  conciergePreAction: { type: string; payload?: any } | null;
  openConcierge: (preAction?: { type: string; payload?: any } | null) => void;
  closeConcierge: () => void;
}

function mapApiEvent(raw: Record<string, unknown>): Event {
  return {
    id: String(raw.id),
    trip_id: String(raw.trip_id),
    title: raw.title as string,
    day_date: (raw.day_date as string) ?? null,
    start_time: raw.start_time ? new Date(raw.start_time as string) : null,
    end_time: raw.end_time ? new Date(raw.end_time as string) : null,
    lat: (raw.lat as number) ?? 0,
    lng: (raw.lng as number) ?? 0,
    sort_order: (raw.sort_order as number) ?? 0,
    added_by: (raw.added_by as string) ?? null,
    up: (raw.up as number) ?? 0,
    down: (raw.down as number) ?? 0,
    my_vote: (raw.my_vote as number) ?? 0,
    category: (raw.category as string) ?? null,
    description: (raw.description as string) ?? null,
    photo_url: (raw.photo_url as string) ?? null,
    rating: (raw.rating as number) ?? null,
    address: (raw.address as string) ?? null,
    place_id: (raw.place_id as string) ?? null,
    is_skipped: (raw.is_skipped as boolean) ?? false,
  };
}

function sortEvents(events: Event[]): Event[] {
  return [...events].sort((a, b) => {
    // Timed events first, sorted by start_time; then TBD by sort_order
    if (a.start_time && b.start_time) return a.start_time.getTime() - b.start_time.getTime();
    if (a.start_time && !b.start_time) return -1;
    if (!a.start_time && b.start_time) return 1;
    return a.sort_order - b.sort_order;
  });
}

export const useTripStore = create<TripState>((set, get) => ({
  activeTripId: null,
  ideas: [],
  events: [],
  tripDays: [],
  legsByDay: {},
  routeMetaByDay: {},
  collaborators: [
    { id: '1', name: 'You', color: '#4f46e5' },
    { id: '2', name: 'Sarah', color: '#ec4899' },
  ],

  setActiveTrip: (id) => set({ activeTripId: id, events: [], ideas: [], tripDays: [] }),
  setIdeas: (ideas) => set({ ideas }),
  setEvents: (events) => set({ events: sortEvents(events) }),
  setEventsRaw: (events) => set({ events }),
  addIdea: (idea) => set((s) => ({ ideas: [idea, ...s.ideas] })),
  addEvent: (event) => set((s) => ({ events: sortEvents([...s.events, event]) })),
  removeIdea: (ideaId) => set((s) => ({ ideas: s.ideas.filter((i) => i.id !== ideaId) })),
  removeEvent: (eventId) =>
    set((s) => {
      const ev = s.events.find((e) => e.id === eventId);
      const nextLegs = { ...s.legsByDay };
      if (ev?.trip_id && ev?.day_date) delete nextLegs[legsKey(ev.trip_id, ev.day_date)];
      return { events: s.events.filter((e) => e.id !== eventId), legsByDay: nextLegs };
    }),

  loadEvents: async (tripId, token) => {
    try {
      const res = await fetch(`${API}/events/?trip_id=${tripId}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      if (!res.ok) return;
      const raw: Record<string, unknown>[] = await res.json();
      set({ events: sortEvents(raw.map(mapApiEvent)) });
    } catch {
      // Network error – keep current state
    }
  },

  moveIdeaToTimeline: async (ideaId, tripId, token, startTime?, dayDate?) => {
    const { ideas, events } = get();
    const idea = ideas.find((i) => i.id === ideaId);
    if (!idea) return;

    set({ ideas: ideas.filter((i) => i.id !== ideaId) });

    if (!tripId || !token) {
      const maxOrder = events.reduce((m, e) => Math.max(m, e.sort_order), 0);
      const localEvent: Event = {
        id: Math.random().toString(36).slice(2, 9),
        trip_id: '0',
        title: idea.title,
        day_date: dayDate ?? null,
        start_time: startTime ?? null,
        end_time: startTime ? new Date(startTime.getTime() + 3600_000) : null,
        lat: idea.lat,
        lng: idea.lng,
        sort_order: maxOrder + 1,
      };
      set((s) => ({ events: sortEvents([...s.events, localEvent]) }));
      return;
    }

    const maxOrder = events.reduce((m, e) => Math.max(m, e.sort_order), 0);

    try {
      const numId = parseInt(ideaId, 10);
      const res = await fetch(`${API}/events/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          trip_id: parseInt(tripId, 10),
          title: idea.title,
          lat: idea.lat,
          lng: idea.lng,
          day_date: dayDate ?? null,
          start_time: startTime ? startTime.toISOString() : null,
          end_time: startTime ? new Date(startTime.getTime() + 3600_000).toISOString() : null,
          sort_order: maxOrder + 1,
          added_by: idea.added_by ?? null,
          source_idea_id: !isNaN(numId) ? numId : null,
        }),
      });

      if (res.ok) {
        const raw = await res.json();
        set((s) => ({ events: sortEvents([...s.events, mapApiEvent(raw)]) }));

        const numericId = parseInt(ideaId, 10);
        if (!isNaN(numericId)) {
          try {
            await fetch(`${API}/trips/${tripId}/ideas/${numericId}`, {
              method: 'DELETE',
              headers: { Authorization: `Bearer ${token}` },
            });
          } catch {
            toastBus("Saved to your timeline, but couldn't clear it from the bin", { kind: 'info' });
          }
        }
      } else {
        set((s) => ({ events: sortEvents([...s.events, makeLocalEvent(idea, startTime, s.events, dayDate ?? null)]) }));
        toastBus("Couldn't save to the server — kept locally", { kind: 'error' });
      }
    } catch {
      set((s) => ({ events: sortEvents([...s.events, makeLocalEvent(idea, startTime, s.events, dayDate ?? null)]) }));
      toastBus("Network error — saved locally only", { kind: 'error' });
    }
  },

  moveEventToIdea: async (eventId, tripId, token) => {
    const { events } = get();
    const event = events.find((e) => e.id === eventId);
    if (!event) return;

    // Optimistically remove from timeline + invalidate the day's route legs
    set((s) => {
      const nextLegs = { ...s.legsByDay };
      if (event.trip_id && event.day_date) delete nextLegs[legsKey(event.trip_id, event.day_date)];
      return { events: s.events.filter((e) => e.id !== eventId), legsByDay: nextLegs };
    });

    const restoredIdea: Idea = {
      id: `restored-${eventId}`,
      title: event.title,
      lat: event.lat,
      lng: event.lng,
      start_time: event.start_time ?? null,
      end_time: event.end_time ?? null,
      added_by: event.added_by ?? null,
      up: event.up ?? 0,
      down: event.down ?? 0,
      my_vote: event.my_vote ?? 0,
    };
    set((s) => ({ ideas: [restoredIdea, ...s.ideas] }));

    if (tripId && token) {
      try {
        const res = await fetch(`${API}/events/${eventId}/move-to-bin`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const idea = await res.json();
          set((s) => ({
            ideas: s.ideas.map((i) =>
              i.id === `restored-${eventId}`
                ? {
                    id: String(idea.id), title: idea.title, lat: idea.lat ?? 0, lng: idea.lng ?? 0,
                    place_id: idea.place_id ?? null,
                    start_time: idea.start_time ? new Date(idea.start_time) : null,
                    end_time: idea.end_time ? new Date(idea.end_time) : null,
                    added_by: idea.added_by ?? null, up: idea.up ?? 0, down: idea.down ?? 0, my_vote: idea.my_vote ?? 0,
                  }
                : i
            ),
          }));
          set((s) => ({ ideasLastUpdated: s.ideasLastUpdated + 1 }));
        } else {
          toastBus("Couldn't move event back to the bin", { kind: 'error' });
        }
      } catch {
        toastBus('Network error — change may not be saved', { kind: 'error' });
      }
    }
  },

  updateEventTime: async (eventId, startTime, endTime, token) => {
    const prev = get().events.find((e) => e.id === eventId);
    set((s) => ({
      events: sortEvents(
        s.events.map((e) =>
          e.id === eventId ? { ...e, start_time: startTime, end_time: endTime } : e
        )
      ),
    }));

    if (token) {
      try {
        const res = await fetch(`${API}/events/${eventId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            start_time: startTime ? startTime.toISOString() : null,
            end_time: endTime ? endTime.toISOString() : null,
          }),
        });
        if (!res.ok) throw new Error(`status ${res.status}`);
      } catch {
        if (prev) {
          set((s) => ({
            events: sortEvents(
              s.events.map((e) =>
                e.id === eventId ? { ...e, start_time: prev.start_time, end_time: prev.end_time } : e
              )
            ),
          }));
        }
        toastBus("Couldn't update event time — reverted", { kind: 'error' });
      }
    }
  },

  toggleEventSkip: async (eventId, token) => {
    const { events } = get();
    const event = events.find((e) => e.id === eventId);
    if (!event) return;
    const newSkipped = !event.is_skipped;

    set((s) => ({
      events: s.events.map((e) =>
        e.id === eventId ? { ...e, is_skipped: newSkipped } : e
      ),
    }));

    if (token) {
      try {
        const res = await fetch(`${API}/events/${eventId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ is_skipped: newSkipped }),
        });
        if (!res.ok) throw new Error(`status ${res.status}`);
      } catch {
        set((s) => ({
          events: s.events.map((e) =>
            e.id === eventId ? { ...e, is_skipped: !newSkipped } : e
          ),
        }));
        toastBus(newSkipped ? "Couldn't skip event — reverted" : "Couldn't restore event — reverted", { kind: 'error' });
      }
    }
  },

  reorderEvent: async (eventId, newSortOrder, token) => {
    const prevOrder = get().events.find((e) => e.id === eventId)?.sort_order;
    set((s) => ({
      events: s.events.map((e) => (e.id === eventId ? { ...e, sort_order: newSortOrder } : e)),
    }));

    if (token) {
      try {
        const res = await fetch(`${API}/events/${eventId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ sort_order: newSortOrder }),
        });
        if (!res.ok) throw new Error(`status ${res.status}`);
      } catch {
        if (typeof prevOrder === 'number') {
          set((s) => ({
            events: s.events.map((e) => (e.id === eventId ? { ...e, sort_order: prevOrder } : e)),
          }));
        }
        toastBus("Couldn't save the new order — reverted", { kind: 'error' });
      }
    }
  },

  updateCollaboratorStatus: (userId, activeEventId) =>
    set((s) => ({
      collaborators: s.collaborators.map((c) =>
        c.id === userId ? { ...c, activeEventId } : c
      ),
    })),

  setTripDays: (days) => set({ tripDays: days }),

  loadTripDays: async (tripId, token) => {
    try {
      const res = await fetch(`${API}/trips/${tripId}/days`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      if (!res.ok) return;
      const raw: Record<string, unknown>[] = await res.json();
      set({
        tripDays: raw.map((d) => ({
          id: String(d.id),
          trip_id: String(d.trip_id),
          date: d.date as string,
          day_number: d.day_number as number,
        })),
      });
    } catch {
      // keep current state
    }
  },

  addTripDay: async (tripId, date, token) => {
    try {
      const res = await fetch(`${API}/trips/${tripId}/days`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ date }),
      });
      if (!res.ok) return null;
      const raw = await res.json();
      const day: TripDay = {
        id: String(raw.id),
        trip_id: String(raw.trip_id),
        date: raw.date as string,
        day_number: raw.day_number as number,
      };
      set((s) => ({
        tripDays: [...s.tripDays, day].sort(
          (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
        ),
      }));
      return day;
    } catch {
      return null;
    }
  },

  deleteTripDay: async (tripId, dayId, token, itemsAction = 'bin') => {
    let success = false;
    try {
      const dayDate = get().tripDays.find((d) => d.id === dayId)?.date;
      const res = await fetch(`${API}/trips/${tripId}/days/${dayId}?items_action=${itemsAction}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok || res.status === 204) {
        success = true;
        if (dayDate) {
          set((s) => {
            const nextLegs = { ...s.legsByDay };
            delete nextLegs[legsKey(tripId, dayDate)];
            return { legsByDay: nextLegs };
          });
        }
        // Re-fetch days to get renumbered/re-dated state from backend
        const listRes = await fetch(`${API}/trips/${tripId}/days`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: 'no-store',
        });
        if (listRes.ok) {
          const raw: Record<string, unknown>[] = await listRes.json();
          set({
            tripDays: raw.map((d) => ({
              id: String(d.id),
              trip_id: String(d.trip_id),
              date: d.date as string,
              day_number: d.day_number as number,
            })),
          });
        }
      }
    } catch {
      // handled below
    }
    if (!success) {
      toastBus("Couldn't delete that day — please try again", { kind: 'error' });
    }
  },

  setRouteLegs: (tripId, dayDate, legs) =>
    set((s) => ({ legsByDay: { ...s.legsByDay, [legsKey(tripId, dayDate)]: legs } })),

  clearRouteLegsForDay: (tripId, dayDate) =>
    set((s) => {
      const next = { ...s.legsByDay };
      delete next[legsKey(tripId, dayDate)];
      return { legsByDay: next };
    }),

  setRouteMeta: (tripId, dayDate, meta) =>
    set((s) => ({ routeMetaByDay: { ...s.routeMetaByDay, [legsKey(tripId, dayDate)]: meta } })),

  clearRouteMetaForDay: (tripId, dayDate) =>
    set((s) => {
      const next = { ...s.routeMetaByDay };
      delete next[legsKey(tripId, dayDate)];
      return { routeMetaByDay: next };
    }),

  ideasLastUpdated: 0,

  hoveredEventId: null,
  selectedEventId: null,
  setHoveredEventId: (id) => set({ hoveredEventId: id }),
  setSelectedEventId: (id) => set({ selectedEventId: id }),

  conciergeOpen: false,
  conciergePreAction: null,
  openConcierge: (preAction = null) => set({ conciergeOpen: true, conciergePreAction: preAction }),
  closeConcierge: () => set({ conciergeOpen: false, conciergePreAction: null }),
}));


export type ReEnrichKind = 'brainstorm' | 'idea' | 'event';

export interface ReEnrichResult {
  place_id?: string | null;
  lat?: number | null;
  lng?: number | null;
  address?: string | null;
  photo_url?: string | null;
  rating?: number | null;
  description?: string | null;
  category?: string | null;
}

export async function reEnrichItem(kind: ReEnrichKind, itemId: number): Promise<ReEnrichResult> {
  const token = getToken();
  const res = await fetch(`${API}/trips/enrich`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ kind, item_id: itemId }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? 'Enrichment failed');
  }
  return res.json();
}
