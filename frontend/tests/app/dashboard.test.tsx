/**
 * Dashboard page tests.
 *
 * Strategy: stub all heavy leaf components (map, widgets, modals) so the
 * test only exercises the glue logic in DashboardPage itself — data fetching,
 * trip grid rendering, search, section switching, create-trip modal,
 * invitations accept/decline.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';

// ── stub heavy leaf components ─────────────────────────────────────────────────

vi.mock('@/components/layout/NotificationBell', () => ({
  default: React.forwardRef((_: any, ref: any) => {
    React.useImperativeHandle(ref, () => ({ refresh: vi.fn() }));
    return <div data-testid="notification-bell" />;
  }),
}));
vi.mock('@/components/dashboard/TodayWidget', () => ({
  default: React.forwardRef((_: any, ref: any) => {
    React.useImperativeHandle(ref, () => ({ refresh: vi.fn() }));
    return null;
  }),
}));
vi.mock('@/components/dashboard/DashboardTripPlanner', () => ({ default: () => null }));
vi.mock('@/components/groups/GroupsPanel', () => ({ default: () => null }));
vi.mock('@/components/UserMenu', () => ({ default: () => null }));
vi.mock('@/components/PersonaSoftPrompt', () => ({ default: () => null }));
vi.mock('@/components/OnboardingPersonaModal', () => ({ default: () => null }));
vi.mock('@/components/billing/OnboardingPlusModal', () => ({ OnboardingPlusModal: () => null }));
vi.mock('@/components/billing/PlusBanner', () => ({
  PastDueBanner: () => null,
  OneTimeExpiryBanner: () => null,
  ReEngagementBanner: () => null,
  FreeUsageStrip: () => null,
}));

// ── nav ───────────────────────────────────────────────────────────────────────

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, prefetch: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock('next/link', () => ({
  default: ({ href, children, className }: any) => <a href={href} className={className}>{children}</a>,
}));

// ── hooks ─────────────────────────────────────────────────────────────────────

const mockUser = { id: 99, name: 'Alice', email: 'alice@example.com', personas: ['adventure'] };

vi.mock('@/hooks/useAuth', () => ({
  default: vi.fn(() => ({ user: mockUser, isLoading: false })),
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/hooks/useEntitlement', () => ({
  useEntitlement: vi.fn(),
  isNeedsPlus: vi.fn(() => null),
}));

vi.mock('@/hooks/useTutorial', () => ({
  useTutorial: vi.fn(() => ({ status: 'completed', isLoading: false, isActive: false, step: 0, trip_id: null, platform: 'web' })),
}));

vi.mock('@/components/ui/Toast', () => ({
  useToast: vi.fn(() => ({ show: vi.fn(), dismiss: vi.fn() })),
  ToastProvider: ({ children }: any) => <>{children}</>,
}));

vi.mock('@/lib/toast-bus', () => ({
  toastBus: vi.fn(),
  registerToastEmitter: vi.fn(),
}));

// ── api & utilities ───────────────────────────────────────────────────────────

vi.mock('@/lib/api', () => ({ api: vi.fn(), ApiError: class extends Error { status = 0; data = null; } }));
vi.mock('@/lib/plusOnboarding', () => ({
  hasSeenPlusOnboarding: vi.fn(() => true),
  markPlusOnboardingSeen: vi.fn(),
  clearPlusOnboardingSeen: vi.fn(),
}));

const MOTION_PROPS = new Set(['initial','animate','exit','transition','variants','whileHover','whileTap','layout','layoutId','custom','viewport','drag']);
const motionCache: Record<string, React.ElementType> = {};
const framerStub = {
  motion: new Proxy({} as Record<string, React.ElementType>, {
    get: (_, tag: string) => (motionCache[tag] ??= React.forwardRef((props: any, ref: any) => {
      const clean: Record<string, unknown> = {};
      for (const k in props) if (!MOTION_PROPS.has(k)) clean[k] = props[k];
      return React.createElement(tag, { ...clean, ref });
    })),
  }),
  AnimatePresence: ({ children }: any) => children,
  useReducedMotion: () => true,
  useAnimation: () => ({ start: () => Promise.resolve(), stop: () => {}, set: () => {} }),
  LayoutGroup: ({ children }: any) => children,
};
vi.mock('framer-motion', () => framerStub);

import { api } from '@/lib/api';
import { useEntitlement } from '@/hooks/useEntitlement';

const mockApi = vi.mocked(api);
const mockUseEntitlement = vi.mocked(useEntitlement);

function makeEntitlement() {
  return {
    entitlement: {
      tier: 'free' as const,
      status: 'none',
      brainstorm_remaining: 10,
      brainstorm_cap: 15,
      active_trip_count: 1,
      active_trip_cap: 2,
      period_end: null,
      can_use_concierge: false,
      can_create_active_trip: true,
      can_use_offline_maps: false,
      brainstorm_used: 5,
      price_inr: 149,
      onetime_price_inr: 200,
      onetime_duration_days: 30,
    },
    isLoading: false,
    isConfirmed: true,
    refresh: vi.fn(),
    requirePlus: vi.fn().mockResolvedValue(false),
    pendingPaywall: null,
    resolvePaywall: vi.fn(),
  };
}

function makeTrip(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    name: 'Paris Adventure',
    start_date: '2027-08-01',
    end_date: '2027-08-10',
    destination: 'Paris, France',
    ...overrides,
  };
}

beforeEach(() => {
  mockApi.mockReset();
  mockPush.mockReset();
  mockUseEntitlement.mockReturnValue(makeEntitlement() as ReturnType<typeof useEntitlement>);

  mockApi.mockImplementation((url: string) => {
    if (String(url) === '/api/trips') return Promise.resolve([makeTrip()]);
    if (String(url).includes('/invitations/pending')) return Promise.resolve([]);
    return Promise.resolve(undefined);
  });
});

const user = userEvent.setup();

async function renderDashboard() {
  const { default: DashboardPage } = await import('@/app/(authenticated)/dashboard/page');
  render(<DashboardPage />);
}

// ── rendering ─────────────────────────────────────────────────────────────────

describe('DashboardPage — rendering', () => {
  it('greets the user by first name', async () => {
    await renderDashboard();
    await waitFor(() => expect(screen.getByText(/Hey, Alice/i)).toBeInTheDocument());
  });

  it('renders trip cards from the API', async () => {
    mockApi.mockImplementation((url: string) => {
      if (String(url) === '/api/trips') {
        return Promise.resolve([
          makeTrip({ id: 1, name: 'Paris Adventure' }),
          makeTrip({ id: 2, name: 'Tokyo Escape' }),
        ]);
      }
      if (String(url).includes('/invitations/pending')) return Promise.resolve([]);
      return Promise.resolve(undefined);
    });
    await renderDashboard();
    await waitFor(() => expect(screen.getByText('Paris Adventure')).toBeInTheDocument());
    expect(screen.getByText('Tokyo Escape')).toBeInTheDocument();
  });

  it('shows empty state copy when the trip list is empty', async () => {
    mockApi.mockImplementation((url: string) => {
      if (String(url) === '/api/trips') return Promise.resolve([]);
      return Promise.resolve([]);
    });
    await renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/No upcoming trips/i)).toBeInTheDocument()
    );
  });

  it('shows a load error state when the trips API fails', async () => {
    mockApi.mockImplementation((url: string) => {
      if (String(url) === '/api/trips') return Promise.reject(new Error('server down'));
      return Promise.resolve([]);
    });
    await renderDashboard();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
    );
  });
});

// ── search ────────────────────────────────────────────────────────────────────

describe('DashboardPage — search', () => {
  it('filters trips by name as the user types', async () => {
    mockApi.mockImplementation((url: string) => {
      if (String(url) === '/api/trips') {
        return Promise.resolve([
          makeTrip({ id: 1, name: 'Paris Adventure' }),
          makeTrip({ id: 2, name: 'Tokyo Escape' }),
        ]);
      }
      return Promise.resolve([]);
    });
    await renderDashboard();
    await waitFor(() => expect(screen.getByText('Paris Adventure')).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText(/Search trips/i), { target: { value: 'tokyo' } });
    await waitFor(() => expect(screen.queryByText('Paris Adventure')).not.toBeInTheDocument());
    expect(screen.getByText('Tokyo Escape')).toBeInTheDocument();
  });

  it('clears the search when the × button is clicked', async () => {
    mockApi.mockImplementation((url: string) => {
      if (String(url) === '/api/trips') return Promise.resolve([makeTrip({ name: 'Tokyo Escape' })]);
      return Promise.resolve([]);
    });
    await renderDashboard();
    await waitFor(() => expect(screen.getByText('Tokyo Escape')).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText(/Search trips/i), { target: { value: 'tokyo' } });
    const clearBtn = screen.getByRole('button', { name: '' });
    await user.click(clearBtn);
    expect(screen.getByText('Tokyo Escape')).toBeInTheDocument();
  });
});

// ── section navigation ────────────────────────────────────────────────────────

describe('DashboardPage — section navigation', () => {
  it('switches to Invitations section on nav click', async () => {
    await renderDashboard();
    await waitFor(() => expect(screen.getByText('Paris Adventure')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Trip Invitations/i }));
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Trip Invitations' })).toBeInTheDocument()
    );
    expect(screen.getByText(/All quiet on the travel front/i)).toBeInTheDocument();
  });

  it('switches to My Trips section and shows current/past toggle', async () => {
    await renderDashboard();
    await waitFor(() => expect(screen.getByText('Paris Adventure')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /My Trips/i }));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Ongoing & Upcoming/i })).toBeInTheDocument()
    );
  });
});

// ── invitations ───────────────────────────────────────────────────────────────

describe('DashboardPage — invitations', () => {
  const inv = {
    id: 55,
    trip: { id: 10, name: 'Rome Trip', start_date: '2027-09-01' },
    inviter: { id: 2, name: 'Bob' },
  };

  beforeEach(() => {
    mockApi.mockImplementation((url: string, opts?: any) => {
      if (String(url) === '/api/trips') return Promise.resolve([]);
      if (String(url).includes('/invitations/pending')) return Promise.resolve([inv]);
      if (opts?.method === 'POST' || opts?.method === 'DELETE') return Promise.resolve(undefined);
      return Promise.resolve(undefined);
    });
  });

  it('shows the invitation card with trip name and inviter', async () => {
    await renderDashboard();
    await user.click(screen.getByRole('button', { name: /Trip Invitations/i }));
    await waitFor(() => expect(screen.getByText('Rome Trip')).toBeInTheDocument());
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('accepts an invitation and removes it from the list', async () => {
    await renderDashboard();
    await user.click(screen.getByRole('button', { name: /Trip Invitations/i }));
    await screen.findByText('Rome Trip');

    await user.click(screen.getByRole('button', { name: /Accept/i }));
    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/trips/invitations/55/accept', { method: 'POST' })
    );
    await waitFor(() => expect(screen.queryByText('Rome Trip')).not.toBeInTheDocument());
  });

  it('declines an invitation and removes it from the list', async () => {
    await renderDashboard();
    await user.click(screen.getByRole('button', { name: /Trip Invitations/i }));
    await screen.findByText('Rome Trip');

    await user.click(screen.getByRole('button', { name: /Decline/i }));
    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/trips/invitations/55/decline', { method: 'DELETE' })
    );
    await waitFor(() => expect(screen.queryByText('Rome Trip')).not.toBeInTheDocument());
  });
});

// ── create trip modal ─────────────────────────────────────────────────────────

describe('DashboardPage — create trip modal', () => {
  it('opens the create trip modal when "New Trip" is clicked', async () => {
    await renderDashboard();
    await user.click(screen.getByRole('button', { name: /New Trip/i }));
    await waitFor(() =>
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    );
    expect(screen.getByPlaceholderText(/Summer in Santorini/i)).toBeInTheDocument();
  });

  it('closes the modal when the × button is clicked', async () => {
    await renderDashboard();
    await user.click(screen.getByRole('button', { name: /New Trip/i }));
    await screen.findByRole('dialog');

    await user.click(screen.getByLabelText(/Close create trip dialog/i));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('submits the form and navigates to the new trip', async () => {
    mockApi.mockImplementation((url: string, opts?: any) => {
      if (String(url) === '/api/trips' && opts?.method === 'POST') {
        return Promise.resolve({ id: 42, name: 'Costa Rica' });
      }
      if (String(url) === '/api/trips') return Promise.resolve([]);
      return Promise.resolve([]);
    });
    await renderDashboard();
    await user.click(screen.getByRole('button', { name: /New Trip/i }));
    const dialog = await screen.findByRole('dialog');

    act(() => {
      fireEvent.change(within(dialog).getByPlaceholderText(/Summer in Santorini/i), { target: { value: 'Costa Rica' } });
      fireEvent.change(dialog.querySelector('input[type="date"]') as HTMLInputElement, { target: { value: '2025-11-01' } });
    });
    await user.click(within(dialog).getByRole('button', { name: 'Create Trip' }));

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/trips', expect.objectContaining({
        method: 'POST',
        json: expect.objectContaining({ name: 'Costa Rica' }),
      }))
    );
    expect(mockPush).toHaveBeenCalledWith('/trips/42');
  });

  it('shows an error message when trip creation fails', async () => {
    mockApi.mockImplementation((url: string, opts?: any) => {
      if (String(url) === '/api/trips' && opts?.method === 'POST') {
        return Promise.reject(new Error('Trip limit reached'));
      }
      return Promise.resolve([]);
    });
    await renderDashboard();
    await user.click(screen.getByRole('button', { name: /New Trip/i }));
    const dialog = await screen.findByRole('dialog');

    act(() => {
      fireEvent.change(within(dialog).getByPlaceholderText(/Summer in Santorini/i), { target: { value: 'New Trip' } });
      fireEvent.change(dialog.querySelector('input[type="date"]') as HTMLInputElement, { target: { value: '2025-12-01' } });
    });
    await user.click(within(dialog).getByRole('button', { name: 'Create Trip' }));

    await waitFor(() =>
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    );
  });
});

// ── TripGrid inline actions ───────────────────────────────────────────────────

describe('DashboardPage — TripGrid delete', () => {
  it('shows delete confirmation and calls DELETE API', async () => {
    mockApi.mockImplementation((url: string, opts?: any) => {
      if (String(url) === '/api/trips') {
        return Promise.resolve([makeTrip({ id: 7, name: 'Kyoto Journey', my_role: 'admin' })]);
      }
      if (opts?.method === 'DELETE') return Promise.resolve(undefined);
      return Promise.resolve([]);
    });
    await renderDashboard();
    await waitFor(() => expect(screen.getByText('Kyoto Journey')).toBeInTheDocument());

    await user.click(screen.getByTitle('Delete trip'));
    const alertDialog = await screen.findByRole('alertdialog');
    await user.click(within(alertDialog).getByRole('button', { name: /Delete Trip/i }));

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/trips/7', { method: 'DELETE' })
    );
  });
});
