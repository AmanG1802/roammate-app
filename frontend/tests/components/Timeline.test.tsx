import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import React from 'react';
import Timeline from '@/components/trip/Timeline';
import { useTripStore, legsKey } from '@/lib/store';
import type { Event } from '@/lib/store';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
vi.mock('framer-motion', () => import('../helpers/framerMock'));
vi.mock('@/components/trip/VoteControl', () => ({ default: () => <div data-testid="vote-control" /> }));
vi.mock('@/components/ui/EnrichmentBadge', () => ({
  default: ({ onRetry }: { onRetry: () => void }) => <button data-testid="enrichment-retry" onClick={onRetry} />,
}));

const mockApi = vi.mocked(api);
const DAY = '2026-06-14';

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'ev-1',
    trip_id: '1',
    title: 'Event',
    day_date: DAY,
    start_time: '09:00:00',
    end_time: '10:00:00',
    lat: 1,
    lng: 2,
    sort_order: 0,
    ...overrides,
  };
}

/** Seed events directly; the on-mount loadEvents() GET is rejected so it keeps them. */
function seed(events: Event[], opts: { days?: number } = {}) {
  useTripStore.setState({
    events,
    ideas: [],
    tripDays: Array.from({ length: opts.days ?? 1 }, (_, i) => ({
      id: `d${i}`, trip_id: '1', date: DAY, day_number: i + 1,
    })),
    legsByDay: {},
    selectedEventId: null,
  });
}

function dataTransfer() {
  const store: Record<string, string> = {};
  return { setData: (k: string, v: string) => { store[k] = v; }, getData: (k: string) => store[k] ?? '' };
}

beforeEach(() => {
  mockApi.mockReset();
  // Reject the events GET (keeps seeded state); resolve every mutation.
  mockApi.mockImplementation((url: string) =>
    String(url).startsWith('/api/events?') ? Promise.reject(new Error('skip-load')) : Promise.resolve(undefined),
  );
  useTripStore.setState({ events: [], ideas: [], tripDays: [], legsByDay: {}, selectedEventId: null });
});

// ── Empty / loading states ────────────────────────────────────────────────────

describe('Timeline — empty states', () => {
  it('prompts to add a day when no trip days exist', async () => {
    seed([], { days: 0 });
    render(<Timeline tripId="1" />);
    expect(await screen.findByText('Add a day first')).toBeInTheDocument();
  });

  it('prompts to build the day when days exist but no events', async () => {
    seed([]);
    render(<Timeline tripId="1" />);
    expect(await screen.findByTestId('empty-drop-zone')).toBeInTheDocument();
    expect(screen.getByText('Build your day')).toBeInTheDocument();
  });
});

// ── Rendering ─────────────────────────────────────────────────────────────────

describe('Timeline — rendering', () => {
  it('renders events with formatted wall-clock times', async () => {
    seed([
      makeEvent({ id: 'a', title: 'Breakfast', start_time: '08:00:00', end_time: '09:00:00' }),
      makeEvent({ id: 'b', title: 'Museum', start_time: '11:00:00', end_time: '13:00:00' }),
    ]);
    render(<Timeline tripId="1" />);

    await waitFor(() => expect(screen.getByText('Breakfast')).toBeInTheDocument());
    expect(screen.getByText('Museum')).toBeInTheDocument();
    expect(screen.getByTestId('time-badge-a')).toHaveTextContent('8:00 AM');
    expect(screen.getByTestId('time-badge-a')).toHaveTextContent('9:00 AM');
  });

  it('shows a TBD badge for events without a start time', async () => {
    seed([makeEvent({ id: 'a', title: 'Mystery', start_time: null, end_time: null })]);
    render(<Timeline tripId="1" />);
    expect(await screen.findByTestId('tbd-badge-a')).toBeInTheDocument();
  });

  it('flags an overlapping event with a conflict icon', async () => {
    seed([
      makeEvent({ id: 'a', title: 'A', start_time: '09:00:00', end_time: '11:00:00' }),
      makeEvent({ id: 'b', title: 'B', start_time: '10:00:00', end_time: '12:00:00' }),
    ]);
    render(<Timeline tripId="1" />);
    await waitFor(() => expect(screen.getByText('A')).toBeInTheDocument());

    expect(within(screen.getByTestId('time-badge-b')).getByTestId('conflict-icon')).toBeInTheDocument();
    expect(within(screen.getByTestId('time-badge-a')).queryByTestId('conflict-icon')).not.toBeInTheDocument();
  });

  it('renders hour gap dots between distant events', async () => {
    seed([
      makeEvent({ id: 'a', title: 'A', start_time: '08:00:00', end_time: '09:00:00' }),
      makeEvent({ id: 'b', title: 'B', start_time: '11:00:00', end_time: '12:00:00' }),
    ]);
    render(<Timeline tripId="1" />);
    // 09:00 → 11:00 = 2h gap → 2 dots
    expect(await screen.findByTestId('gap-dots-2')).toBeInTheDocument();
  });
});

// ── Time editing ──────────────────────────────────────────────────────────────

