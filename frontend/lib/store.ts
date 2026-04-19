import { create } from 'zustand';

const API = process.env.NEXT_PUBLIC_API_URL ?? '';

/**
 * Format a Date as a naive ISO-like string using *local* time values,
 * e.g. "2026-04-16T14:00:00".  Unlike Date.toISOString() (which converts to
 * UTC), this preserves the wall-clock time the user intended.  The backend
 * stores TIMESTAMP WITHOUT TIME ZONE, so sending local values avoids the
 * UTC-shift that was turning "2pm IST" into "8:30am".
 */
function toLocalISOString(d: Date): string {
  const pad = (n: number, w = 2) => String(n).padStart(w, '0');
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

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

/** Format a Date into a compact time hint string, e.g. "3pm" or "3:30pm". */
function formatTimeHint(date: Date): string {
  let h = date.getHours();
  const m = date.getMinutes();
  const ampm = h >= 12 ? 'pm' : 'am';
  if (h > 12) h -= 12;
  if (h === 0) h = 12;
  const mStr = m === 0 ? '' : `:${String(m).padStart(2, '0')}`;
  return `${h}${mStr}${ampm}`;
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
}

export interface Idea {
  id: string;
  title: string;
  lat: number;
  lng: number;
  time_hint?: string | null;  // e.g. "2pm" extracted from input text
  added_by?: string | null;   // first name of user who added the idea
  up?: number;
  down?: number;
  my_vote?: number;
}

export interface TripDay {
  id: string;
  trip_id: string;
  date: string;       // ISO date string "YYYY-MM-DD"
  day_number: number;
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

  /** Persist sort_order after manual drag-to-reorder. */
  reorderEvent: (eventId: string, newSortOrder: number, token: string | null) => Promise<void>;

  updateCollaboratorStatus: (userId: string, activeEventId?: string) => void;

  /** Trip day management */
  setTripDays: (days: TripDay[]) => void;
  loadTripDays: (tripId: string, token: string) => Promise<void>;
  addTripDay: (tripId: string, date: string, token: string) => Promise<TripDay | null>;
  deleteTripDay: (tripId: string, dayId: string, token: string, itemsAction?: 'bin' | 'delete') => Promise<void>;
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
  collaborators: [
    { id: '1', name: 'You', color: '#4f46e5' },
    { id: '2', name: 'Sarah', color: '#ec4899' },
  ],

  setActiveTrip: (id) => set({ activeTripId: id }),
  setIdeas: (ideas) => set({ ideas }),
  setEvents: (events) => set({ events: sortEvents(events) }),
  setEventsRaw: (events) => set({ events }),
  addIdea: (idea) => set((s) => ({ ideas: [idea, ...s.ideas] })),
  addEvent: (event) => set((s) => ({ events: sortEvents([...s.events, event]) })),
  removeIdea: (ideaId) => set((s) => ({ ideas: s.ideas.filter((i) => i.id !== ideaId) })),
  removeEvent: (eventId) => set((s) => ({ events: s.events.filter((e) => e.id !== eventId) })),

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
          start_time: startTime ? toLocalISOString(startTime) : null,
          end_time: startTime ? toLocalISOString(new Date(startTime.getTime() + 3600_000)) : null,
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
            // Deletion failed; idea may reappear on reload but event is safe.
          }
        }
      } else {
        set((s) => ({ events: sortEvents([...s.events, makeLocalEvent(idea, startTime, s.events, dayDate ?? null)]) }));
      }
    } catch {
      set((s) => ({ events: sortEvents([...s.events, makeLocalEvent(idea, startTime, s.events, dayDate ?? null)]) }));
    }
  },

  moveEventToIdea: async (eventId, tripId, token) => {
    const { events } = get();
    const event = events.find((e) => e.id === eventId);
    if (!event) return;

    // Optimistically remove from timeline
    set((s) => ({ events: s.events.filter((e) => e.id !== eventId) }));

    const restoredIdea: Idea = {
      id: `restored-${eventId}`,
      title: event.title,
      lat: event.lat,
      lng: event.lng,
      time_hint: event.start_time ? formatTimeHint(event.start_time) : undefined,
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
                ? { id: String(idea.id), title: idea.title, lat: idea.lat ?? 0, lng: idea.lng ?? 0, time_hint: idea.time_hint ?? null, added_by: idea.added_by ?? null, up: idea.up ?? 0, down: idea.down ?? 0, my_vote: idea.my_vote ?? 0 }
                : i
            ),
          }));
          // Nudge IdeaBin to re-fetch so enrichment (photo, description, category, etc.) hydrates
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('idea-bin:refresh'));
          }
        }
      } catch {
        // Optimistic state still reflects user intent
      }
    }
  },

  updateEventTime: async (eventId, startTime, endTime, token) => {
    set((s) => ({
      events: sortEvents(
        s.events.map((e) =>
          e.id === eventId ? { ...e, start_time: startTime, end_time: endTime } : e
        )
      ),
    }));

    if (token) {
      try {
        await fetch(`${API}/events/${eventId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            start_time: startTime ? toLocalISOString(startTime) : null,
            end_time: endTime ? toLocalISOString(endTime) : null,
          }),
        });
      } catch {
        // Silently fail; local state is already updated
      }
    }
  },

  reorderEvent: async (eventId, newSortOrder, token) => {
    // Update sort_order without re-sorting — manual drag order must be preserved.
    set((s) => ({
      events: s.events.map((e) => (e.id === eventId ? { ...e, sort_order: newSortOrder } : e)),
    }));

    if (token) {
      try {
        await fetch(`${API}/events/${eventId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ sort_order: newSortOrder }),
        });
      } catch {
        // Silently fail
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
    try {
      const res = await fetch(`${API}/trips/${tripId}/days/${dayId}?items_action=${itemsAction}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok || res.status === 204) {
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
      // keep current state
    }
  },
}));
