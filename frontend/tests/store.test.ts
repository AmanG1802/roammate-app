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
    day_date: null,
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
    const late  = makeEvent({ id: 'late',  start_time: '14:00:00', sort_order: 0 });
    const early = makeEvent({ id: 'early', start_time: '09:00:00', sort_order: 1 });

    useTripStore.getState().setEventsRaw([late, early]);

    const { events } = useTripStore.getState();
    expect(events[0].id).toBe('late');
    expect(events[1].id).toBe('early');
  });

  it('differs from setEvents which always sorts by start_time', () => {
    const late  = makeEvent({ id: 'late',  start_time: '14:00:00', sort_order: 0 });
    const early = makeEvent({ id: 'early', start_time: '09:00:00', sort_order: 1 });

    useTripStore.getState().setEvents([late, early]);
    expect(useTripStore.getState().events[0].id).toBe('early');

    useTripStore.getState().setEventsRaw([late, early]);
    expect(useTripStore.getState().events[0].id).toBe('late');
  });
});

// ── moveIdeaToTimeline ────────────────────────────────────────────────────────

describe('useTripStore – moveIdeaToTimeline', () => {
  it('moves idea to timeline in demo mode (tripId=null)', async () => {
    useTripStore.getState().addIdea(makeIdea({ id: 'test-1', title: 'Test Idea' }));

    const startTime = '10:00:00';
    await useTripStore.getState().moveIdeaToTimeline('test-1', null, null, startTime);

    const state = useTripStore.getState();
    expect(state.ideas).toHaveLength(0);
    expect(state.events).toHaveLength(1);
    expect(state.events[0].title).toBe('Test Idea');
    expect(state.events[0].start_time).toEqual(startTime);
  });

  it('startTime from idea.start_time becomes event start_time', async () => {
    const at3pm = '15:00:00';
    useTripStore.getState().addIdea(makeIdea({ id: 'idea-99', title: 'Coffee', start_time: at3pm }));

    await useTripStore.getState().moveIdeaToTimeline('idea-99', null, null, at3pm);

    const { events } = useTripStore.getState();
    expect(events[0].start_time).toBe('15:00:00');
  });

  it('calls DELETE for idea after successful event creation', async () => {
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
      return Promise.resolve({ ok: true } as Response);
    });

    await useTripStore.getState().moveIdeaToTimeline('42', '1', 'token', null);

    const calls = fetchMock.mock.calls as [string, RequestInit][];
    const deleteCall = calls.find(([url, opts]) => url.includes('/ideas/42') && opts?.method === 'DELETE');
    expect(deleteCall).toBeTruthy();
  });

  it('does NOT call DELETE for idea when event creation fails', async () => {
    useTripStore.getState().addIdea(makeIdea({ id: '99', title: 'Cafe' }));

    fetchMock.mockResolvedValue({ ok: false } as Response);

    await useTripStore.getState().moveIdeaToTimeline('99', '1', 'token', null);

    const calls = fetchMock.mock.calls as [string][];
    const deleteCalled = calls.some(([url]) => url.includes('/ideas/'));
    expect(deleteCalled).toBe(false);
  });
});

// ── moveEventToIdea ───────────────────────────────────────────────────────────

describe('useTripStore – moveEventToIdea', () => {
  it('preserves start_time when returning event to bin', async () => {
    const startTime = '15:00:00';
    useTripStore.setState({
      events: [makeEvent({ id: 'ev-42', start_time: startTime, end_time: null })],
    });

    await useTripStore.getState().moveEventToIdea('ev-42', null, null);

    const { ideas } = useTripStore.getState();
    expect(ideas).toHaveLength(1);
    expect(ideas[0].start_time).toEqual(startTime);
  });

  it('restored idea has null start_time when event had null start_time', async () => {
    useTripStore.setState({
      events: [makeEvent({ id: 'ev-43', start_time: null, end_time: null })],
    });

    await useTripStore.getState().moveEventToIdea('ev-43', null, null);

    const { ideas } = useTripStore.getState();
    expect(ideas[0].start_time == null).toBe(true);
  });

  it('round-trips start_time: idea → timeline → back to bin', async () => {
    const at2pm = '14:00:00';
    useTripStore.getState().addIdea(makeIdea({ id: 'idea-1', start_time: at2pm }));

    await useTripStore.getState().moveIdeaToTimeline('idea-1', null, null, at2pm);
    const eventId = useTripStore.getState().events[0].id;

    await useTripStore.getState().moveEventToIdea(eventId, null, null);

    const { ideas } = useTripStore.getState();
    expect(ideas).toHaveLength(1);
    expect(ideas[0].start_time).toBe('14:00:00');
  });
});

// ── reorderEvent ──────────────────────────────────────────────────────────────

describe('useTripStore – reorderEvent (Bug 4)', () => {
  it('updates sort_order without re-sorting events by start_time', async () => {
    const late  = makeEvent({ id: 'ev-late',  start_time: '14:00:00', sort_order: 0 });
    const early = makeEvent({ id: 'ev-early', start_time: '09:00:00', sort_order: 1 });

    useTripStore.getState().setEventsRaw([late, early]);

    await useTripStore.getState().reorderEvent('ev-late', 0, null);
    await useTripStore.getState().reorderEvent('ev-early', 1, null);

    const { events } = useTripStore.getState();
    expect(events[0].id).toBe('ev-late');
    expect(events[1].id).toBe('ev-early');
  });
});