describe('Timeline — time editing', () => {
  it('edits an event time and PATCHes it', async () => {
    seed([makeEvent({ id: 'a', title: 'Lunch', start_time: '09:00:00', end_time: '11:00:00' })]);
    render(<Timeline tripId="1" />);
    await waitFor(() => expect(screen.getByText('Lunch')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('time-badge-a'));
    const editor = await screen.findByTestId('time-editor-a');
    fireEvent.change(within(editor).getByLabelText('Start time'), { target: { value: '10:30' } });
    fireEvent.click(within(editor).getByLabelText('Confirm time'));

    await waitFor(() => expect(screen.getByTestId('time-badge-a')).toHaveTextContent('10:30 AM'));
    const patch = mockApi.mock.calls.find(([u, o]) => String(u) === '/api/events/a' && (o as any)?.method === 'PATCH');
    expect(patch).toBeTruthy();
    expect((patch![1] as any).json).toMatchObject({ start_time: '10:30:00' });
  });

  it('keeps the editor open (confirm disabled) until a value changes', async () => {
    seed([makeEvent({ id: 'a', title: 'Lunch' })]);
    render(<Timeline tripId="1" />);
    await waitFor(() => expect(screen.getByText('Lunch')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('time-badge-a'));
    const editor = await screen.findByTestId('time-editor-a');
    expect(within(editor).getByLabelText('Confirm time')).toBeDisabled();
  });
});

// ── Move to bin / restore ─────────────────────────────────────────────────────

describe('Timeline — move to bin & restore', () => {
  it('removes an event sent back to the bin', async () => {
    seed([makeEvent({ id: 'a', title: 'Park' })]);
    render(<Timeline tripId="1" />);
    await waitFor(() => expect(screen.getByText('Park')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('move-to-bin-a'));

    await waitFor(() => expect(screen.queryByTestId('event-card-a')).not.toBeInTheDocument());
    expect(mockApi.mock.calls.some(([u]) => String(u) === '/api/events/a/move-to-bin')).toBe(true);
  });

  it('restores a skipped event', async () => {
    seed([makeEvent({ id: 'a', title: 'Beach', is_skipped: true })]);
    render(<Timeline tripId="1" />);
    await waitFor(() => expect(screen.getByText('Skipped')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('unskip-a'));

    await waitFor(() => expect(screen.queryByText('Skipped')).not.toBeInTheDocument());
    expect(mockApi.mock.calls.some(([u, o]) => String(u) === '/api/events/a' && (o as any)?.method === 'PATCH')).toBe(true);
  });
});

// ── Drag to reorder ───────────────────────────────────────────────────────────

describe('Timeline — drag reorder', () => {
  it('reorders events on drop and persists each new sort_order', async () => {
    seed([
      makeEvent({ id: 'a', title: 'First', start_time: null, end_time: null, sort_order: 0 }),
      makeEvent({ id: 'b', title: 'Second', start_time: null, end_time: null, sort_order: 1 }),
    ]);
    render(<Timeline tripId="1" />);
    await waitFor(() => expect(screen.getByText('First')).toBeInTheDocument());

    const dt = dataTransfer();
    // Drag "Second" onto "First" → inserts before → [Second, First]
    fireEvent.dragStart(screen.getByTestId('event-card-b'), { dataTransfer: dt });
    fireEvent.dragOver(screen.getByTestId('event-card-a'), { dataTransfer: dt });
    fireEvent.drop(screen.getByTestId('event-card-a'), { dataTransfer: dt });

    await waitFor(() => {
      const titles = screen.getAllByRole('heading', { level: 4 }).map((h) => h.textContent);
      expect(titles).toEqual(['Second', 'First']);
    });
    expect(mockApi.mock.calls.some(([u, o]) => String(u).startsWith('/api/events/') && (o as any)?.method === 'PATCH')).toBe(true);
  });
});

// ── filterDay + travel hints ──────────────────────────────────────────────────

describe('Timeline — filterDay & travel hints', () => {
  it('shows only the filtered day and renders the travel hint between legs', async () => {
    const day2 = '2026-06-15';
    useTripStore.setState({
      events: [
        makeEvent({ id: 'a', title: 'Day1 Morning', start_time: '09:00:00', end_time: '10:00:00', day_date: DAY }),
        makeEvent({ id: 'b', title: 'Day1 Noon', start_time: '12:00:00', end_time: '13:00:00', day_date: DAY }),
        makeEvent({ id: 'c', title: 'Day2 Thing', start_time: '09:00:00', end_time: '10:00:00', day_date: day2 }),
      ],
      ideas: [],
      tripDays: [
        { id: 'd1', trip_id: '1', date: DAY, day_number: 1 },
        { id: 'd2', trip_id: '1', date: day2, day_number: 2 },
      ],
      legsByDay: {
        [legsKey('1', DAY)]: [{ from_event_id: 'a', to_event_id: 'b', duration_s: 1200, distance_m: 8000 }],
      },
      selectedEventId: null,
    });

    render(<Timeline tripId="1" filterDay={new Date(`${DAY}T12:00:00`)} />);

    await waitFor(() => expect(screen.getByText('Day1 Morning')).toBeInTheDocument());
    expect(screen.getByText('Day1 Noon')).toBeInTheDocument();
    expect(screen.queryByText('Day2 Thing')).not.toBeInTheDocument();
    // 1200s ≈ 20 min, 8000m / 1200s ≈ 6.7 m/s → drive
    expect(screen.getByTestId('travel-hint-a')).toHaveTextContent(/20 min drive/i);
  });
});

// ── readOnly ──────────────────────────────────────────────────────────────────

describe('Timeline — readOnly', () => {
  it('hides move-to-bin and does not open the time editor', async () => {
    seed([makeEvent({ id: 'a', title: 'Locked' })]);
    render(<Timeline tripId="1" readOnly />);
    await waitFor(() => expect(screen.getByText('Locked')).toBeInTheDocument());

    expect(screen.queryByTestId('move-to-bin-a')).not.toBeInTheDocument();
    // In readOnly the time is a static span, not an edit button.
    fireEvent.click(screen.getByTestId('time-badge-a'));
    expect(screen.queryByTestId('time-editor-a')).not.toBeInTheDocument();
  });
});
