import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useTripStore, legsKey, reEnrichItem } from '@/lib/store';
import type { Event, Idea, TripDay } from '@/lib/store';
import { api } from '@/lib/api';
import { toastBus } from '@/lib/toast-bus';

// Store tests exercise state logic, not the network. Mock at the api boundary.
vi.mock('@/lib/api', () => ({ api: vi.fn() }));
vi.mock('@/lib/toast-bus', () => ({ toastBus: vi.fn() }));

const mockApi = vi.mocked(api);
const mockToast = vi.mocked(toastBus);

function makeIdea(overrides: Partial<Idea> = {}): Idea {
  return { id: 'idea-1', title: 'Coffee', lat: 1, lng: 2, ...overrides };
}

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'ev-1',
    trip_id: '1',
    title: 'Coffee',
    start_time: null,
    end_time: null,
    lat: 1,
    lng: 2,
    sort_order: 0,
    day_date: null,
    ...overrides,
  };
}

function makeDay(overrides: Partial<TripDay> = {}): TripDay {
  return { id: 'd1', trip_id: '1', date: '2026-06-14', day_number: 1, ...overrides };
}

beforeEach(() => {
  mockApi.mockReset();
  mockToast.mockReset();
  useTripStore.setState({
    activeTripId: '1',
    activeTripTimezone: null,
    ideas: [],
    events: [],
    tripDays: [],
    legsByDay: {},
    routeMetaByDay: {},
    ideasLastUpdated: 0,
    hoveredEventId: null,
    selectedEventId: null,
    conciergeOpen: false,
    conciergePreAction: null,
    collaborators: [
      { id: '1', name: 'You', color: '#4f46e5' },
      { id: '2', name: 'Sarah', color: '#ec4899' },
    ],
  });
});

// ── Synchronous state actions ───────────────────────────────────────────────

describe('store — basic mutations', () => {
  it('adds ideas to the front', () => {
    useTripStore.getState().addIdea(makeIdea({ id: 'a' }));
    useTripStore.getState().addIdea(makeIdea({ id: 'b' }));
    expect(useTripStore.getState().ideas.map((i) => i.id)).toEqual(['b', 'a']);
  });

  it('removes an idea by id', () => {
    useTripStore.setState({ ideas: [makeIdea({ id: 'a' }), makeIdea({ id: 'b' })] });
    useTripStore.getState().removeIdea('a');
    expect(useTripStore.getState().ideas.map((i) => i.id)).toEqual(['b']);
  });

  it('updates collaborator status', () => {
    useTripStore.getState().updateCollaboratorStatus('2', 'event-1');
    const sarah = useTripStore.getState().collaborators.find((c) => c.id === '2');
    expect(sarah?.activeEventId).toBe('event-1');
  });

  it('setActiveTrip resets per-trip state', () => {
    useTripStore.setState({ events: [makeEvent()], ideas: [makeIdea()], tripDays: [makeDay()] });
    useTripStore.getState().setActiveTrip('99');
    const s = useTripStore.getState();
    expect(s.activeTripId).toBe('99');
    expect(s.events).toEqual([]);
    expect(s.ideas).toEqual([]);
    expect(s.tripDays).toEqual([]);
  });
});

// ── Sorting ──────────────────────────────────────────────────────────────────

describe('store — event sorting', () => {
  it('setEvents sorts timed events by (day, start_time) and TBD last', () => {
    const late = makeEvent({ id: 'late', start_time: '14:00:00' });
    const early = makeEvent({ id: 'early', start_time: '09:00:00' });
    const tbd = makeEvent({ id: 'tbd', start_time: null, sort_order: 5 });
    useTripStore.getState().setEvents([tbd, late, early]);
    expect(useTripStore.getState().events.map((e) => e.id)).toEqual(['early', 'late', 'tbd']);
  });

  it('orders timed events across days by day first', () => {
    const d2 = makeEvent({ id: 'd2', day_date: '2026-06-15', start_time: '08:00:00' });
    const d1 = makeEvent({ id: 'd1', day_date: '2026-06-14', start_time: '20:00:00' });
    useTripStore.getState().setEvents([d2, d1]);
    expect(useTripStore.getState().events.map((e) => e.id)).toEqual(['d1', 'd2']);
  });

  it('setEventsRaw preserves caller order (no re-sort)', () => {
    const late = makeEvent({ id: 'late', start_time: '14:00:00' });
    const early = makeEvent({ id: 'early', start_time: '09:00:00' });
    useTripStore.getState().setEventsRaw([late, early]);
    expect(useTripStore.getState().events.map((e) => e.id)).toEqual(['late', 'early']);
  });
});

// ── moveIdeaToTimeline ─────────────────────────────────────────────────────

