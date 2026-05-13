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
  localStorage.setItem('token', 'test-token');
  fetchMock.mockResolvedValue({ ok: false } as Response);
});

function mockStore(override: Partial<ReturnType<typeof useTripStore>> = {}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (useTripStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    ideas: [],
    addIdea: vi.fn(),
    setIdeas: vi.fn(),
    removeIdea: vi.fn(),
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
    expect(mappedIdeas[0].id).toBe('5');
  });

  it('renders clock badge with start_time when idea has start_time', () => {
    const at3pm = new Date('2026-05-01T15:00:00');
    mockStore({
      ideas: [
        { id: '1', title: 'Coffee', lat: 0, lng: 0, start_time: at3pm },
      ] as any,
    });
    render(<IdeaBin tripId={null} />);
    expect(screen.getByText('3pm')).toBeTruthy();
  });

  it('renders "No time" when idea has no start_time', () => {
    mockStore({
      ideas: [
        { id: '2', title: 'Museum', lat: 0, lng: 0 },
      ] as any,
    });
    render(<IdeaBin tripId={null} />);
    expect(screen.getByText('No time')).toBeTruthy();
  });
});
