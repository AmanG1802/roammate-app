/**
 * Timeline.test.tsx
 *
 * Comprehensive tests for the Timeline component covering:
 *  - Render (empty state, event list)
 *  - Drag from Idea Bin → empty timeline area  (regression: must always work)
 *  - Drag from Idea Bin → on top of an existing event card  (regression: was broken)
 *  - [Bug 1] time_hint from idea is passed as startTime to moveIdeaToTimeline
 *  - Drag-to-reorder within timeline
 *  - [Bug 4] Manual reorder calls setEventsRaw (not setEvents) so sortEvents can't undo it
 *  - "Move to bin" button
 *  - TBD badge when start_time is null
 *  - Time badge shown when start_time is set
 *  - Inline time editor (open, confirm, cancel)
 *  - Conflict detection (red border when events overlap)
 *  - loadEvents called on mount with tripId
 *  - loadEvents NOT called when tripId is null
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Timeline from '../components/trip/Timeline';
import { useTripStore } from '../lib/store';
import type { Event, Idea } from '../lib/store';

// ── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('../lib/store', () => ({
  useTripStore: vi.fn(),
}));

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...props}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('token', 'test-token');
  fetchMock.mockResolvedValue({ ok: false } as Response);
});

const mockLoadEvents      = vi.fn();
const mockMoveIdea        = vi.fn();
const mockMoveEventToIdea = vi.fn();
const mockUpdateTime      = vi.fn();
const mockReorderEvent    = vi.fn();
const mockSetEventsRaw    = vi.fn();

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'ev-1',
    trip_id: '1',
    title: 'Louvre Museum',
    start_time: new Date('2026-05-01T10:00:00'),
    end_time:   new Date('2026-05-01T12:00:00'),
    lat: 48.86,
    lng: 2.33,
    sort_order: 0,
    ...overrides,
  };
}

function makeIdea(overrides: Partial<Idea> = {}): Idea {
  return {
    id: 'idea-1',
    title: 'Coffee',
    lat: 0,
    lng: 0,
    ...overrides,
  };
}

function mockStore(events: Event[] = [], ideas: Idea[] = []) {
  (useTripStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    events,
    ideas,
    loadEvents:         mockLoadEvents,
    moveIdeaToTimeline: mockMoveIdea,
    moveEventToIdea:    mockMoveEventToIdea,
    updateEventTime:    mockUpdateTime,
    reorderEvent:       mockReorderEvent,
    setEventsRaw:       mockSetEventsRaw,
  });
}

/**
 * Minimal dataTransfer stub understood by RTL's fireEvent.
 * setData / getData mirror a real DataTransfer object.
 */
function makeDataTransfer(preset: Record<string, string> = {}) {
  const store: Record<string, string> = { ...preset };
  return {
    setData: vi.fn((k: string, v: string) => { store[k] = v; }),
    getData: vi.fn((k: string) => store[k] ?? ''),
    clearData: vi.fn(),
    effectAllowed: 'all',
    dropEffect: 'none',
    files: [],
    items: [],
    types: Object.keys(store),
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Timeline – render', () => {
  it('shows empty-state drop zone when there are no events', () => {
    mockStore([]);
    render(<Timeline tripId={null} />);
    expect(screen.getByTestId('empty-drop-zone')).toBeTruthy();
    expect(screen.getByText(/build your day/i)).toBeTruthy();
  });

  it('renders event cards when events exist', () => {
    mockStore([makeEvent(), makeEvent({ id: 'ev-2', title: 'Notre Dame', sort_order: 1 })]);
    render(<Timeline tripId={null} />);
    expect(screen.getByText('Louvre Museum')).toBeTruthy();
    expect(screen.getByText('Notre Dame')).toBeTruthy();
  });

  it('shows concierge-mode empty text when filterDay is provided', () => {
    mockStore([]);
    render(<Timeline tripId={null} filterDay={new Date()} />);
    expect(screen.getByText(/no events for this day/i)).toBeTruthy();
  });
});

describe('Timeline – API mount behaviour', () => {
  it('calls loadEvents on mount when tripId is provided', () => {
    mockStore([]);
    render(<Timeline tripId="42" />);
    expect(mockLoadEvents).toHaveBeenCalledOnce();
    expect(mockLoadEvents).toHaveBeenCalledWith('42', 'test-token');
  });

  it('does NOT call loadEvents when tripId is null', () => {
    mockStore([]);
    render(<Timeline tripId={null} />);
    expect(mockLoadEvents).not.toHaveBeenCalled();
  });

  it('does NOT call loadEvents when no token in localStorage', () => {
    localStorage.removeItem('token');
    mockStore([]);
    render(<Timeline tripId="42" />);
    expect(mockLoadEvents).not.toHaveBeenCalled();
  });
});

