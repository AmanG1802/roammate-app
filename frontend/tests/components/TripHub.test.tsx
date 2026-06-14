import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import TripHubPage from '@/app/(authenticated)/trips/[id]/page';
import { api, ApiError } from '@/lib/api';

// Keep the real ApiError (the page does `err instanceof ApiError`); mock only api().
vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, api: vi.fn() };
});
vi.mock('framer-motion', () => import('../helpers/framerMock'));

const routerPush = vi.fn();
const routerPrefetch = vi.fn();
vi.mock('next/navigation', () => ({
  useParams: () => ({ id: '42' }),
  useRouter: () => ({ push: routerPush, prefetch: routerPrefetch }),
}));
vi.mock('next/link', () => ({
  default: ({ href, children, onClick }: any) => <a href={href} onClick={onClick}>{children}</a>,
}));

const authState: { user: any } = { user: { id: 1, name: 'Me' } };
vi.mock('@/hooks/useAuth', () => ({
  default: () => ({ user: authState.user }),
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockApi = vi.mocked(api);

function makeTrip(overrides: Record<string, unknown> = {}) {
  return {
    id: 42,
    name: 'Tokyo Adventure',
    start_date: '2026-06-14T00:00:00',
    end_date: '2026-06-18T00:00:00',
    timezone: 'Asia/Tokyo',
    ...overrides,
  };
}

function makeMembers() {
  return [
    { id: 1, user_id: 1, role: 'admin', user: { name: 'Me', avatar_url: null } },
    { id: 2, user_id: 2, role: 'view_only', user: { name: 'Sarah Lee', avatar_url: null } },
  ];
}

/** Default api wiring: trip + members load successfully; mutations resolve. */
function wireApi(over: (url: string, opts?: any) => unknown | undefined = () => undefined) {
  mockApi.mockImplementation((url: string, opts?: any) => {
    const custom = over(url, opts);
    if (custom !== undefined) return Promise.resolve(custom);
    if (url === '/api/trips/42') return Promise.resolve(makeTrip());
    if (url === '/api/trips/42/members') return Promise.resolve(makeMembers());
    return Promise.resolve(undefined);
  });
}

beforeEach(() => {
  mockApi.mockReset();
  routerPush.mockReset();
  authState.user = { id: 1, name: 'Me' };
});

// ── Load states ───────────────────────────────────────────────────────────────

describe('TripHub — load states', () => {
  it('renders the not-found state on 404', async () => {
    mockApi.mockImplementation((url: string) =>
      url === '/api/trips/42'
        ? Promise.reject(new ApiError(404, 'Not found'))
        : Promise.resolve(makeMembers()),
    );
    render(<TripHubPage />);
    expect(await screen.findByText('Trip not found.')).toBeInTheDocument();
  });

  it('renders trip identity once loaded', async () => {
    wireApi();
    render(<TripHubPage />);

    expect(await screen.findByText('Tokyo')).toBeInTheDocument();
    expect(screen.getByText('Adventure')).toBeInTheDocument();
    expect(screen.getByText('Jun 14 → Jun 18, 2026')).toBeInTheDocument();
    expect(screen.getByText('5 days')).toBeInTheDocument();
    expect(screen.getByText('Asia/Tokyo')).toBeInTheDocument();
  });

  it('shows the traveler count and members', async () => {
    wireApi();
    render(<TripHubPage />);
    expect(await screen.findByText('2 Travelers')).toBeInTheDocument();
  });
});

// ── CTA links ─────────────────────────────────────────────────────────────────

describe('TripHub — navigation links', () => {
  it('points each CTA at the right planner route', async () => {
    wireApi();
    render(<TripHubPage />);
    await screen.findByText('Tokyo');

    expect(screen.getByText('Brainstorm').closest('a')).toHaveAttribute('href', '/trips?id=42&mode=brainstorm');
    expect(screen.getByText('Open Planner').closest('a')).toHaveAttribute('href', '/trips?id=42');
    expect(screen.getByText('Live Concierge').closest('a')).toHaveAttribute('href', '/trips?id=42&mode=concierge');
    expect(screen.getByText('People').closest('a')).toHaveAttribute('href', '/trips?id=42&mode=people');
  });
});

// ── Invite flow (admin) ───────────────────────────────────────────────────────

describe('TripHub — invite', () => {
  it('invites a member and shows the success state', async () => {
    const user = userEvent.setup();
    wireApi((url, opts) => {
      if (url === '/api/trips/42/invite' && opts?.method === 'POST') {
        return { id: 3, user_id: 9, role: 'view_with_vote', user: { name: 'New Person', avatar_url: null } };
      }
      return undefined;
    });
    render(<TripHubPage />);
    await screen.findByText('Tokyo');

    await user.click(screen.getByTitle('Add traveler'));
    await user.type(screen.getByPlaceholderText('traveler@email.com'), 'new@person.com');
    await user.selectOptions(screen.getByRole('combobox'), 'view_with_vote');
    await user.click(screen.getByRole('button', { name: 'Invite' }));

    expect(await screen.findByText('✓ Added!')).toBeInTheDocument();
    const inviteCall = mockApi.mock.calls.find(([u, o]) => String(u) === '/api/trips/42/invite' && (o as any)?.method === 'POST');
    expect((inviteCall![1] as any).json).toEqual({ email: 'new@person.com', role: 'view_with_vote' });
  });

  it('surfaces the API error message when invite fails', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string, opts?: any) => {
      if (url === '/api/trips/42') return Promise.resolve(makeTrip());
      if (url === '/api/trips/42/members') return Promise.resolve(makeMembers());
      if (url === '/api/trips/42/invite') return Promise.reject(new ApiError(409, 'User already on this trip'));
      return Promise.resolve(undefined);
    });
    render(<TripHubPage />);
    await screen.findByText('Tokyo');

    await user.click(screen.getByTitle('Add traveler'));
    await user.type(screen.getByPlaceholderText('traveler@email.com'), 'dupe@person.com');
    await user.selectOptions(screen.getByRole('combobox'), 'admin');
    await user.click(screen.getByRole('button', { name: 'Invite' }));

    expect(await screen.findByText('User already on this trip')).toBeInTheDocument();
  });
});