describe('store — moveIdeaToTimeline', () => {
  it('moves idea locally in demo mode (no tripId, no API call)', async () => {
    useTripStore.setState({ ideas: [makeIdea({ id: 'x', title: 'Museum' })] });
    await useTripStore.getState().moveIdeaToTimeline('x', null, null, '10:00:00');

    const s = useTripStore.getState();
    expect(s.ideas).toHaveLength(0);
    expect(s.events).toHaveLength(1);
    expect(s.events[0].title).toBe('Museum');
    expect(s.events[0].start_time).toBe('10:00:00');
    expect(mockApi).not.toHaveBeenCalled();
  });

  it('POSTs the event then DELETEs the idea from the bin on success', async () => {
    useTripStore.setState({ ideas: [makeIdea({ id: '42', title: 'Museum' })] });
    mockApi.mockImplementation((url: string, opts?: any) => {
      if (url === '/api/events' && opts?.method === 'POST') {
        return Promise.resolve({ id: 100, trip_id: 1, title: 'Museum', lat: 1, lng: 2, sort_order: 1 });
      }
      return Promise.resolve(undefined);
    });

    await useTripStore.getState().moveIdeaToTimeline('42', '1', 'token', null);

    const deleteCall = mockApi.mock.calls.find(
      ([url, opts]) => url === '/api/trips/1/ideas/42' && (opts as any)?.method === 'DELETE',
    );
    expect(deleteCall).toBeTruthy();
    expect(useTripStore.getState().events.find((e) => e.id === '100')).toBeTruthy();
  });

  it('keeps a local fallback event and toasts when the POST fails', async () => {
    useTripStore.setState({ ideas: [makeIdea({ id: '99', title: 'Cafe' })] });
    mockApi.mockRejectedValue(new Error('network'));

    await useTripStore.getState().moveIdeaToTimeline('99', '1', 'token', '08:00:00');

    const s = useTripStore.getState();
    expect(s.ideas).toHaveLength(0);
    expect(s.events).toHaveLength(1);
    expect(s.events[0].title).toBe('Cafe');
    expect(mockToast).toHaveBeenCalled();
  });

  it('is a no-op for an unknown idea id', async () => {
    await useTripStore.getState().moveIdeaToTimeline('missing', '1', 'token', null);
    expect(useTripStore.getState().events).toHaveLength(0);
    expect(mockApi).not.toHaveBeenCalled();
  });
});

// ── moveEventToIdea ──────────────────────────────────────────────────────────

describe('store — moveEventToIdea', () => {
  it('preserves start_time when sending an event back to the bin', async () => {
    useTripStore.setState({ events: [makeEvent({ id: 'ev-42', start_time: '15:00:00' })] });
    await useTripStore.getState().moveEventToIdea('ev-42', null, null);

    const { ideas, events } = useTripStore.getState();
    expect(events).toHaveLength(0);
    expect(ideas).toHaveLength(1);
    expect(ideas[0].start_time).toBe('15:00:00');
  });

  it('round-trips idea → timeline → bin in demo mode', async () => {
    useTripStore.setState({ ideas: [makeIdea({ id: 'idea-1', start_time: '14:00:00' })] });
    await useTripStore.getState().moveIdeaToTimeline('idea-1', null, null, '14:00:00');
    const eventId = useTripStore.getState().events[0].id;
    await useTripStore.getState().moveEventToIdea(eventId, null, null);
    expect(useTripStore.getState().ideas[0].start_time).toBe('14:00:00');
  });

  it('replaces the optimistic idea with the server idea on success', async () => {
    useTripStore.setState({ events: [makeEvent({ id: 'ev-7', title: 'Park' })] });
    mockApi.mockResolvedValue({ id: 555, title: 'Park', lat: 1, lng: 2 });

    await useTripStore.getState().moveEventToIdea('ev-7', '1', 'token');

    const { ideas, ideasLastUpdated } = useTripStore.getState();
    expect(ideas.find((i) => i.id === '555')).toBeTruthy();
    expect(ideas.find((i) => i.id === 'restored-ev-7')).toBeFalsy();
    expect(ideasLastUpdated).toBe(1);
  });

  it('toasts when the move-to-bin API fails', async () => {
    useTripStore.setState({ events: [makeEvent({ id: 'ev-8' })] });
    mockApi.mockRejectedValue(new Error('network'));
    await useTripStore.getState().moveEventToIdea('ev-8', '1', 'token');
    expect(mockToast).toHaveBeenCalled();
  });
});

// ── updateEventTime ──────────────────────────────────────────────────────────

