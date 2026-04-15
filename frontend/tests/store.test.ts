import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useTripStore } from '../lib/store';
import type { Event, Idea } from '../lib/store';

// ── Helpers ───────────────────────────────────────────────────────────────────

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

beforeEach(() => {
  vi.clearAllMocks();
  fetchMock.mockResolvedValue({ ok: false } as Response);

  useTripStore.setState({
    activeTripId: '1',
    ideas: [],
    events: [],
    collaborators: [
      { id: '1', name: 'You', color: '#4f46e5' },
      { id: '2', name: 'Sarah', color: '#ec4899' },
    ],
  });
});

function makeIdea(overrides: Partial<Idea> = {}): Idea {
  return { id: 'idea-1', title: 'Coffee', lat: 0, lng: 0, ...overrides };
}

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'ev-1',
    trip_id: '1',
    title: 'Coffee',
    start_time: null,
    end_time: null,
    lat: 0,
    lng: 0,
    sort_order: 0,
    ...overrides,
  };
}

// ── Baseline store actions ────────────────────────────────────────────────────

describe('useTripStore – baseline', () => {
  it('adds an idea', () => {
    useTripStore.getState().addIdea(makeIdea({ id: 'test-1', title: 'Test Idea' }));
    expect(useTripStore.getState().ideas).toHaveLength(1);
    expect(useTripStore.getState().ideas[0].title).toBe('Test Idea');
  });

  it('updates collaborator status', () => {
    useTripStore.getState().updateCollaboratorStatus('2', 'event-1');
    const sarah = useTripStore.getState().collaborators.find((c) => c.id === '2');
    expect(sarah?.activeEventId).toBe('event-1');
  });
});

// ── setEventsRaw ──────────────────────────────────────────────────────────────

describe('useTripStore – setEventsRaw (Bug 4)', () => {
  it('preserves provided order without re-sorting by start_time', () => {
    const late  = makeEvent({ id: 'late',  start_time: new Date('2026-05-01T14:00:00'), sort_order: 0 });
    const early = makeEvent({ id: 'early', start_time: new Date('2026-05-01T09:00:00'), sort_order: 1 });

    // Place the later event first — setEventsRaw must not re-sort by time.
    useTripStore.getState().setEventsRaw([late, early]);

    const { events } = useTripStore.getState();
    expect(events[0].id).toBe('late');
    expect(events[1].id).toBe('early');
  });

  it('differs from setEvents which always sorts by start_time', () => {
    const late  = makeEvent({ id: 'late',  start_time: new Date('2026-05-01T14:00:00'), sort_order: 0 });
    const early = makeEvent({ id: 'early', start_time: new Date('2026-05-01T09:00:00'), sort_order: 1 });

    // setEvents re-sorts by start_time
    useTripStore.getState().setEvents([late, early]);
    expect(useTripStore.getState().events[0].id).toBe('early');

    // setEventsRaw keeps provided order
    useTripStore.getState().setEventsRaw([late, early]);
    expect(useTripStore.getState().events[0].id).toBe('late');
  });
});

// ── moveIdeaToTimeline ────────────────────────────────────────────────────────

