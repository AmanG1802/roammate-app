/**
 * Billing component tests: CouponInput, BrainstormQuotaPill, PlusBanner variants.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';

// ── shared mocks ──────────────────────────────────────────────────────────────

vi.mock('framer-motion', () => import('../helpers/framerMock'));
vi.mock('next/link', () => ({
  default: ({ href, children, className }: any) => <a href={href} className={className}>{children}</a>,
}));

// ── api mock ──────────────────────────────────────────────────────────────────
// ApiError must be hoisted so the vi.mock factory (which is hoisted by vitest) can close over it.

const ApiError = vi.hoisted(() => {
  return class extends Error {
    status: number;
    data: unknown;
    constructor(status: number, message: string, data: unknown = null) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.data = data;
    }
  };
});

vi.mock('@/lib/api', () => ({ api: vi.fn(), ApiError }));
vi.mock('@/lib/motion', () => ({ motionTokens: { ease: { out: 'easeOut' } } }));

import { api } from '@/lib/api';
const mockApi = vi.mocked(api);

// ── useEntitlement mock ───────────────────────────────────────────────────────

vi.mock('@/hooks/useEntitlement', () => ({
  useEntitlement: vi.fn(),
}));

import { useEntitlement } from '@/hooks/useEntitlement';
const mockUseEntitlement = vi.mocked(useEntitlement);

function makeEntitlement(overrides: Record<string, unknown> = {}) {
  return {
    entitlement: {
      tier: 'free',
      status: 'none',
      brainstorm_remaining: 10,
      brainstorm_cap: 15,
      active_trip_count: 1,
      active_trip_cap: 2,
      period_end: null,
      ...overrides,
    },
    isLoading: false,
    isConfirmed: true,
    requirePlus: vi.fn().mockResolvedValue(false),
    refresh: vi.fn(),
    pendingPaywall: null,
    resolvePaywall: vi.fn(),
  };
}

beforeEach(() => {
  mockApi.mockReset();
  mockUseEntitlement.mockReturnValue(makeEntitlement() as ReturnType<typeof useEntitlement>);
});

// ═══════════════════════════════════════════════════════════════════════════════
// CouponInput
// ═══════════════════════════════════════════════════════════════════════════════

describe('CouponInput', () => {
  async function renderCoupon(props: Partial<React.ComponentProps<any>> = {}) {
    const { CouponInput } = await import('@/components/billing/CouponInput');
    const onApplied = props.onApplied ?? vi.fn();
    render(<CouponInput target="subscription" onApplied={onApplied} {...props} />);
    return { onApplied: props.onApplied ?? onApplied };
  }

  it('starts collapsed and shows "Have a code?" link', async () => {
    await renderCoupon();
    expect(screen.getByRole('button', { name: /Have a code\?/i })).toBeInTheDocument();
    expect(screen.queryByPlaceholderText('Enter code')).not.toBeInTheDocument();
  });

  it('expands the input when "Have a code?" is clicked', async () => {
    const user = userEvent.setup();
    await renderCoupon();
    await user.click(screen.getByRole('button', { name: /Have a code\?/i }));
    expect(await screen.findByPlaceholderText('Enter code')).toBeInTheDocument();
  });

  it('starts expanded when initialCode is supplied', async () => {
    await renderCoupon({ initialCode: 'WELCOME' });
    expect(screen.getByDisplayValue('WELCOME')).toBeInTheDocument();
  });

  it('uppercases the code as the user types', async () => {
    const user = userEvent.setup();
    await renderCoupon({ initialCode: '' });
    await user.click(screen.getByRole('button', { name: /Have a code\?/i }));
    await user.type(screen.getByPlaceholderText('Enter code'), 'summer20');
    expect(screen.getByDisplayValue('SUMMER20')).toBeInTheDocument();
  });

  it('calls the validate API and shows success state on apply', async () => {
    const user = userEvent.setup();
    const quote = {
      coupon_id: 1,
      code: 'SAVE10',
      applies_to: 'subscription',
      original_amount_paise: 14900,
      discount_amount_paise: 1490,
      final_amount_paise: 13410,
      razorpay_offer_id: null,
      apple_offer_id: null,
      display_message: '10% off your first month',
    };
    mockApi.mockResolvedValue(quote);
    const onApplied = vi.fn();
    await renderCoupon({ onApplied });

    await user.click(screen.getByRole('button', { name: /Have a code\?/i }));
    await user.type(screen.getByPlaceholderText('Enter code'), 'SAVE10');
    await user.click(screen.getByRole('button', { name: /Apply/i }));

    await waitFor(() =>
      expect(screen.getByText('10% off your first month')).toBeInTheDocument()
    );
    expect(onApplied).toHaveBeenCalledWith(quote);
    expect(mockApi).toHaveBeenCalledWith(
      '/api/billing/coupons/validate',
      expect.objectContaining({ json: { code: 'SAVE10', target: 'subscription' } }),
    );
  });

  it('shows an error message when the code is invalid', async () => {
    const user = userEvent.setup();
    mockApi.mockRejectedValue(
      new ApiError(422, 'Invalid code', { detail: { message: 'Code expired' } }),
    );
    const onApplied = vi.fn();
    await renderCoupon({ onApplied });

    await user.click(screen.getByRole('button', { name: /Have a code\?/i }));
    await user.type(screen.getByPlaceholderText('Enter code'), 'EXPIRED');
    await user.click(screen.getByRole('button', { name: /Apply/i }));

    await waitFor(() => expect(screen.getByText('Code expired')).toBeInTheDocument());
    expect(onApplied).toHaveBeenCalledWith(null);
  });

  it('shows fallback error when no detail.message in the ApiError', async () => {
    const user = userEvent.setup();
    mockApi.mockRejectedValue(new ApiError(422, 'bad', { detail: 'Bad coupon' }));
    await renderCoupon({ initialCode: '' });

    await user.click(screen.getByRole('button', { name: /Have a code\?/i }));
    await user.type(screen.getByPlaceholderText('Enter code'), 'BAD');
    await user.click(screen.getByRole('button', { name: /Apply/i }));

    await waitFor(() => expect(screen.getByText('Bad coupon')).toBeInTheDocument());
  });

  it('clears the applied code when the remove button is clicked', async () => {
    const user = userEvent.setup();
    const quote = {
      coupon_id: 1, code: 'OFF', applies_to: 'subscription',
      original_amount_paise: 100, discount_amount_paise: 10, final_amount_paise: 90,
      razorpay_offer_id: null, apple_offer_id: null, display_message: '10% off',
    };
    mockApi.mockResolvedValue(quote);
    const onApplied = vi.fn();
    await renderCoupon({ onApplied });

    await user.click(screen.getByRole('button', { name: /Have a code\?/i }));
    await user.type(screen.getByPlaceholderText('Enter code'), 'OFF');
    await user.click(screen.getByRole('button', { name: /Apply/i }));
    await screen.findByText('10% off');

    await user.click(screen.getByLabelText('Remove code'));
    expect(screen.queryByText('10% off')).not.toBeInTheDocument();
    expect(onApplied).toHaveBeenLastCalledWith(null);
  });

  it('auto-applies initialCode when autoApply=true', async () => {
    const quote = {
      coupon_id: 2, code: 'AUTO', applies_to: 'subscription',
      original_amount_paise: 100, discount_amount_paise: 20, final_amount_paise: 80,
      razorpay_offer_id: null, apple_offer_id: null, display_message: 'Auto discount',
    };
    mockApi.mockResolvedValue(quote);
    const onApplied = vi.fn();
    await renderCoupon({ initialCode: 'AUTO', autoApply: true, onApplied });

    await waitFor(() => expect(onApplied).toHaveBeenCalledWith(quote));
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// BrainstormQuotaPill
// ═══════════════════════════════════════════════════════════════════════════════

describe('BrainstormQuotaPill', () => {
  async function renderPill(brainstorm_remaining: number | null, brainstorm_cap = 15) {
    mockUseEntitlement.mockReturnValue(
      makeEntitlement({ brainstorm_remaining, brainstorm_cap }) as ReturnType<typeof useEntitlement>,
    );
    const { BrainstormQuotaPill } = await import('@/components/billing/QuotaPill');
    render(<BrainstormQuotaPill />);
  }

  it('renders remaining / cap for a free user', async () => {
    await renderPill(10, 15);
    expect(screen.getByText(/10 \/ 15 left/i)).toBeInTheDocument();
  });

  it('shows "No brainstorms left" when remaining is 0', async () => {
    await renderPill(0);
    expect(screen.getByText(/No brainstorms left/i)).toBeInTheDocument();
  });

  it('renders nothing for Plus users (remaining === null)', async () => {
    await renderPill(null);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('calls requirePlus when the pill is clicked and quota is 0', async () => {
    const requirePlus = vi.fn().mockResolvedValue(false);
    mockUseEntitlement.mockReturnValue({
      ...makeEntitlement({ brainstorm_remaining: 0 }),
      requirePlus,
    } as ReturnType<typeof useEntitlement>);
    const { BrainstormQuotaPill } = await import('@/components/billing/QuotaPill');
    render(<BrainstormQuotaPill />);

    fireEvent.click(screen.getByRole('button'));
    expect(requirePlus).toHaveBeenCalledWith('brainstorm_quota');
  });

  it('uses a danger palette when remaining is 0', async () => {
    await renderPill(0);
    const pill = screen.getByRole('button');
    expect(pill.className).toContain('rose');
  });

  it('uses a warn palette when remaining <= 3', async () => {
    await renderPill(2);
    const pill = screen.getByRole('button');
    expect(pill.className).toContain('amber');
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// PlusBanner variants
// ═══════════════════════════════════════════════════════════════════════════════

describe('PastDueBanner', () => {
  it('renders the alert for past_due status', async () => {
    mockUseEntitlement.mockReturnValue(
      makeEntitlement({ status: 'past_due' }) as ReturnType<typeof useEntitlement>,
    );
    const { PastDueBanner } = await import('@/components/billing/PlusBanner');
    render(<PastDueBanner />);
    expect(screen.getByRole('alert')).toHaveTextContent(/Update your payment/i);
  });

  it('renders nothing when status is not past_due', async () => {
    mockUseEntitlement.mockReturnValue(
      makeEntitlement({ status: 'active' }) as ReturnType<typeof useEntitlement>,
    );
    const { PastDueBanner } = await import('@/components/billing/PlusBanner');
    const { container } = render(<PastDueBanner />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('FreeUsageStrip', () => {
  it('renders usage counts for a confirmed free user', async () => {
    const { FreeUsageStrip } = await import('@/components/billing/PlusBanner');
    render(<FreeUsageStrip />);
    // Component shows "used / cap" — brainstorm_used = bsCap - bsRemaining = 15-10 = 5
    expect(screen.getByText(/5 \/ 15/i)).toBeInTheDocument();
  });

  it('renders nothing for a Plus user (tier !== free)', async () => {
    mockUseEntitlement.mockReturnValue(
      makeEntitlement({ tier: 'plus' }) as ReturnType<typeof useEntitlement>,
    );
    const { FreeUsageStrip } = await import('@/components/billing/PlusBanner');
    const { container } = render(<FreeUsageStrip />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when entitlement is not yet confirmed', async () => {
    mockUseEntitlement.mockReturnValue({
      ...makeEntitlement(),
      isConfirmed: false,
    } as ReturnType<typeof useEntitlement>);
    const { FreeUsageStrip } = await import('@/components/billing/PlusBanner');
    const { container } = render(<FreeUsageStrip />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('OneTimeExpiryBanner', () => {
  it('renders within 5 days of expiry for one_time users', async () => {
    const twoDaysFromNow = new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString();
    mockUseEntitlement.mockReturnValue(
      makeEntitlement({ status: 'one_time', period_end: twoDaysFromNow }) as ReturnType<typeof useEntitlement>,
    );
    const { OneTimeExpiryBanner } = await import('@/components/billing/PlusBanner');
    render(<OneTimeExpiryBanner />);
    expect(screen.getByRole('status')).toHaveTextContent(/2 day/i);
  });

  it('renders nothing when more than 5 days remain', async () => {
    const tenDaysFromNow = new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString();
    mockUseEntitlement.mockReturnValue(
      makeEntitlement({ status: 'one_time', period_end: tenDaysFromNow }) as ReturnType<typeof useEntitlement>,
    );
    const { OneTimeExpiryBanner } = await import('@/components/billing/PlusBanner');
    const { container } = render(<OneTimeExpiryBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing for non one_time users', async () => {
    mockUseEntitlement.mockReturnValue(
      makeEntitlement({ status: 'active' }) as ReturnType<typeof useEntitlement>,
    );
    const { OneTimeExpiryBanner } = await import('@/components/billing/PlusBanner');
    const { container } = render(<OneTimeExpiryBanner />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('ReEngagementBanner', () => {
  beforeEach(() => {
    localStorage.removeItem('plus_reengagement_open_count');
    localStorage.removeItem('plus_reengagement_dismissed');
  });

  it('is hidden on the first two opens (count < 3)', async () => {
    localStorage.setItem('plus_reengagement_open_count', '1');
    const { ReEngagementBanner } = await import('@/components/billing/PlusBanner');
    const { container } = render(<ReEngagementBanner tripCount={2} />);
    // Banner only becomes visible after count reaches 3 via useEffect
    expect(container.querySelector('[data-testid]') || container.firstChild).toBeFalsy();
  });

  it('becomes visible on the 3rd open for a confirmed free user with trips', async () => {
    localStorage.setItem('plus_reengagement_open_count', '2'); // will be incremented to 3
    const { ReEngagementBanner } = await import('@/components/billing/PlusBanner');
    render(<ReEngagementBanner tripCount={3} />);
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Try Plus/i })).toBeInTheDocument()
    );
  });

  it('stays hidden when the user has no trips', async () => {
    localStorage.setItem('plus_reengagement_open_count', '2');
    const { ReEngagementBanner } = await import('@/components/billing/PlusBanner');
    const { container } = render(<ReEngagementBanner tripCount={0} />);
    // tripCount < 1 → never sets visible
    expect(screen.queryByRole('button', { name: /Try Plus/i })).not.toBeInTheDocument();
  });

  it('dismisses the banner and sets localStorage flag', async () => {
    const user = userEvent.setup();
    localStorage.setItem('plus_reengagement_open_count', '2');
    const { ReEngagementBanner } = await import('@/components/billing/PlusBanner');
    render(<ReEngagementBanner tripCount={1} />);

    await waitFor(() => screen.getByLabelText('Dismiss'));
    await user.click(screen.getByLabelText('Dismiss'));

    expect(screen.queryByRole('button', { name: /Try Plus/i })).not.toBeInTheDocument();
    expect(localStorage.getItem('plus_reengagement_dismissed')).toBe('1');
  });
});