describe('Timeline – drag from Idea Bin', () => {
  /**
   * REGRESSION: drag-to-timeline must work whether the user drops on the empty
   * container area OR directly on top of an existing event card.
   */

  it('handles idea drop onto the empty container area (no time_hint)', () => {
    mockStore([]);
    render(<Timeline tripId="1" />);

    const dt = makeDataTransfer({ ideaId: 'idea-99' });
    const container = screen.getByTestId('timeline-container');

    fireEvent.dragOver(container, { dataTransfer: dt });
    fireEvent.drop(container, { dataTransfer: dt });

    expect(mockMoveIdea).toHaveBeenCalledOnce();
    // No idea in store → startTime must be null
    expect(mockMoveIdea).toHaveBeenCalledWith('idea-99', '1', 'test-token', null);
  });

  it('[Bug 1] passes parsed time from time_hint as startTime when idea has time_hint', () => {
    mockStore([], [makeIdea({ id: 'idea-99', time_hint: '3pm' })]);
    render(<Timeline tripId="1" />);

    const dt = makeDataTransfer({ ideaId: 'idea-99' });
    const container = screen.getByTestId('timeline-container');

    fireEvent.drop(container, { dataTransfer: dt });

    expect(mockMoveIdea).toHaveBeenCalledOnce();
    const [, , , startTime] = mockMoveIdea.mock.calls[0] as [string, string, string, Date | null];
    expect(startTime).toBeInstanceOf(Date);
    expect((startTime as Date).getHours()).toBe(15); // 3pm = 15:00
  });

  it('[Bug 1] passes null startTime when idea has no time_hint', () => {
    mockStore([], [makeIdea({ id: 'idea-99', time_hint: null })]);
    render(<Timeline tripId="1" />);

    const dt = makeDataTransfer({ ideaId: 'idea-99' });
    fireEvent.drop(screen.getByTestId('timeline-container'), { dataTransfer: dt });

    const [, , , startTime] = mockMoveIdea.mock.calls[0] as [string, string, string, Date | null];
    expect(startTime).toBeNull();
  });

  it('[Bug 1][REGRESSION] idea dropped onto an existing event card also carries time_hint', () => {
    mockStore([makeEvent()], [makeIdea({ id: 'idea-77', time_hint: '2:30pm' })]);
    render(<Timeline tripId="1" />);

    const dt = makeDataTransfer({ ideaId: 'idea-77' });
    const card = screen.getByTestId('event-card-ev-1');

    fireEvent.dragOver(card, { dataTransfer: dt });
    fireEvent.drop(card, { dataTransfer: dt });

    expect(mockMoveIdea).toHaveBeenCalledOnce();
    const [, , , startTime] = mockMoveIdea.mock.calls[0] as [string, string, string, Date | null];
    expect(startTime).toBeInstanceOf(Date);
    expect((startTime as Date).getHours()).toBe(14);   // 2pm portion
    expect((startTime as Date).getMinutes()).toBe(30);  // :30 portion
  });

  it('[REGRESSION] handles idea drop onto an existing event card (no time_hint)', () => {
    mockStore([makeEvent()]);
    render(<Timeline tripId="1" />);

    const dt = makeDataTransfer({ ideaId: 'idea-77' });
    const card = screen.getByTestId('event-card-ev-1');

    fireEvent.dragOver(card, { dataTransfer: dt });
    fireEvent.drop(card, { dataTransfer: dt });

    expect(mockMoveIdea).toHaveBeenCalledOnce();
    expect(mockMoveIdea).toHaveBeenCalledWith('idea-77', '1', 'test-token', null);
  });

  it('calls moveIdeaToTimeline with null token when no token in localStorage', () => {
    localStorage.removeItem('token');
    mockStore([]);
    render(<Timeline tripId="1" />);

    const dt = makeDataTransfer({ ideaId: 'idea-1' });
    const container = screen.getByTestId('timeline-container');
    fireEvent.drop(container, { dataTransfer: dt });

    expect(mockMoveIdea).toHaveBeenCalledWith('idea-1', '1', null, null);
  });

  it('does nothing when dropped data has no ideaId', () => {
    mockStore([]);
    render(<Timeline tripId="1" />);

    const dt = makeDataTransfer({}); // no ideaId
    const container = screen.getByTestId('timeline-container');
    fireEvent.drop(container, { dataTransfer: dt });

    expect(mockMoveIdea).not.toHaveBeenCalled();
  });
});