describe('useTripStore – moveIdeaToTimeline', () => {
  it('moves idea to timeline in demo mode (tripId=null)', async () => {
    useTripStore.getState().addIdea(makeIdea({ id: 'test-1', title: 'Test Idea' }));

    const startTime = new Date(2026, 4, 12, 10, 0);
    await useTripStore.getState().moveIdeaToTimeline('test-1', null, null, startTime);

    const state = useTripStore.getState();
    expect(state.ideas).toHaveLength(0);
    expect(state.events).toHaveLength(1);
    expect(state.events[0].title).toBe('Test Idea');
    expect(state.events[0].start_time).toEqual(startTime);
  });

  it('[Bug 1] startTime passed from time_hint becomes event start_time', async () => {
    useTripStore.getState().addIdea(makeIdea({ id: 'idea-99', title: 'Coffee' }));

    const at3pm = new Date();
    at3pm.setHours(15, 0, 0, 0);

    // Caller (Timeline) parses time_hint → passes as startTime
    await useTripStore.getState().moveIdeaToTimeline('idea-99', null, null, at3pm);

    const { events } = useTripStore.getState();
    expect(events[0].start_time?.getHours()).toBe(15);
  });

  it('[Bug 2] calls DELETE for idea after successful event creation', async () => {
    useTripStore.getState().addIdea(makeIdea({ id: '42', title: 'Museum' }));

    fetchMock.mockImplementation((url: string) => {
      if (url.includes('/events/')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 100, trip_id: 1, title: 'Museum',
            lat: 0, lng: 0, start_time: null, end_time: null, sort_order: 0,
          }),
        } as unknown as Response);
      }
      // DELETE /ideas/42
      return Promise.resolve({ ok: true } as Response);
    });

    await useTripStore.getState().moveIdeaToTimeline('42', '1', 'token', null);

    const calls = fetchMock.mock.calls as [string, RequestInit][];
    const deleteCall = calls.find(([url, opts]) => url.includes('/ideas/42') && opts?.method === 'DELETE');
    expect(deleteCall).toBeTruthy();
  });

  it('[Bug 2] does NOT call DELETE for idea when event creation fails', async () => {
    useTripStore.getState().addIdea(makeIdea({ id: '99', title: 'Cafe' }));

    // All fetches return non-ok (event POST fails)
    fetchMock.mockResolvedValue({ ok: false } as Response);

    await useTripStore.getState().moveIdeaToTimeline('99', '1', 'token', null);

    const calls = fetchMock.mock.calls as [string][];
    const deleteCalled = calls.some(([url]) => url.includes('/ideas/'));
    expect(deleteCalled).toBe(false);
  });
});

// ── moveEventToIdea ───────────────────────────────────────────────────────────

describe('useTripStore – moveEventToIdea (Bug 3)', () => {
  it('restores time_hint from start_time when returning event to bin', async () => {
    const startTime = new Date('2026-05-01T15:00:00'); // 3pm
    useTripStore.setState({
      events: [makeEvent({ id: 'ev-42', start_time: startTime, end_time: null })],
    });

    await useTripStore.getState().moveEventToIdea('ev-42', null, null);

    const { ideas } = useTripStore.getState();
    expect(ideas).toHaveLength(1);
    expect(ideas[0].time_hint).toBeTruthy();
    expect(ideas[0].time_hint).toMatch(/3/);    // hour "3" present
    expect(ideas[0].time_hint).toMatch(/pm/i);  // am/pm marker present
  });

  it('restored idea has no time_hint when event had null start_time', async () => {
    useTripStore.setState({
      events: [makeEvent({ id: 'ev-43', start_time: null, end_time: null })],
    });

    await useTripStore.getState().moveEventToIdea('ev-43', null, null);

    const { ideas } = useTripStore.getState();
    expect(ideas[0].time_hint == null || ideas[0].time_hint === '').toBe(true);
  });

  it('round-trips time_hint: idea → timeline → back to bin', async () => {
    useTripStore.getState().addIdea(makeIdea({ id: 'idea-1', time_hint: '2pm' }));

    const at2pm = new Date();
    at2pm.setHours(14, 0, 0, 0);

    await useTripStore.getState().moveIdeaToTimeline('idea-1', null, null, at2pm);
    const eventId = useTripStore.getState().events[0].id;

    await useTripStore.getState().moveEventToIdea(eventId, null, null);

    const { ideas } = useTripStore.getState();
    expect(ideas).toHaveLength(1);
    expect(ideas[0].time_hint).toMatch(/2/);
    expect(ideas[0].time_hint).toMatch(/pm/i);
  });
});

// ── reorderEvent ──────────────────────────────────────────────────────────────

describe('useTripStore – reorderEvent (Bug 4)', () => {
  it('updates sort_order without re-sorting events by start_time', async () => {
    const late  = makeEvent({ id: 'ev-late',  start_time: new Date('2026-05-01T14:00:00'), sort_order: 0 });
    const early = makeEvent({ id: 'ev-early', start_time: new Date('2026-05-01T09:00:00'), sort_order: 1 });

    // Manually place later event first (user's drag choice)
    useTripStore.getState().setEventsRaw([late, early]);

    // reorderEvent updates sort_orders without sorting
    await useTripStore.getState().reorderEvent('ev-late', 0, null);
    await useTripStore.getState().reorderEvent('ev-early', 1, null);

    const { events } = useTripStore.getState();
    expect(events[0].id).toBe('ev-late');   // manual order preserved
    expect(events[1].id).toBe('ev-early');
  });
});