// ── Inline edits (admin) ──────────────────────────────────────────────────────

describe('TripHub — inline edits', () => {
  it('saves an edited start date and re-renders the range', async () => {
    wireApi((url, opts) => {
      if (url === '/api/trips/42' && opts?.method === 'PATCH') {
        return makeTrip({ start_date: '2026-07-01T00:00:00', end_date: '2026-07-05T00:00:00' });
      }
      return undefined;
    });
    render(<TripHubPage />);
    await screen.findByText('Tokyo');

    fireEvent.click(screen.getByTitle('Edit start date'));
    const dateInput = document.querySelector('input[type="date"]') as HTMLInputElement;
    fireEvent.change(dateInput, { target: { value: '2026-07-01' } });
    fireEvent.keyDown(dateInput, { key: 'Enter' });

    expect(await screen.findByText('Jul 1 → Jul 5, 2026')).toBeInTheDocument();
    const patch = mockApi.mock.calls.find(([u, o]) => String(u) === '/api/trips/42' && (o as any)?.method === 'PATCH');
    expect((patch![1] as any).json).toEqual({ start_date: '2026-07-01T00:00:00' });
  });

  it('saves an edited timezone', async () => {
    wireApi((url, opts) => {
      if (url === '/api/trips/42' && opts?.method === 'PATCH') return makeTrip({ timezone: 'Europe/London' });
      return undefined;
    });
    render(<TripHubPage />);
    await screen.findByText('Tokyo');

    fireEvent.click(screen.getByTitle('Edit timezone'));
    const select = screen.getByRole('combobox') as HTMLSelectElement;
    fireEvent.change(select, { target: { value: 'Europe/London' } });
    const pill = select.closest('div')!;
    fireEvent.click(within(pill).getAllByRole('button')[0]); // save (Check)

    await waitFor(() => expect(screen.getByText('Europe/London')).toBeInTheDocument());
    const patch = mockApi.mock.calls.find(([u, o]) => String(u) === '/api/trips/42' && (o as any)?.method === 'PATCH');
    expect((patch![1] as any).json).toEqual({ timezone: 'Europe/London' });
  });
});

// ── Non-admin ─────────────────────────────────────────────────────────────────

describe('TripHub — non-admin', () => {
  it('hides invite and inline-edit controls', async () => {
    authState.user = { id: 2, name: 'Sarah Lee' }; // view_only member
    wireApi();
    render(<TripHubPage />);
    await screen.findByText('Tokyo');

    expect(screen.queryByTitle('Add traveler')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Edit start date')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Edit timezone')).not.toBeInTheDocument();
  });
});
