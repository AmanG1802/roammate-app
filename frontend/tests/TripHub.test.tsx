/**
 * TripHub integration tests.
 *
 * Key bugs these tests guard against:
 * - `await` inside a non-async callback (the original SyntaxError bug)
 * - Members not appearing after invite succeeds
 * - Error messages not shown on invite failure
 * - Navigation links pointing to wrong URLs
 * - Loading / not-found states not rendering
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import React from 'react';

// ── Next.js mocks ────────────────────────────���────────────────────���───────────
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useParams: () => ({ id: '42' }),
  useRouter: () => ({ push: mockPush }),
}));
vi.mock('next/link', () => ({
  default: ({ href, children, onClick }: { href: string; children: React.ReactNode; onClick?: React.MouseEventHandler<HTMLAnchorElement> }) => (
    <a href={href} onClick={onClick}>{children}</a>
  ),
}));

// ── GSAP mock (prevents DOM manipulation errors in jsdom) ─────────────────────
vi.mock('gsap', () => ({
  gsap: {
    context: (_fn: () => void, _ref: unknown) => {
      try { _fn(); } catch { /* ignore errors in gsap context */ }
      return { revert: vi.fn() };
    },
    set: vi.fn(),
    timeline: () => ({ to: vi.fn().mockReturnThis() }),
    to: vi.fn(),
  },
}));

// ── Auth mock (ProtectedRoute just renders children) ──────────────────────────
vi.mock('@/hooks/useAuth', () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  default: () => ({ user: null, isLoading: false }),
}));

// ── Import component AFTER all mocks — catches SyntaxErrors at collection time ─
// If TripHubPage has `await` in a non-async callback, this import would throw a
// SyntaxError and fail the entire test file at collection, making the bug obvious.
import TripHubPage from '../app/trips/[id]/page';

// ── Fixtures ────────────────────────────────���─────────────────────────────────
const TRIP_FIXTURE = {
  id: 42,
  name: 'Tokyo Adventures',
  start_date: '2026-04-15T00:00:00Z',
  end_date: '2026-04-22T00:00:00Z',
  created_at: '2026-04-01T00:00:00Z',
  created_by_id: 1,
};

const MEMBERS_FIXTURE = [
  {
    id: 1, trip_id: 42, user_id: 1, role: 'owner',
    user: { id: 1, name: 'Alice Smith', email: 'alice@test.com' },
  },
  {
    id: 2, trip_id: 42, user_id: 2, role: 'editor',
    user: { id: 2, name: 'Bob Jones', email: 'bob@test.com' },
  },
];

const NEW_MEMBER_FIXTURE = {
  id: 3, trip_id: 42, user_id: 3, role: 'editor',
  user: { id: 3, name: 'Carol White', email: 'carol@test.com' },
};

// ── Setup ─────────────────────────────────────────────────────────────────────
beforeEach(() => {
  vi.clearAllMocks();
  // setup.ts clears localStorage before each test; set default auth token
  localStorage.setItem('token', 'mock-token');
});

// ── Fetch helper ──────────────────────────────────────────────────────────────
function makeFetch(overrides: Record<string, object | number> = {}) {
  return vi.fn(async (url: string, _opts?: RequestInit) => {
    for (const [fragment, payload] of Object.entries(overrides)) {
      if (url.includes(fragment)) {
        if (typeof payload === 'number') {
          return {
            ok: false, status: payload,
            json: async () => ({ detail: `Error ${payload}` }),
          } as unknown as Response;
        }
        return { ok: true, json: async () => payload } as unknown as Response;
      }
    }
    // Default: trip then members
    if (url.includes('/members')) {
      return { ok: true, json: async () => MEMBERS_FIXTURE } as unknown as Response;
    }
    return { ok: true, json: async () => TRIP_FIXTURE } as unknown as Response;
  });
}

