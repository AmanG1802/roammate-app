import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import NotificationBell from '@/components/layout/NotificationBell';
import type { NotificationBellHandle } from '@/components/layout/NotificationBell';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock('framer-motion', () => import('../helpers/framerMock'));

const mockApi = vi.mocked(api);

function notif(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    type: 'trip_created',
    payload: { trip_name: 'Paris Trip' },
    trip_id: 99,
    group_id: null,
    actor: null,
    read_at: null,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

beforeEach(() => {
  mockApi.mockReset();
  // Default: 0 unread, empty list
  mockApi.mockImplementation((url: string) => {
    if (url.endsWith('/unread-count')) return Promise.resolve({ unread: 0 });
    return Promise.resolve([]);
  });
});

// ── badge ─────────────────────────────────────────────────────────────────────

describe('NotificationBell — unread badge', () => {
  it('renders the bell button', async () => {
    render(<NotificationBell />);
    expect(screen.getByRole('button', { name: /Notifications/i })).toBeInTheDocument();
  });

  it('shows the unread count badge when there are unread notifications', async () => {
    mockApi.mockImplementation((url: string) => {
      if (url.endsWith('/unread-count')) return Promise.resolve({ unread: 5 });
      return Promise.resolve([]);
    });
    render(<NotificationBell />);
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /5 unread/i })).toBeInTheDocument()
    );
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('shows 99+ when unread count exceeds 99', async () => {
    mockApi.mockImplementation((url: string) => {
      if (url.endsWith('/unread-count')) return Promise.resolve({ unread: 120 });
      return Promise.resolve([]);
    });
    render(<NotificationBell />);

    // Open the bell to trigger list fetch which reveals the badge fully
    const bell = await screen.findByRole('button', { name: /Notifications/i });
    await waitFor(() => expect(screen.getByText('99+')).toBeInTheDocument());
  });
});

// ── open / close ──────────────────────────────────────────────────────────────

describe('NotificationBell — open / close', () => {
  it('opens the dropdown when the bell is clicked', async () => {
    const user = userEvent.setup();
    render(<NotificationBell />);

    await user.click(screen.getByRole('button', { name: /Notifications/i }));
    await waitFor(() =>
      expect(screen.getByText('Notifications')).toBeInTheDocument()
    );
  });

  it('closes the dropdown when clicking outside', async () => {
    const user = userEvent.setup();
    render(
      <div>
        <NotificationBell />
        <div data-testid="outside">Outside</div>
      </div>,
    );

    await user.click(screen.getByRole('button', { name: /Notifications/i }));
    await screen.findByText('Notifications');

    fireEvent.mouseDown(screen.getByTestId('outside'));
    await waitFor(() =>
      expect(screen.queryByText("You're all caught up")).not.toBeInTheDocument()
    );
  });

  it('fetches the notification list when opened', async () => {
    const user = userEvent.setup();
    render(<NotificationBell />);

    await user.click(screen.getByRole('button', { name: /Notifications/i }));

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/notifications?limit=30')
    );
  });
});

// ── empty state ───────────────────────────────────────────────────────────────

describe('NotificationBell — empty state', () => {
  it('shows "You\'re all caught up" when the list is empty', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string) => {
      if (url.endsWith('/unread-count')) return Promise.resolve({ unread: 0 });
      return Promise.resolve([]);
    });
    render(<NotificationBell />);

    await user.click(screen.getByRole('button', { name: /Notifications/i }));
    await waitFor(() =>
      expect(screen.getByText(/You're all caught up/i)).toBeInTheDocument()
    );
  });
});

// ── notification list ─────────────────────────────────────────────────────────