describe('Timeline – drag-to-reorder', () => {
  it('[Bug 4] calls setEventsRaw (not setEvents) so manual order is preserved', () => {
    const ev1 = makeEvent({ id: 'ev-1', title: 'Louvre', sort_order: 0 });
    const ev2 = makeEvent({ id: 'ev-2', title: 'Eiffel', sort_order: 1 });
    mockStore([ev1, ev2]);
    render(<Timeline tripId="1" />);

    const card1 = screen.getByTestId('event-card-ev-1');
    const card2 = screen.getByTestId('event-card-ev-2');

    const dt = makeDataTransfer({ reorderEventId: 'ev-2' });

    fireEvent.dragStart(card2, { dataTransfer: dt });
    fireEvent.dragOver(card1, { dataTransfer: dt });
    fireEvent.drop(card1, { dataTransfer: dt });

    expect(mockSetEventsRaw).toHaveBeenCalled();
    expect(mockReorderEvent).toHaveBeenCalled();
  });

  it('[Bug 4] reorders events when an event is dragged onto another', () => {
    const ev1 = makeEvent({ id: 'ev-1', title: 'Louvre', sort_order: 0 });
    const ev2 = makeEvent({ id: 'ev-2', title: 'Eiffel', sort_order: 1 });
    mockStore([ev1, ev2]);
    render(<Timeline tripId="1" />);

    const card1 = screen.getByTestId('event-card-ev-1');
    const dt = makeDataTransfer({ reorderEventId: 'ev-2' });

    fireEvent.dragStart(screen.getByTestId('event-card-ev-2'), { dataTransfer: dt });
    fireEvent.dragOver(card1, { dataTransfer: dt });
    fireEvent.drop(card1, { dataTransfer: dt });

    // setEventsRaw must be called with ev-2 before ev-1
    const [reordered] = mockSetEventsRaw.mock.calls[0] as [Event[]];
    expect(reordered[0].id).toBe('ev-2');
    expect(reordered[1].id).toBe('ev-1');
  });

  it('does not reorder when source and target are the same event', () => {
    mockStore([makeEvent()]);
    render(<Timeline tripId="1" />);

    const card = screen.getByTestId('event-card-ev-1');
    const dt = makeDataTransfer({ reorderEventId: 'ev-1' });

    fireEvent.dragOver(card, { dataTransfer: dt });
    fireEvent.drop(card, { dataTransfer: dt });

    expect(mockSetEventsRaw).not.toHaveBeenCalled();
  });

  it('does not call moveIdeaToTimeline when dropping a reorder drag', () => {
    mockStore([makeEvent({ id: 'ev-1' }), makeEvent({ id: 'ev-2', title: 'Eiffel', sort_order: 1 })]);
    render(<Timeline tripId="1" />);

    const card1 = screen.getByTestId('event-card-ev-1');
    const dt = makeDataTransfer({ reorderEventId: 'ev-2' });

    fireEvent.drop(card1, { dataTransfer: dt });

    expect(mockMoveIdea).not.toHaveBeenCalled();
  });
});

describe('Timeline – "Move to bin" button', () => {
  it('calls moveEventToIdea when the button is clicked', () => {
    mockStore([makeEvent()]);
    render(<Timeline tripId="1" />);

    fireEvent.click(screen.getByTestId('move-to-bin-ev-1'));

    expect(mockMoveEventToIdea).toHaveBeenCalledOnce();
    expect(mockMoveEventToIdea).toHaveBeenCalledWith('ev-1', '1', 'test-token');
  });
});

describe('Timeline – TBD / time display', () => {
  it('shows TBD badge when start_time is null', () => {
    mockStore([makeEvent({ start_time: null, end_time: null })]);
    render(<Timeline tripId={null} />);
    expect(screen.getByTestId('tbd-badge-ev-1')).toBeTruthy();
    expect(screen.getByText('TBD')).toBeTruthy();
  });

  it('shows formatted time badge when start_time is set', () => {
    mockStore([makeEvent()]);
    render(<Timeline tripId={null} />);
    expect(screen.getByTestId('time-badge-ev-1')).toBeTruthy();
    // 10:00 AM
    expect(screen.getByTestId('time-badge-ev-1').textContent).toContain('10:00 AM');
  });
});

