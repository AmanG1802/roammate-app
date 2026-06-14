import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import BrainstormBin from '@/components/trip/BrainstormBin';
import { api } from '@/lib/api';
import { reEnrichItem } from '@/lib/store';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
vi.mock('@/lib/store', () => ({ reEnrichItem: vi.fn() }));
vi.mock('@/components/ui/EnrichmentBadge', () => ({
  default: ({ onRetry, retrying }: { onRetry: () => void; retrying?: boolean }) => (
    <button data-testid="enrichment-retry" onClick={onRetry} disabled={retrying}>retry</button>
  ),
}));

const mockApi = vi.mocked(api);
const mockReEnrich = vi.mocked(reEnrichItem);

function item(overrides: Record<string, unknown> = {}) {
  return { id: 1, title: 'Eiffel Tower', place_id: 'p1', ...overrides };
}

beforeEach(() => {
  mockApi.mockReset();
  mockReEnrich.mockReset();
});

// ── loading & list ────────────────────────────────────────────────────────────

describe('BrainstormBin — loading & list', () => {
  it('shows empty state when API returns no items', async () => {
    mockApi.mockResolvedValue([]);
    render(<BrainstormBin tripId="1" />);
    expect(await screen.findByText(/Bin is Empty/i)).toBeInTheDocument();
  });

  it('renders all item titles from the API', async () => {
    mockApi.mockResolvedValue([
      item({ id: 1, title: 'Louvre' }),
      item({ id: 2, title: 'Versailles' }),
    ]);
    render(<BrainstormBin tripId="1" />);
    await waitFor(() => expect(screen.getByText('Louvre')).toBeInTheDocument());
    expect(screen.getByText('Versailles')).toBeInTheDocument();
  });

  it('shows category badge when category is present', async () => {
    mockApi.mockResolvedValue([item({ category: 'museum', title: 'Musée d\'Orsay' })]);
    render(<BrainstormBin tripId="1" />);
    await waitFor(() => expect(screen.getByText('museum')).toBeInTheDocument());
  });

  it('shows time_category when present', async () => {
    mockApi.mockResolvedValue([item({ time_category: 'morning', title: 'Sunrise hike' })]);
    render(<BrainstormBin tripId="1" />);
    await waitFor(() => expect(screen.getByText('morning')).toBeInTheDocument());
  });

  it('shows the item count badge in the header', async () => {
    mockApi.mockResolvedValue([
      item({ id: 1, title: 'A' }),
      item({ id: 2, title: 'B' }),
      item({ id: 3, title: 'C' }),
    ]);
    render(<BrainstormBin tripId="1" />);
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument());
  });

  it('exposes a ref.refresh() that re-fetches items', async () => {
    const ref = React.createRef<{ refresh: () => void }>();
    mockApi.mockResolvedValue([item({ title: 'A' })]);
    render(<BrainstormBin tripId="1" ref={ref} />);
    await screen.findByText('A');

    mockApi.mockResolvedValue([item({ title: 'A' }), item({ id: 2, title: 'B' })]);
    ref.current!.refresh();
    await waitFor(() => expect(screen.getByText('B')).toBeInTheDocument());
  });
});

// ── delete ────────────────────────────────────────────────────────────────────

describe('BrainstormBin — delete item', () => {
  it('optimistically removes the card and calls DELETE', async () => {
    const user = userEvent.setup();
    mockApi.mockResolvedValue([item({ id: 42, title: 'Notre Dame' })]);
    render(<BrainstormBin tripId="1" />);
    await screen.findByText('Notre Dame');

    mockApi.mockResolvedValue(undefined);
    await user.click(screen.getByTitle('Delete'));

    await waitFor(() => expect(screen.queryByText('Notre Dame')).not.toBeInTheDocument());
    expect(mockApi).toHaveBeenCalledWith('/api/trips/1/brainstorm/items/42', { method: 'DELETE' });
  });
});

// ── clear all ─────────────────────────────────────────────────────────────────

describe('BrainstormBin — clear all', () => {
  it('requires a double-click confirmation before clearing', async () => {
    const user = userEvent.setup();
    mockApi.mockResolvedValue([item({ id: 1, title: 'Sacré-Cœur' })]);
    render(<BrainstormBin tripId="1" />);
    await screen.findByText('Sacré-Cœur');

    // First click → enter confirm state
    await user.click(screen.getByTitle('Clear all items'));
    expect(screen.getByTitle('Click again to confirm')).toBeInTheDocument();

    // Second click → actually clears
    mockApi.mockResolvedValue(undefined);
    await user.click(screen.getByTitle('Click again to confirm'));
    await waitFor(() => expect(screen.queryByText('Sacré-Cœur')).not.toBeInTheDocument());
    expect(mockApi).toHaveBeenCalledWith('/api/trips/1/brainstorm/items', { method: 'DELETE' });
  });
});