describe('store — updateEventTime', () => {
  it('applies the new time optimistically', async () => {
    useTripStore.setState({ events: [makeEvent({ id: 'ev-1', start_time: '09:00:00' })] });
    mockApi.mockResolvedValue(undefined);
    await useTripStore.getState().updateEventTime('ev-1', '11:00:00', '12:00:00', null);
    const ev = useTripStore.getState().events.find((e) => e.id === 'ev-1');
    expect(ev?.start_time).toBe('11:00:00');
    expect(ev?.end_time).toBe('12:00:00');
  });

  it('reverts to the previous time and toasts on failure', async () => {
    useTripStore.setState({ events: [makeEvent({ id: 'ev-1', start_time: '09:00:00', end_time: '10:00:00' })] });
    mockApi.mockRejectedValue(new Error('boom'));
    await useTripStore.getState().updateEventTime('ev-1', '11:00:00', '12:00:00', null);
    const ev = useTripStore.getState().events.find((e) => e.id === 'ev-1');
    expect(ev?.start_time).toBe('09:00:00');
    expect(ev?.end_time).toBe('10:00:00');
    expect(mockToast).toHaveBeenCalled();
  });
});

// ── toggleEventSkip ──────────────────────────────────────────────────────────

describe('store — toggleEventSkip', () => {
  it('flips is_skipped optimistically', async () => {
    useTripStore.setState({ events: [makeEvent({ id: 'ev-1', is_skipped: false })] });
    mockApi.mockResolvedValue(undefined);
    await useTripStore.getState().toggleEventSkip('ev-1', null);
    expect(useTripStore.getState().events[0].is_skipped).toBe(true);
  });

  it('reverts on failure', async () => {
    useTripStore.setState({ events: [makeEvent({ id: 'ev-1', is_skipped: false })] });
    mockApi.mockRejectedValue(new Error('boom'));
    await useTripStore.getState().toggleEventSkip('ev-1', null);
    expect(useTripStore.getState().events[0].is_skipped).toBe(false);
    expect(mockToast).toHaveBeenCalled();
  });
});

// ── reorderEvent ─────────────────────────────────────────────────────────────

describe('store — reorderEvent', () => {
  it('updates sort_order without re-sorting the array', async () => {
    const late = makeEvent({ id: 'late', start_time: '14:00:00', sort_order: 0 });
    const early = makeEvent({ id: 'early', start_time: '09:00:00', sort_order: 1 });
    useTripStore.getState().setEventsRaw([late, early]);
    mockApi.mockResolvedValue(undefined);

    await useTripStore.getState().reorderEvent('late', 5, null);

    const events = useTripStore.getState().events;
    expect(events.map((e) => e.id)).toEqual(['late', 'early']);
    expect(events.find((e) => e.id === 'late')?.sort_order).toBe(5);
  });

  it('reverts sort_order on failure', async () => {
    useTripStore.getState().setEventsRaw([makeEvent({ id: 'ev-1', sort_order: 3 })]);
    mockApi.mockRejectedValue(new Error('boom'));
    await useTripStore.getState().reorderEvent('ev-1', 9, null);
    expect(useTripStore.getState().events[0].sort_order).toBe(3);
    expect(mockToast).toHaveBeenCalled();
  });
});

// ── loadEvents ───────────────────────────────────────────────────────────────

describe('store — loadEvents', () => {
  it('maps and sorts events from the API', async () => {
    mockApi.mockResolvedValue([
      { id: 2, trip_id: 1, title: 'Late', start_time: '18:00:00' },
      { id: 1, trip_id: 1, title: 'Early', start_time: '08:00:00' },
    ]);
    await useTripStore.getState().loadEvents('1', 'token');
    expect(useTripStore.getState().events.map((e) => e.title)).toEqual(['Early', 'Late']);
  });

  it('keeps existing state on network error', async () => {
    useTripStore.setState({ events: [makeEvent({ id: 'keep' })] });
    mockApi.mockRejectedValue(new Error('offline'));
    await useTripStore.getState().loadEvents('1', 'token');
    expect(useTripStore.getState().events.map((e) => e.id)).toEqual(['keep']);
  });
});

// ── Trip days ────────────────────────────────────────────────────────────────