// ── Tests ─────────────────────────────────────────────────────────────────────
describe('TripHubPage', () => {

  // ── Module integrity ───────────────────────────��───────────────────────────��
  it('module imports without SyntaxError (await-in-non-async-callback guard)', () => {
    expect(TripHubPage).toBeDefined();
    expect(typeof TripHubPage).toBe('function');
  });

  // ── Loading state ───────────────────────────────────────────────────────────
  it('shows loading spinner before data arrives', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    render(<TripHubPage />);
    expect(screen.getByText(/Loading Trip/i)).toBeTruthy();
  });

  // ── Rendered trip content ───────────────────────────────────────────────────
  it('renders every word of the trip name', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => expect(screen.getByText('Tokyo')).toBeTruthy());
    expect(screen.getByText('Adventures')).toBeTruthy();
  });

  it('renders the date range from trip data', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => screen.getByText(/Apr 15/));
  });

  it('renders the trip duration pill', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => screen.getByText(/8 days/i));
  });

  it('renders traveler count', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => screen.getByText(/2 Travelers/i));
  });

  it('renders member initials for all members', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => {
      expect(screen.getByText('AS')).toBeTruthy(); // Alice Smith
      expect(screen.getByText('BJ')).toBeTruthy(); // Bob Jones
    });
  });

  it('shows owner star badge on owner member', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => screen.getByText('★'));
  });

  // ── Not-found state ─────────────────────────────────────────────────────────
  it('shows not-found message when API returns 403', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/members')) {
        return { ok: false, status: 403, json: async () => ({ detail: 'Forbidden' }) } as unknown as Response;
      }
      return { ok: false, status: 403, json: async () => ({ detail: 'Forbidden' }) } as unknown as Response;
    }));
    render(<TripHubPage />);
    await waitFor(() => screen.getByText(/Trip not found/i));
  });

  // ── Navigation links ────────────────────────────────────────────────────────
  it('Open Planner link points to /trips?id=42', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => screen.getByText(/Open Planner/i));
    const link = screen.getByText(/Open Planner/i).closest('a');
    expect(link?.getAttribute('href')).toBe('/trips?id=42');
  });

  it('Live Concierge link points to /trips?id=42&mode=concierge', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => screen.getByText(/Live Concierge/i));
    const link = screen.getByText(/Live Concierge/i).closest('a');
    expect(link?.getAttribute('href')).toBe('/trips?id=42&mode=concierge');
  });

  it('back link points to /dashboard', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => screen.getByText(/All Trips/i));
    const link = screen.getByText(/All Trips/i).closest('a');
    expect(link?.getAttribute('href')).toBe('/dashboard');
  });

  // ── Invite form toggle ──────────────────────────────────────────────────────
  it('invite form is hidden initially', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => screen.getByText(/2 Travelers/i));
    expect(screen.queryByPlaceholderText(/traveler@email/i)).toBeNull();
  });

  it('invite form appears after clicking + button', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => screen.getByTitle(/Add traveler/i));
    fireEvent.click(screen.getByTitle(/Add traveler/i));
    await waitFor(() => expect(screen.getByPlaceholderText(/traveler@email/i)).toBeTruthy());
  });

  it('invite form hides when toggled a second time', async () => {
    vi.stubGlobal('fetch', makeFetch());
    render(<TripHubPage />);
    await waitFor(() => screen.getByTitle(/Add traveler/i));
    fireEvent.click(screen.getByTitle(/Add traveler/i)); // open
    await waitFor(() => screen.getByPlaceholderText(/traveler@email/i));
    fireEvent.click(screen.getByTitle(/Add traveler/i)); // close
    await waitFor(() => expect(screen.queryByPlaceholderText(/traveler@email/i)).toBeNull());
  });

  // ── Invite success — THIS IS THE PRIMARY REGRESSION TEST FOR THE BUG ────────
  // Before the fix: `setMembers((prev) => [...prev, await res.json()])` was a
  // SyntaxError. After the fix: `const newMember = await res.json(); setMembers(…)`.
  // This test proves the member list updates correctly after a successful invite.
  it('adds new member to the list after successful invite (regression: await-in-callback)', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/members')) return { ok: true, json: async () => MEMBERS_FIXTURE } as unknown as Response;
      if (url.includes('/invite')) return { ok: true, json: async () => NEW_MEMBER_FIXTURE } as unknown as Response;
      return { ok: true, json: async () => TRIP_FIXTURE } as unknown as Response;
    }));

    render(<TripHubPage />);
    await waitFor(() => screen.getByText(/2 Travelers/i));

    // Open form, fill, submit
    fireEvent.click(screen.getByTitle(/Add traveler/i));
    await waitFor(() => screen.getByPlaceholderText(/traveler@email/i));
    fireEvent.change(screen.getByPlaceholderText(/traveler@email/i), {
      target: { value: 'carol@test.com' },
    });
    const inviteBtn = screen.getByRole('button', { name: /^Invite$/i });
    fireEvent.click(inviteBtn);

    // Carol White's initials and updated count should both appear
    await waitFor(() => {
      expect(screen.getByText('CW')).toBeTruthy();
      // The count is spread across React text nodes so use a function matcher
      const countEl = screen.getByText(
        (_content, el) => el?.tagName === 'SPAN' && (el.textContent ?? '').includes('3'),
      );
      expect(countEl).toBeTruthy();
    });
  });

  it('fires POST with correct body and Authorization header', async () => {
    const fetchSpy = vi.fn(async (url: string) => {
      if (url.includes('/members')) return { ok: true, json: async () => MEMBERS_FIXTURE } as unknown as Response;
      if (url.includes('/invite')) return { ok: true, json: async () => NEW_MEMBER_FIXTURE } as unknown as Response;
      return { ok: true, json: async () => TRIP_FIXTURE } as unknown as Response;
    });
    vi.stubGlobal('fetch', fetchSpy);

    render(<TripHubPage />);
    await waitFor(() => screen.getByTitle(/Add traveler/i));
    fireEvent.click(screen.getByTitle(/Add traveler/i));
    await waitFor(() => screen.getByPlaceholderText(/traveler@email/i));
    fireEvent.change(screen.getByPlaceholderText(/traveler@email/i), {
      target: { value: 'carol@test.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^Invite$/i }));

    await waitFor(() => screen.getByText('CW'));

    const inviteCall = (fetchSpy.mock.calls as [string, RequestInit?][]).find(
      ([url]) => url.includes('/invite')
    );
    expect(inviteCall).toBeTruthy();
    const body = JSON.parse(inviteCall![1]?.body as string);
    expect(body.email).toBe('carol@test.com');
    const headers = inviteCall![1]?.headers as Record<string, string>;
    expect(headers['Authorization']).toBe('Bearer mock-token');
  });

  // ── Invite error paths ──────────────────────────────────────────────────────
  it('shows "No account found" error on 404 invite response', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/members')) return { ok: true, json: async () => MEMBERS_FIXTURE } as unknown as Response;
      if (url.includes('/invite')) {
        return { ok: false, status: 404, json: async () => ({ detail: 'No account found with that email' }) } as unknown as Response;
      }
      return { ok: true, json: async () => TRIP_FIXTURE } as unknown as Response;
    }));

    render(<TripHubPage />);
    await waitFor(() => screen.getByTitle(/Add traveler/i));
    fireEvent.click(screen.getByTitle(/Add traveler/i));
    await waitFor(() => screen.getByPlaceholderText(/traveler@email/i));
    fireEvent.change(screen.getByPlaceholderText(/traveler@email/i), {
      target: { value: 'ghost@nobody.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^Invite$/i }));

    await waitFor(() => screen.getByText(/No account found with that email/i));
    // Member count must stay at 2
    expect(screen.getByText(/2 Travelers/i)).toBeTruthy();
  });

  it('shows "already a member" error on 409 invite response', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/members')) return { ok: true, json: async () => MEMBERS_FIXTURE } as unknown as Response;
      if (url.includes('/invite')) {
        return { ok: false, status: 409, json: async () => ({ detail: 'User is already a member of this trip' }) } as unknown as Response;
      }
      return { ok: true, json: async () => TRIP_FIXTURE } as unknown as Response;
    }));

    render(<TripHubPage />);
    await waitFor(() => screen.getByTitle(/Add traveler/i));
    fireEvent.click(screen.getByTitle(/Add traveler/i));
    await waitFor(() => screen.getByPlaceholderText(/traveler@email/i));
    fireEvent.change(screen.getByPlaceholderText(/traveler@email/i), {
      target: { value: 'alice@test.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^Invite$/i }));

    await waitFor(() => screen.getByText(/already a member/i));
  });

  it('clears error when user types a new email after a failed invite', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/members')) return { ok: true, json: async () => MEMBERS_FIXTURE } as unknown as Response;
      if (url.includes('/invite')) {
        return { ok: false, json: async () => ({ detail: 'No account found with that email' }) } as unknown as Response;
      }
      return { ok: true, json: async () => TRIP_FIXTURE } as unknown as Response;
    }));

    render(<TripHubPage />);
    await waitFor(() => screen.getByTitle(/Add traveler/i));
    fireEvent.click(screen.getByTitle(/Add traveler/i));
    await waitFor(() => screen.getByPlaceholderText(/traveler@email/i));
    const input = screen.getByPlaceholderText(/traveler@email/i);
    fireEvent.change(input, { target: { value: 'ghost@nobody.com' } });
    fireEvent.click(screen.getByRole('button', { name: /^Invite$/i }));
    await waitFor(() => screen.getByText(/No account found/i));

    // Typing clears the error
    fireEvent.change(input, { target: { value: 'carol@test.com' } });
    await waitFor(() => expect(screen.queryByText(/No account found/i)).toBeNull());
  });

  it('disables Invite button while request is in-flight', async () => {
    let resolveInvite!: (v: Response) => void;
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/members')) return { ok: true, json: async () => MEMBERS_FIXTURE } as unknown as Response;
      if (url.includes('/invite')) {
        return new Promise<Response>((res) => { resolveInvite = res; });
      }
      return { ok: true, json: async () => TRIP_FIXTURE } as unknown as Response;
    }));

    render(<TripHubPage />);
    await waitFor(() => screen.getByTitle(/Add traveler/i));
    fireEvent.click(screen.getByTitle(/Add traveler/i));
    await waitFor(() => screen.getByPlaceholderText(/traveler@email/i));
    fireEvent.change(screen.getByPlaceholderText(/traveler@email/i), {
      target: { value: 'carol@test.com' },
    });

    // Get the button reference BEFORE clicking (text will change to Loader2 after)
    const inviteBtn = screen.getByRole('button', { name: /^Invite$/i });
    fireEvent.click(inviteBtn);

    // Same DOM element — disabled because inviteStatus === 'loading'
    expect(inviteBtn).toBeDisabled();

    // Clean up: resolve the pending promise
    await act(async () => {
      resolveInvite({ ok: true, json: async () => NEW_MEMBER_FIXTURE } as unknown as Response);
    });
  });

  it('Enter key submits the invite form', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/members')) return { ok: true, json: async () => MEMBERS_FIXTURE } as unknown as Response;
      if (url.includes('/invite')) return { ok: true, json: async () => NEW_MEMBER_FIXTURE } as unknown as Response;
      return { ok: true, json: async () => TRIP_FIXTURE } as unknown as Response;
    }));

    render(<TripHubPage />);
    await waitFor(() => screen.getByTitle(/Add traveler/i));
    fireEvent.click(screen.getByTitle(/Add traveler/i));
    await waitFor(() => screen.getByPlaceholderText(/traveler@email/i));
    const input = screen.getByPlaceholderText(/traveler@email/i);
    fireEvent.change(input, { target: { value: 'carol@test.com' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => expect(screen.getByText('CW')).toBeTruthy());
  });

  // ── Unauthenticated ─────────────────────────────────────────────────────────
  it('redirects to /login when no token in localStorage', async () => {
    // beforeEach sets a token, so remove it for this specific test
    localStorage.removeItem('token');
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));

    render(<TripHubPage />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login'));
  });
});
