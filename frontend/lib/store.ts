import { create } from 'zustand';

const API = process.env.NEXT_PUBLIC_API_URL ?? '';

/** Create a temporary local event (used when API is unavailable). */
function makeLocalEvent(
  idea: Idea,
  startTime: Date | null | undefined,
  events: Event[]
): Event {
  const maxOrder = events.reduce((m, e) => Math.max(m, e.sort_order), -1);
  return {
    id: `local-${Math.random().toString(36).slice(2, 9)}`,
    trip_id: '0',
    title: idea.title,
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
  start_time: Date | null;   // null = TBD
  end_time: Date | null;     // null = TBD
  lat: number;
  lng: number;
  sort_order: number;
}

export interface Idea {
  id: string;
  title: string;
  lat: number;
  lng: number;
  time_hint?: string | null;  // e.g. "2pm" extracted from input text
}

interface TripState {
  activeTripId: string | null;
  ideas: Idea[];
  events: Event[];
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
  moveIdeaToTimeline: (ideaId: string, tripId: string | null, token: string | null, startTime?: Date | null) => Promise<void>;

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
}

function mapApiEvent(raw: Record<string, unknown>): Event {
  return {
    id: String(raw.id),
    trip_id: String(raw.trip_id),
    title: raw.title as string,
    start_time: raw.start_time ? new Date(raw.start_time as string) : null,
    end_time: raw.end_time ? new Date(raw.end_time as string) : null,
    lat: (raw.lat as number) ?? 0,
    lng: (raw.lng as number) ?? 0,
    sort_order: (raw.sort_order as number) ?? 0,
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
      });
      if (!res.ok) return;
      const raw: Record<string, unknown>[] = await res.json();
      set({ events: sortEvents(raw.map(mapApiEvent)) });
    } catch {
      // Network error – keep current state
    }
  },

  moveIdeaToTimeline: async (ideaId, tripId, token, startTime?) => {
    const { ideas, events } = get();
    const idea = ideas.find((i) => i.id === ideaId);
    if (!idea) return;

    // Optimistically remove from ideas
    set({ ideas: ideas.filter((i) => i.id !== ideaId) });

    // Demo / no-tripId mode: create local-only event
    if (!tripId || !token) {
      const maxOrder = events.reduce((m, e) => Math.max(m, e.sort_order), 0);
      const localEvent: Event = {
        id: Math.random().toString(36).slice(2, 9),
        trip_id: '0',
        title: idea.title,
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
      const res = await fetch(`${API}/events/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          trip_id: parseInt(tripId, 10),
          title: idea.title,
          lat: idea.lat,
          lng: idea.lng,
          start_time: startTime ? startTime.toISOString() : null,
          end_time: startTime ? new Date(startTime.getTime() + 3600_000).toISOString() : null,
          sort_order: maxOrder + 1,
        }),
      });

      if (res.ok) {
        const raw = await res.json();
        set((s) => ({ events: sortEvents([...s.events, mapApiEvent(raw)]) }));

        // Await idea deletion so a rapid page-refresh can't outrun a fire-and-forget.
        const numericId = parseInt(ideaId, 10);
        if (!isNaN(numericId)) {
          try {
            await fetch(`${API}/trips/${tripId}/ideas/${numericId}`, {
              method: 'DELETE',
              headers: { Authorization: `Bearer ${token}` },
            });
          } catch {
            // Deletion failed; the idea may reappear on next load but the event is safe.
          }
        }
      } else {
        // API failed – fall back to a local-only event so the UI always works.
        // The event won't survive a reload, but it's far better than silent failure.
        set((s) => ({ events: sortEvents([...s.events, makeLocalEvent(idea, startTime, s.events)]) }));
      }
    } catch {
      // Network error – same local fallback
      set((s) => ({ events: sortEvents([...s.events, makeLocalEvent(idea, startTime, s.events)]) }));
    }
  },

  moveEventToIdea: async (eventId, tripId, token) => {
    const { events } = get();
    const event = events.find((e) => e.id === eventId);
    if (!event) return;

    // Optimistically remove from timeline
    set((s) => ({ events: s.events.filter((e) => e.id !== eventId) }));

    // Restore time_hint from the event's start_time so the clock badge reappears in the bin.
    const restoredIdea: Idea = {
      id: `restored-${eventId}`,
      title: event.title,
      lat: event.lat,
      lng: event.lng,
      time_hint: event.start_time ? formatTimeHint(event.start_time) : undefined,
    };
    set((s) => ({ ideas: [restoredIdea, ...s.ideas] }));

    if (tripId && token) {
      try {
        await fetch(`${API}/events/${eventId}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        // If delete fails, the optimistic state still reflects user intent
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
            start_time: startTime ? startTime.toISOString() : null,
            end_time: endTime ? endTime.toISOString() : null,
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
}));
