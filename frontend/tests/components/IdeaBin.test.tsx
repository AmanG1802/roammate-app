import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import IdeaBin from '@/components/trip/IdeaBin';
import { useTripStore } from '@/lib/store';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));

// Leaf children with their own network/UI concerns — stub them out.
vi.mock('@/components/trip/VoteControl', () => ({
  default: () => <div data-testid="vote-control" />,
}));
vi.mock('@/components/ui/EnrichmentBadge', () => ({
  default: ({ onRetry }: { onRetry: () => void }) => (
    <button data-testid="enrichment-retry" onClick={onRetry}>retry</button>
  ),
}));

// framer-motion → plain DOM elements with stable identities (see helper).
vi.mock('framer-motion', () => import('../helpers/framerMock'));

const mockApi = vi.mocked(api);

function ideaRow(overrides: Record<string, unknown> = {}) {
  return { id: 1, title: 'Eiffel Tower', lat: 48.8, lng: 2.3, place_id: 'p1', ...overrides };
}

beforeEach(() => {
  mockApi.mockReset();
  useTripStore.setState({ ideas: [], ideasLastUpdated: 0 });
});

describe('IdeaBin — loading & list', () => {
  it('shows the empty state once loading resolves with no ideas', async () => {
    mockApi.mockResolvedValue([]);
    render(<IdeaBin tripId="1" />);
    expect(await screen.findByText(/Bin is Empty/i)).toBeInTheDocument();
  });

  it('renders idea cards from the API with formatted times', async () => {
    mockApi.mockResolvedValue([
      ideaRow({ id: 1, title: 'Eiffel Tower', start_time: '14:30:00' }),
      ideaRow({ id: 2, title: 'Louvre', start_time: null }),
    ]);
    render(<IdeaBin tripId="1" />);

    await waitFor(() => expect(screen.getByText('Eiffel Tower')).toBeInTheDocument());
    expect(screen.getByText('Louvre')).toBeInTheDocument();
    expect(screen.getByText('2:30pm')).toBeInTheDocument();
    expect(screen.getByText('No time')).toBeInTheDocument();
  });

  it('derives a time from time_category when start_time is absent', async () => {
    mockApi.mockResolvedValue([ideaRow({ id: 1, title: 'Brunch', time_category: 'morning' })]);
    render(<IdeaBin tripId="1" />);
    // 'morning' → 10:00 → "10am"
    await waitFor(() => expect(screen.getByText('10am')).toBeInTheDocument());
  });
});

describe('IdeaBin — ingest', () => {
  it('POSTs the ingest text and appends returned ideas', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string, opts?: any) => {
      if (url.endsWith('/ideas')) return Promise.resolve([]); // initial load
      if (url.endsWith('/ingest') && opts?.method === 'POST') {
        return Promise.resolve([{ id: 5, title: 'Colosseum', lat: 41.8, lng: 12.4 }]);
      }
      return Promise.resolve(undefined);
    });

    render(<IdeaBin tripId="1" />);
    await screen.findByText(/Bin is Empty/i);

    await user.type(screen.getByPlaceholderText(/Paste locations/i), 'Colosseum');
    // In the empty state the only button is the ingest submit button.
    await user.click(screen.getByRole('button'));

    await waitFor(() => expect(screen.getByText('Colosseum')).toBeInTheDocument());
    const ingestCall = mockApi.mock.calls.find(([u, o]) => String(u).endsWith('/ingest') && (o as any)?.method === 'POST');
    expect(ingestCall).toBeTruthy();
    expect((ingestCall![1] as any).json).toEqual({ text: 'Colosseum' });
  });
});

describe('IdeaBin — delete', () => {
  it('optimistically removes a card and calls DELETE', async () => {
    mockApi.mockResolvedValue([ideaRow({ id: 42, title: 'Notre Dame' })]);
    render(<IdeaBin tripId="1" />);
    await screen.findByText('Notre Dame');

    mockApi.mockResolvedValue(undefined);
    fireEvent.click(screen.getByTitle('Delete idea'));

    await waitFor(() => expect(screen.queryByText('Notre Dame')).not.toBeInTheDocument());
    const del = mockApi.mock.calls.find(([u, o]) => String(u) === '/api/trips/1/ideas/42' && (o as any)?.method === 'DELETE');
    expect(del).toBeTruthy();
  });
});

describe('IdeaBin — edit time', () => {
  it('saves an edited time and PATCHes the backend', async () => {
    mockApi.mockResolvedValue([ideaRow({ id: 7, title: 'Seine Cruise', start_time: null })]);
    const { container } = render(<IdeaBin tripId="1" />);
    await screen.findByText('Seine Cruise');
    expect(screen.getByText('No time')).toBeInTheDocument();

    mockApi.mockResolvedValue(undefined);
    fireEvent.click(screen.getByTitle('Edit time'));

    const input = container.querySelector('input[type="time"]') as HTMLInputElement;
    expect(input).toBeTruthy();
    fireEvent.change(input, { target: { value: '09:15' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => expect(screen.getByText('9:15am')).toBeInTheDocument());
    const patch = mockApi.mock.calls.find(([u, o]) => String(u) === '/api/trips/1/ideas/7' && (o as any)?.method === 'PATCH');
    expect(patch).toBeTruthy();
    expect((patch![1] as any).json).toEqual({ start_time: '09:15:00' });
  });
});

describe('IdeaBin — readOnly', () => {
  it('hides delete, edit, and ingest controls', async () => {
    mockApi.mockResolvedValue([ideaRow({ id: 1, title: 'Montmartre' })]);
    render(<IdeaBin tripId="1" readOnly />);
    await screen.findByText('Montmartre');

    expect(screen.queryByTitle('Delete idea')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Edit time')).not.toBeInTheDocument();
  });
});
