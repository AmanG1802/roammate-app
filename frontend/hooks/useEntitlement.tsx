'use client';

/**
 * Roammate Plus entitlement client.
 *
 * Single React context that:
 *   - hydrates `/billing/status` on mount and after every successful purchase
 *   - exposes `tier`, `brainstormRemaining`, `canUseConcierge`, etc.
 *   - `requirePlus(feature)` opens the paywall modal and resolves when the
 *     user either subscribes (true) or dismisses (false)
 *
 * The PaywallModal itself listens via this context — the provider hands it
 * `feature` + `resolve()`. Components never import the modal directly.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from '@/lib/api';

export type PaywallFeature =
  | 'concierge'
  | 'brainstorm_quota'
  | 'active_trips'
  | 'offline_maps';

export interface Entitlement {
  tier: 'free' | 'plus';
  status: 'none' | 'active' | 'past_due' | 'canceled' | 'expired' | 'pending' | 'one_time';
  period_end: string | null;
  can_create_active_trip: boolean;
  can_use_concierge: boolean;
  can_use_offline_maps: boolean;
  brainstorm_remaining: number | null;
  active_trip_count: number;
  active_trip_cap: number | null;
  brainstorm_used: number;
  brainstorm_cap: number | null;
  price_inr: number;
  onetime_price_inr: number;
  onetime_duration_days: number;
}

const FREE_DEFAULT: Entitlement = {
  tier: 'free',
  status: 'none',
  period_end: null,
  can_create_active_trip: true,
  can_use_concierge: false,
  can_use_offline_maps: false,
  brainstorm_remaining: 15,
  active_trip_count: 0,
  active_trip_cap: 2,
  brainstorm_used: 0,
  brainstorm_cap: 15,
  price_inr: 149,
  onetime_price_inr: 200,
  onetime_duration_days: 30,
};

export type PaywallPlan = 'monthly' | 'one_time';

export interface PaywallOptions {
  /** Pre-select this plan when the paywall opens. Defaults to "monthly". */
  plan?: PaywallPlan;
}

interface PaywallRequest {
  feature: PaywallFeature;
  plan: PaywallPlan;
  resolve: (subscribed: boolean) => void;
}

interface EntitlementContextValue {
  entitlement: Entitlement;
  isLoading: boolean;
  /**
   * True only once a `/billing/status` fetch has succeeded at least once.
   * Until then `entitlement` is the optimistic free-tier placeholder, NOT a
   * confirmed fact — so upsell UI (banners, the onboarding pitch) must gate on
   * this to avoid pitching Plus to a paying user whose status hasn't loaded or
   * whose fetch failed. Stays true after the first success (we keep the last
   * known value across later transient failures rather than reverting to free).
   */
  isConfirmed: boolean;
  refresh: () => Promise<void>;
  requirePlus: (feature: PaywallFeature, opts?: PaywallOptions) => Promise<boolean>;
  /** Internal use by PaywallModal — current pending paywall request. */
  pendingPaywall: PaywallRequest | null;
  /** Internal use by PaywallModal — resolve the current request. */
  resolvePaywall: (subscribed: boolean) => void;
}

const EntitlementContext = createContext<EntitlementContextValue | null>(null);

async function fetchStatus(): Promise<Entitlement | null> {
  // Go through the cookie-aware client so we inherit the one-shot 401 →
  // /auth/refresh → retry behaviour. A raw fetch here would be the only call
  // in the app that gives up on an expired access cookie, silently leaving the
  // user on the free-tier default.
  try {
    return await api<Entitlement>('/api/billing/status');
  } catch {
    return null;
  }
}


export function EntitlementProvider({ children }: { children: ReactNode }) {
  const [entitlement, setEntitlement] = useState<Entitlement>(FREE_DEFAULT);
  const [isLoading, setIsLoading] = useState(true);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [pendingPaywall, setPendingPaywall] = useState<PaywallRequest | null>(null);

  const refresh = useCallback(async () => {
    const s = await fetchStatus();
    if (s) {
      setEntitlement(s);
      setIsConfirmed(true);
    }
    // Note: a failed fetch deliberately does NOT flip isConfirmed. We keep the
    // last known entitlement (or the free placeholder on first load) but never
    // treat an unconfirmed/errored state as "confirmed free" for upsell gating.
    setIsLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    // Re-check entitlement on tab focus so cancellations/upgrades made in
    // another window propagate quickly.
    const onFocus = () => { refresh(); };
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [refresh]);

  const requirePlus = useCallback((feature: PaywallFeature, opts?: PaywallOptions) => {
    return new Promise<boolean>((resolve) => {
      setPendingPaywall({ feature, plan: opts?.plan ?? 'monthly', resolve });
    });
  }, []);

  const resolvePaywall = useCallback((subscribed: boolean) => {
    setPendingPaywall((curr) => {
      curr?.resolve(subscribed);
      return null;
    });
    if (subscribed) {
      // Backend webhook may take a beat; poll a few times.
      void (async () => {
        for (let i = 0; i < 5; i++) {
          await new Promise((r) => setTimeout(r, 1200));
          const s = await fetchStatus();
          if (s && s.tier === 'plus') {
            setEntitlement(s);
            setIsConfirmed(true);
            return;
          }
        }
        await refresh();
      })();
    }
  }, [refresh]);

  const value = useMemo<EntitlementContextValue>(() => ({
    entitlement,
    isLoading,
    isConfirmed,
    refresh,
    requirePlus,
    pendingPaywall,
    resolvePaywall,
  }), [entitlement, isLoading, isConfirmed, refresh, requirePlus, pendingPaywall, resolvePaywall]);

  return (
    <EntitlementContext.Provider value={value}>
      {children}
    </EntitlementContext.Provider>
  );
}


export function useEntitlement(): EntitlementContextValue {
  const ctx = useContext(EntitlementContext);
  if (!ctx) {
    // Render-time fallback so components don't crash outside the provider
    // (e.g. in the marketing /pricing page when signed out). All gates default
    // to "free" with caps; requirePlus becomes a no-op that resolves false.
    return {
      entitlement: FREE_DEFAULT,
      isLoading: false,
      // Outside the provider we can't confirm anything — never claim "confirmed
      // free" so upsell surfaces stay suppressed.
      isConfirmed: false,
      refresh: async () => {},
      requirePlus: async () => false,
      pendingPaywall: null,
      resolvePaywall: () => {},
    };
  }
  return ctx;
}


/**
 * Convenience helper for fetch wrappers: pass a Response; if it's a 402 with
 * a `needs_plus` payload, opens the paywall and returns true (caller should
 * abort). Otherwise returns false. Use inside React components only.
 */
export function isNeedsPlus(body: unknown): { feature: PaywallFeature } | null {
  if (!body || typeof body !== 'object') return null;
  const detail = (body as { detail?: unknown }).detail;
  if (!detail || typeof detail !== 'object') return null;
  const d = detail as { code?: string; feature?: string };
  if (d.code !== 'needs_plus' || !d.feature) return null;
  return { feature: d.feature as PaywallFeature };
}