describe('NotificationBell — notification list', () => {
  it('renders a trip_created notification message', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string) => {
      if (url.endsWith('/unread-count')) return Promise.resolve({ unread: 1 });
      if (url.includes('/notifications')) return Promise.resolve([notif()]);
      return Promise.resolve([]);
    });
    render(<NotificationBell />);

    await user.click(screen.getByRole('button', { name: /Notifications/i }));
    await waitFor(() => expect(screen.getByText('Paris Trip')).toBeInTheDocument());
  });

  it('renders an invite_received notification', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string) => {
      if (url.endsWith('/unread-count')) return Promise.resolve({ unread: 1 });
      if (url.includes('/notifications')) {
        return Promise.resolve([
          notif({
            type: 'invite_received',
            payload: { trip_name: 'Tokyo Trip', inviter_name: 'Alice' },
          }),
        ]);
      }
      return Promise.resolve([]);
    });
    render(<NotificationBell />);

    await user.click(screen.getByRole('button', { name: /Notifications/i }));
    await waitFor(() => expect(screen.getByText('Alice')).toBeInTheDocument());
    expect(screen.getByText('Tokyo Trip')).toBeInTheDocument();
  });

  it('renders a ripple_fired notification', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string) => {
      if (url.endsWith('/unread-count')) return Promise.resolve({ unread: 1 });
      if (url.includes('/notifications')) {
        return Promise.resolve([
          notif({
            type: 'ripple_fired',
            payload: { delta_minutes: 30, shifted_count: 3 },
            actor: { id: 2, name: 'Bob', email: null },
          }),
        ]);
      }
      return Promise.resolve([]);
    });
    render(<NotificationBell />);

    await user.click(screen.getByRole('button', { name: /Notifications/i }));
    await waitFor(() => expect(screen.getByText('30m')).toBeInTheDocument());
  });
});

// ── mark read ─────────────────────────────────────────────────────────────────

describe('NotificationBell — mark read', () => {
  it('marks a notification read optimistically and calls the API', async () => {
    const user = userEvent.setup();
    const n = notif({ id: 7, read_at: null });
    mockApi.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (url.endsWith('/unread-count')) return Promise.resolve({ unread: 1 });
      if (url.includes('/notifications') && !opts) return Promise.resolve([n]);
      return Promise.resolve(undefined); // POST /read
    });
    render(<NotificationBell />);

    await user.click(screen.getByRole('button', { name: /Notifications/i }));
    await screen.findByText('Paris Trip');

    // Click the notification row to mark it read
    const notifRow = screen.getByText('Paris Trip').closest('button')!;
    await user.click(notifRow);

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith(
        '/api/notifications/7/read',
        expect.objectContaining({ method: 'POST' }),
      )
    );
  });

  it('marks all notifications read and calls mark-all-read API', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (url.endsWith('/unread-count')) return Promise.resolve({ unread: 3 });
      if (url.includes('/notifications') && !opts) return Promise.resolve([notif(), notif({ id: 2 }), notif({ id: 3 })]);
      return Promise.resolve(undefined);
    });
    render(<NotificationBell />);

    await user.click(screen.getByRole('button', { name: /Notifications/i }));
    await waitFor(() => expect(screen.getByText(/Mark all read/i)).toBeInTheDocument());

    await user.click(screen.getByText(/Mark all read/i));

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith(
        '/api/notifications/mark-all-read',
        expect.objectContaining({ method: 'POST' }),
      )
    );
  });
});

// ── refresh button ────────────────────────────────────────────────────────────

describe('NotificationBell — refresh', () => {
  it('re-fetches unread count and list when the refresh button is clicked', async () => {
    const user = userEvent.setup();
    render(<NotificationBell />);

    await user.click(screen.getByRole('button', { name: /Notifications/i }));
    await screen.findByText(/You're all caught up/i);

    const callsBefore = mockApi.mock.calls.length;
    await user.click(screen.getByTitle('Refresh'));

    await waitFor(() => expect(mockApi.mock.calls.length).toBeGreaterThan(callsBefore));
  });

  it('exposes ref.refresh() which re-fetches the unread count', async () => {
    const ref = React.createRef<NotificationBellHandle>();
    render(<NotificationBell ref={ref} />);

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/notifications/unread-count')
    );
    const callsBefore = mockApi.mock.calls.length;

    ref.current!.refresh();
    await waitFor(() => expect(mockApi.mock.calls.length).toBeGreaterThan(callsBefore));
  });
});