describe('store — trip days', () => {
  it('loads and maps trip days', async () => {
    mockApi.mockResolvedValue([{ id: 1, trip_id: 1, date: '2026-06-14', day_number: 1 }]);
    await useTripStore.getState().loadTripDays('1', 'token');
    expect(useTripStore.getState().tripDays).toEqual([
      { id: '1', trip_id: '1', date: '2026-06-14', day_number: 1 },
    ]);
  });

  it('inserts a new day in date order', async () => {
    useTripStore.setState({ tripDays: [makeDay({ id: 'd2', date: '2026-06-16', day_number: 2 })] });
    mockApi.mockResolvedValue({ id: 9, trip_id: 1, date: '2026-06-15', day_number: 1 });
    await useTripStore.getState().addTripDay('1', '2026-06-15', 'token');
    expect(useTripStore.getState().tripDays.map((d) => d.date)).toEqual(['2026-06-15', '2026-06-16']);
  });

  it('returns null and leaves state intact when addTripDay fails', async () => {
    mockApi.mockRejectedValue(new Error('boom'));
    const result = await useTripStore.getState().addTripDay('1', '2026-06-15', 'token');
    expect(result).toBeNull();
    expect(useTripStore.getState().tripDays).toEqual([]);
  });

  it('re-fetches days after a successful delete', async () => {
    useTripStore.setState({ tripDays: [makeDay({ id: 'd1', date: '2026-06-14' })] });
    mockApi.mockImplementation((url: string, opts?: any) => {
      if (opts?.method === 'DELETE') return Promise.resolve(undefined);
      return Promise.resolve([{ id: 2, trip_id: 1, date: '2026-06-15', day_number: 1 }]);
    });
    await useTripStore.getState().deleteTripDay('1', 'd1', 'token');
    expect(useTripStore.getState().tripDays.map((d) => d.id)).toEqual(['2']);
    expect(mockToast).not.toHaveBeenCalled();
  });

  it('toasts when delete fails', async () => {
    useTripStore.setState({ tripDays: [makeDay({ id: 'd1' })] });
    mockApi.mockRejectedValue(new Error('boom'));
    await useTripStore.getState().deleteTripDay('1', 'd1', 'token');
    expect(mockToast).toHaveBeenCalled();
  });
});

// ── Route legs / meta ────────────────────────────────────────────────────────

describe('store — route legs and meta', () => {
  it('legsKey builds a stable composite key', () => {
    expect(legsKey('7', '2026-06-14')).toBe('7::2026-06-14');
  });

  it('sets and clears route legs for a day', () => {
    useTripStore.getState().setRouteLegs('1', '2026-06-14', [
      { from_event_id: 'a', to_event_id: 'b', duration_s: 60, distance_m: 100 },
    ]);
    expect(useTripStore.getState().legsByDay[legsKey('1', '2026-06-14')]).toHaveLength(1);

    useTripStore.getState().clearRouteLegsForDay('1', '2026-06-14');
    expect(useTripStore.getState().legsByDay[legsKey('1', '2026-06-14')]).toBeUndefined();
  });

  it('removeEvent clears the legs for that event day', () => {
    const ev = makeEvent({ id: 'ev-1', trip_id: '1', day_date: '2026-06-14' });
    useTripStore.setState({
      events: [ev],
      legsByDay: { [legsKey('1', '2026-06-14')]: [{ from_event_id: 'a', to_event_id: 'b', duration_s: 1, distance_m: 1 }] },
    });
    useTripStore.getState().removeEvent('ev-1');
    expect(useTripStore.getState().legsByDay[legsKey('1', '2026-06-14')]).toBeUndefined();
  });

  it('sets and clears route meta', () => {
    const meta = { fingerprint: 'abc', computedAt: '2026-06-14T00:00:00Z', isStale: false };
    useTripStore.getState().setRouteMeta('1', '2026-06-14', meta);
    expect(useTripStore.getState().routeMetaByDay[legsKey('1', '2026-06-14')]).toEqual(meta);
    useTripStore.getState().clearRouteMetaForDay('1', '2026-06-14');
    expect(useTripStore.getState().routeMetaByDay[legsKey('1', '2026-06-14')]).toBeUndefined();
  });
});

// ── Map highlight + concierge ─────────────────────────────────────────────────

describe('store — ui state', () => {
  it('tracks hovered and selected event ids', () => {
    useTripStore.getState().setHoveredEventId('ev-1');
    useTripStore.getState().setSelectedEventId('ev-2');
    expect(useTripStore.getState().hoveredEventId).toBe('ev-1');
    expect(useTripStore.getState().selectedEventId).toBe('ev-2');
  });

  it('opens the concierge with a pre-action and closes it', () => {
    useTripStore.getState().openConcierge({ type: 'add_event', payload: { x: 1 } });
    expect(useTripStore.getState().conciergeOpen).toBe(true);
    expect(useTripStore.getState().conciergePreAction).toEqual({ type: 'add_event', payload: { x: 1 } });

    useTripStore.getState().closeConcierge();
    expect(useTripStore.getState().conciergeOpen).toBe(false);
    expect(useTripStore.getState().conciergePreAction).toBeNull();
  });
});

// ── reEnrichItem ─────────────────────────────────────────────────────────────

describe('reEnrichItem', () => {
  it('POSTs kind + item_id to the enrich endpoint', async () => {
    mockApi.mockResolvedValue({ place_id: 'p1', lat: 1, lng: 2 });
    const result = await reEnrichItem('event', 33);
    expect(mockApi).toHaveBeenCalledWith('/api/trips/enrich', {
      method: 'POST',
      json: { kind: 'event', item_id: 33 },
    });
    expect(result).toEqual({ place_id: 'p1', lat: 1, lng: 2 });
  });
});