describe('Timeline – inline time editor', () => {
  it('opens the time editor when TBD badge is clicked', () => {
    mockStore([makeEvent({ start_time: null, end_time: null })]);
    render(<Timeline tripId={null} />);

    fireEvent.click(screen.getByTestId('tbd-badge-ev-1'));
    expect(screen.getByTestId('time-editor-ev-1')).toBeTruthy();
  });

  it('opens the time editor when the time badge is clicked', () => {
    mockStore([makeEvent()]);
    render(<Timeline tripId={null} />);

    fireEvent.click(screen.getByTestId('time-badge-ev-1'));
    expect(screen.getByTestId('time-editor-ev-1')).toBeTruthy();
  });

  it('calls updateEventTime with parsed time on confirm', () => {
    mockStore([makeEvent({ start_time: null, end_time: null })]);
    render(<Timeline tripId={null} />);

    fireEvent.click(screen.getByTestId('tbd-badge-ev-1'));

    const startInput = screen.getByLabelText('Start time') as HTMLInputElement;
    const endInput   = screen.getByLabelText('End time')   as HTMLInputElement;

    fireEvent.change(startInput, { target: { value: '09:00' } });
    fireEvent.change(endInput,   { target: { value: '11:00' } });
    fireEvent.click(screen.getByLabelText('Confirm time'));

    expect(mockUpdateTime).toHaveBeenCalledOnce();
    const [id, start, end] = mockUpdateTime.mock.calls[0];
    expect(id).toBe('ev-1');
    expect(start).toBeInstanceOf(Date);
    expect(end).toBeInstanceOf(Date);
  });

  it('closes the editor without saving on cancel', () => {
    mockStore([makeEvent({ start_time: null, end_time: null })]);
    render(<Timeline tripId={null} />);

    fireEvent.click(screen.getByTestId('tbd-badge-ev-1'));
    fireEvent.click(screen.getByLabelText('Cancel time edit'));

    expect(mockUpdateTime).not.toHaveBeenCalled();
    expect(screen.queryByTestId('time-editor-ev-1')).toBeNull();
  });
});

describe('Timeline – conflict detection', () => {
  it('shows conflict icon when adjacent events have overlapping times', () => {
    const ev1 = makeEvent({
      id: 'ev-1',
      title: 'Morning Tour',
      start_time: new Date('2026-05-01T10:00:00'),
      end_time:   new Date('2026-05-01T13:00:00'), // ends at 1pm
      sort_order: 0,
    });
    const ev2 = makeEvent({
      id: 'ev-2',
      title: 'Lunch',
      start_time: new Date('2026-05-01T12:00:00'), // starts at noon — conflicts with ev1
      end_time:   new Date('2026-05-01T14:00:00'),
      sort_order: 1,
    });
    mockStore([ev1, ev2]);
    render(<Timeline tripId={null} />);

    // ev2's time badge should have a conflict indicator
    expect(screen.getByTestId('conflict-icon')).toBeTruthy();
  });

  it('does NOT show conflict icon when events do not overlap', () => {
    const ev1 = makeEvent({
      id: 'ev-1',
      title: 'Morning Tour',
      start_time: new Date('2026-05-01T09:00:00'),
      end_time:   new Date('2026-05-01T11:00:00'),
      sort_order: 0,
    });
    const ev2 = makeEvent({
      id: 'ev-2',
      title: 'Lunch',
      start_time: new Date('2026-05-01T12:00:00'), // starts after ev1 ends
      end_time:   new Date('2026-05-01T14:00:00'),
      sort_order: 1,
    });
    mockStore([ev1, ev2]);
    render(<Timeline tripId={null} />);

    expect(screen.queryByTestId('conflict-icon')).toBeNull();
  });

  it('does NOT show conflict when either event has a null time', () => {
    const ev1 = makeEvent({ id: 'ev-1', sort_order: 0 });
    const ev2 = makeEvent({ id: 'ev-2', title: 'Eiffel', start_time: null, end_time: null, sort_order: 1 });
    mockStore([ev1, ev2]);
    render(<Timeline tripId={null} />);

    expect(screen.queryByTestId('conflict-icon')).toBeNull();
  });

  it('[Bug 4] conflict icon appears when manually reordered events overlap', () => {
    // After a manual reorder, the rendered order drives conflict detection.
    // ev2 (ends 1pm) placed before ev1 (starts noon) → overlap expected.
    const ev2 = makeEvent({
      id: 'ev-2', title: 'Morning Tour',
      start_time: new Date('2026-05-01T09:00:00'),
      end_time:   new Date('2026-05-01T13:00:00'),
      sort_order: 0,  // placed first after reorder
    });
    const ev1 = makeEvent({
      id: 'ev-1', title: 'Lunch',
      start_time: new Date('2026-05-01T12:00:00'),
      end_time:   new Date('2026-05-01T14:00:00'),
      sort_order: 1,  // placed second after reorder
    });
    // Provide in the manually reordered sequence (ev2 first, ev1 second)
    mockStore([ev2, ev1]);
    render(<Timeline tripId={null} />);

    expect(screen.getByTestId('conflict-icon')).toBeTruthy();
  });
});
