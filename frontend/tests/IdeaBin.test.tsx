import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import IdeaBin from '../components/trip/IdeaBin';
import { useTripStore } from '../lib/store';

vi.mock('../lib/store', () => ({
  useTripStore: vi.fn(),
}));

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

beforeEach(() => {
  vi.clearAllMocks();
  // setup.ts clears localStorage before each test
  localStorage.setItem('token', 'test-token');
  fetchMock.mockResolvedValue({ ok: false } as Response);
});

function mockStore(override: Partial<ReturnType<typeof useTripStore>> = {}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (useTripStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    ideas: [],
    addIdea: vi.fn(),
    setIdeas: vi.fn(),
    ...override,
  });
}

describe('IdeaBin Component', () => {
  it('renders empty-bin state when no ideas', () => {
    mockStore();
    render(<IdeaBin tripId={null} />);
    expect(screen.getByText(/Bin is Empty/i)).toBeTruthy();
  });

  it('renders idea cards when ideas exist', () => {
    mockStore({
      ideas: [
        { id: '1', title: 'Louvre Museum', lat: 48.86, lng: 2.33 },
        { id: '2', title: 'Notre Dame', lat: 48.85, lng: 2.34 },
      ] as any,
    });
    render(<IdeaBin tripId={null} />);
    expect(screen.getByText('Louvre Museum')).toBeTruthy();
    expect(screen.getByText('Notre Dame')).toBeTruthy();
  });

  it('updates textarea value on change', () => {
    mockStore();
    render(<IdeaBin tripId={null} />);
    const textarea = screen.getByPlaceholderText(/Paste locations/i);
    fireEvent.change(textarea, { target: { value: 'Eiffel Tower' } });
    expect((textarea as HTMLTextAreaElement).value).toBe('Eiffel Tower');
  });

  it('submit button is disabled when textarea is empty', () => {
    mockStore();
    render(<IdeaBin tripId={null} />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('submit button is enabled when textarea has content', () => {
    mockStore();
    render(<IdeaBin tripId={null} />);
    const textarea = screen.getByPlaceholderText(/Paste locations/i);
    fireEvent.change(textarea, { target: { value: 'Museum' } });
    expect(screen.getByRole('button')).not.toBeDisabled();
  });

  it('disables submit button while ingesting (tripId provided, slow API)', async () => {
    mockStore();
    fetchMock.mockImplementation(async (url: string) => {
      if (url.includes('/ideas')) return { ok: true, json: async () => [] } as unknown as Response;
      // Slow ingest endpoint — never resolves during this test
      return new Promise(() => {});
    });

    render(<IdeaBin tripId="1" />);
    const textarea = screen.getByPlaceholderText(/Paste locations/i);
    const button = screen.getByRole('button');

    fireEvent.change(textarea, { target: { value: 'Museum' } });
    fireEvent.click(button);

    expect(button).toBeDisabled();
  });

  it('falls back to local mock ideas when tripId is null', async () => {
    const addIdea = vi.fn();
    mockStore({ addIdea });

    render(<IdeaBin tripId={null} />);
    const textarea = screen.getByPlaceholderText(/Paste locations/i);
    fireEvent.change(textarea, { target: { value: 'Colosseum, Trevi Fountain' } });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => expect(addIdea).toHaveBeenCalledTimes(2));
    expect(addIdea.mock.calls[0][0].title).toBe('Colosseum');
    expect(addIdea.mock.calls[1][0].title).toBe('Trevi Fountain');
  });

  it('falls back to local mock ideas when API returns non-ok', async () => {
    const addIdea = vi.fn();
    mockStore({ addIdea });
    fetchMock.mockImplementation(async (url: string) => {
      if (url.includes('/ideas')) return { ok: true, json: async () => [] } as unknown as Response;
      return { ok: false } as Response; // ingest fails
    });

    render(<IdeaBin tripId="99" />);
    const textarea = screen.getByPlaceholderText(/Paste locations/i);
    fireEvent.change(textarea, { target: { value: 'Vatican' } });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => expect(addIdea).toHaveBeenCalledTimes(1));
    expect(addIdea.mock.calls[0][0].title).toBe('Vatican');
  });

  it('clears textarea after successful ingest', async () => {
    const addIdea = vi.fn();
    mockStore({ addIdea });

    render(<IdeaBin tripId={null} />);
    const textarea = screen.getByPlaceholderText(/Paste locations/i);
    fireEvent.change(textarea, { target: { value: 'Museum' } });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => expect((textarea as HTMLTextAreaElement).value).toBe(''));
  });

  it('fetches ideas from API on mount when tripId is provided', async () => {
    const setIdeas = vi.fn();
    mockStore({ setIdeas });
    fetchMock.mockImplementation(async (url: string) => {
      if (url.includes('/ideas')) {
        return {
          ok: true,
          json: async () => [
            { id: 5, title: 'Colosseum', lat: 41.89, lng: 12.49, trip_id: 1 },
          ],
        } as unknown as Response;
      }
      return { ok: false } as Response;
    });

    render(<IdeaBin tripId="1" />);

    await waitFor(() => expect(setIdeas).toHaveBeenCalledOnce());
    const mappedIdeas = setIdeas.mock.calls[0][0];
    expect(mappedIdeas[0].title).toBe('Colosseum');
    expect(mappedIdeas[0].id).toBe('5'); // mapped to string
  });

  // ── Bug 3 regression: time_hint clock badge must appear in the Idea Bin ──────

  it('[Bug 3] renders clock badge with time_hint text when idea has time_hint', () => {
    mockStore({
      ideas: [
        { id: '1', title: 'Coffee', lat: 0, lng: 0, time_hint: '3pm' },
      ] as any,
    });
    render(<IdeaBin tripId={null} />);

    const badge = screen.getByTestId('time-hint-badge-1');
    expect(badge).toBeTruthy();
    expect(badge.textContent).toContain('3pm');
  });

  it('[Bug 3] does NOT render clock badge when idea has no time_hint', () => {
    mockStore({
      ideas: [
        { id: '2', title: 'Museum', lat: 0, lng: 0 },
      ] as any,
    });
    render(<IdeaBin tripId={null} />);

    // No time-hint badge for this idea
    expect(screen.queryByTestId('time-hint-badge-2')).toBeNull();
  });

  // ── Bug 1: time_hint is extracted when ingesting in local/fallback mode ──────

  it('[Bug 1] extracts time_hint from text like "Coffee at 3pm" in fallback mode', async () => {
    const addIdea = vi.fn();
    mockStore({ addIdea });

    render(<IdeaBin tripId={null} />);
    const textarea = screen.getByPlaceholderText(/Paste locations/i);
    fireEvent.change(textarea, { target: { value: 'Coffee at 3pm' } });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => expect(addIdea).toHaveBeenCalledTimes(1));
    const addedIdea = addIdea.mock.calls[0][0];
    expect(addedIdea.time_hint).toBe('3pm');
    expect(addedIdea.title).not.toContain('3pm'); // title should be stripped
  });

  it('[Bug 1] extracts time_hint with hour:minute like "Museum at 2:30pm"', async () => {
    const addIdea = vi.fn();
    mockStore({ addIdea });

    render(<IdeaBin tripId={null} />);
    const textarea = screen.getByPlaceholderText(/Paste locations/i);
    fireEvent.change(textarea, { target: { value: 'Museum at 2:30pm' } });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => expect(addIdea).toHaveBeenCalledTimes(1));
    expect(addIdea.mock.calls[0][0].time_hint).toBe('2:30pm');
  });
});