// ── promote all ───────────────────────────────────────────────────────────────

describe('BrainstormBin — promote all', () => {
  it('POSTs to promote with item_ids: null and dispatches idea-bin:refresh', async () => {
    const user = userEvent.setup();
    const refreshSpy = vi.fn();
    window.addEventListener('idea-bin:refresh', refreshSpy);

    mockApi.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (!opts?.method) return Promise.resolve([item()]);
      return Promise.resolve(undefined);
    });
    render(<BrainstormBin tripId="1" />);
    await screen.findByText('Eiffel Tower');

    await user.click(screen.getByText(/Add All to Idea Bin/i));

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith(
        '/api/trips/1/brainstorm/promote',
        expect.objectContaining({ method: 'POST', json: { item_ids: null } }),
      )
    );
    expect(refreshSpy).toHaveBeenCalled();
    window.removeEventListener('idea-bin:refresh', refreshSpy);
  });

  it('shows an error message when promote fails', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (!opts?.method) return Promise.resolve([item()]);
      return Promise.reject(new Error('server error'));
    });
    render(<BrainstormBin tripId="1" />);
    await screen.findByText('Eiffel Tower');

    await user.click(screen.getByText(/Add All to Idea Bin/i));

    await waitFor(() =>
      expect(screen.getByText(/Could not promote items/i)).toBeInTheDocument()
    );
  });
});

// ── selection mode + promote selection ───────────────────────────────────────

describe('BrainstormBin — selection mode', () => {
  it('enters selection mode when "Select" is clicked', async () => {
    const user = userEvent.setup();
    mockApi.mockResolvedValue([item()]);
    render(<BrainstormBin tripId="1" />);
    await screen.findByText('Eiffel Tower');

    await user.click(screen.getByText('Select'));
    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText(/Select items/i)).toBeInTheDocument();
  });

  it('exits selection mode when "Cancel" is clicked', async () => {
    const user = userEvent.setup();
    mockApi.mockResolvedValue([item()]);
    render(<BrainstormBin tripId="1" />);
    await screen.findByText('Eiffel Tower');

    await user.click(screen.getByText('Select'));
    await user.click(screen.getByText('Cancel'));
    expect(screen.getByText('Select')).toBeInTheDocument();
  });

  it('promotes selected items with their IDs', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (!opts?.method) return Promise.resolve([
        item({ id: 10, title: 'Arc de Triomphe' }),
        item({ id: 20, title: 'Panthéon' }),
      ]);
      return Promise.resolve(undefined);
    });
    render(<BrainstormBin tripId="1" />);
    await screen.findByText('Arc de Triomphe');

    await user.click(screen.getByText('Select'));
    // Click on the first card to select it
    await user.click(screen.getByText('Arc de Triomphe'));
    expect(await screen.findByText(/Send 1 to Idea Bin/i)).toBeInTheDocument();

    await user.click(screen.getByText(/Send 1 to Idea Bin/i));

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith(
        '/api/trips/1/brainstorm/promote',
        expect.objectContaining({ json: { item_ids: [10] } }),
      )
    );
  });
});

// ── enrichment retry ─────────────────────────────────────────────────────────

describe('BrainstormBin — enrichment retry', () => {
  it('shows the retry badge for items with no place_id', async () => {
    mockApi.mockResolvedValue([item({ id: 3, title: 'Unknown Spot', place_id: null })]);
    render(<BrainstormBin tripId="1" />);
    await screen.findByText('Unknown Spot');
    expect(screen.getByTestId('enrichment-retry')).toBeInTheDocument();
  });

  it('calls reEnrichItem and patches the item on success', async () => {
    mockApi.mockResolvedValue([item({ id: 3, title: 'Unknown Spot', place_id: null })]);
    mockReEnrich.mockResolvedValue({
      place_id: 'new-id',
      address: '1 Rue de Rivoli',
      photo_url: null,
      rating: null,
      description: null,
      category: 'landmark',
    });

    render(<BrainstormBin tripId="1" />);
    await screen.findByText('Unknown Spot');

    fireEvent.click(screen.getByTestId('enrichment-retry'));
    await waitFor(() => expect(mockReEnrich).toHaveBeenCalledWith('brainstorm', 3));
  });
});
