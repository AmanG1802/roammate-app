'use client';

/**
 * The contextual paywall modal. Rendered once at the root via PaywallProvider;
 * components trigger it via `useEntitlement().requirePlus(feature)`.
 *
 * v1.1 adds:
 *   - Plan toggle: Monthly (recurring) vs One-time (₹200 / 30 days, hard-expire)
 *   - "Have a code?" coupon input — re-quotes when plan toggles
 *   - Three subscribe paths:
 *       (a) Monthly subscription via Razorpay (with optional offer_id from coupon)
 *       (b) One-time Razorpay Order (₹200, or discounted)
 *       (c) Backend free grant when coupon zeroes the price (EARLYACCESS)
 *
 * On any Maybe-later / close, resolves false.
 */

import { AnimatePresence, motion } from 'framer-motion';
import {
  CalendarClock, Infinity as InfinityIcon, MapPinned, Sparkles, X, Check,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { getToken } from '@/lib/auth';
import { motionTokens, useAppMotion } from '@/lib/motion';
import { PlusCrest, PlusWordmark } from './PlusCrest';
import { CouponInput, type CouponQuote } from './CouponInput';
import { PlanToggle, type PlanChoice } from './PlanToggle';
import type { PaywallFeature } from '@/hooks/useEntitlement';
import { useEntitlement } from '@/hooks/useEntitlement';

const API = process.env.NEXT_PUBLIC_API_URL ?? '';

interface FeatureCopy {
  title: string;
  subtext: string;
  Icon: typeof Sparkles;
}

const COPY: Record<PaywallFeature, FeatureCopy> = {
  concierge: {
    title: 'Meet your trip concierge',
    subtext: 'Always-on AI travel companion — included with Plus.',
    Icon: InfinityIcon,
  },
  brainstorm_quota: {
    title: "You've used 15 brainstorms this month",
    subtext: 'Go unlimited with Plus, or wait until next month.',
    Icon: Sparkles,
  },
  active_trips: {
    title: "You're planning 2 trips already",
    subtext: 'Plus lifts the cap so you can dream as wide as you travel.',
    Icon: CalendarClock,
  },
  offline_maps: {
    title: 'Take your maps off-grid',
    subtext: 'Offline tiles + saved pins for when signal disappears.',
    Icon: MapPinned,
  },
};


// ── Razorpay Checkout JS — loaded lazily on first use ─────────────────────────

let razorpayScriptPromise: Promise<void> | null = null;
function loadRazorpay(): Promise<void> {
  if (typeof window === 'undefined') return Promise.resolve();
  if ((window as any).Razorpay) return Promise.resolve();
  if (razorpayScriptPromise) return razorpayScriptPromise;
  razorpayScriptPromise = new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = 'https://checkout.razorpay.com/v1/checkout.js';
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('Failed to load Razorpay Checkout'));
    document.body.appendChild(s);
  });
  return razorpayScriptPromise;
}


// ── Confetti burst — 24 colored capsules, spring-animated outward ──────────

function ConfettiBurst() {
  const { reduce } = useAppMotion();
  if (reduce) return null;
  const colors = ['#4F46E5', '#D946EF', '#F59E0B'];
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {Array.from({ length: 24 }).map((_, i) => {
        const angle = (i / 24) * Math.PI * 2;
        const dist = 140 + Math.random() * 80;
        const x = Math.cos(angle) * dist;
        const y = Math.sin(angle) * dist - 40; // bias upward
        return (
          <motion.span
            key={i}
            className="absolute left-1/2 top-1/2 block rounded-full"
            style={{
              width: 6, height: 12,
              backgroundColor: colors[i % colors.length],
              translateX: '-50%', translateY: '-50%',
            }}
            initial={{ x: 0, y: 0, opacity: 1, rotate: 0, scale: 0.6 }}
            animate={{ x, y, opacity: 0, rotate: 180 + Math.random() * 360, scale: 1 }}
            transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: i * 0.012 }}
          />
        );
      })}
    </div>
  );
}


function readPromoFromUrl(): string | undefined {
  if (typeof window === 'undefined') return undefined;
  const params = new URLSearchParams(window.location.search);
  const promo = params.get('promo');
  return promo ? promo.toUpperCase() : undefined;
}


export function PaywallModal() {
  const { pendingPaywall, resolvePaywall, entitlement } = useEntitlement();
  const { reduce } = useAppMotion();
  const [phase, setPhase] = useState<'idle' | 'submitting' | 'success'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<PlanChoice>('monthly');
  const [coupon, setCoupon] = useState<CouponQuote | null>(null);
  const initialPromo = useMemo(() => readPromoFromUrl(), []);

  const open = pendingPaywall !== null;
  const feature = pendingPaywall?.feature ?? 'concierge';
  const preferredPlan = pendingPaywall?.plan ?? 'monthly';
  const copy = COPY[feature];

  // Reset everything when the modal closes & re-opens.
  useEffect(() => {
    if (!open) {
      const t = setTimeout(() => {
        setPhase('idle');
        setError(null);
        setCoupon(null);
        setPlan('monthly');
      }, 200);
      return () => clearTimeout(t);
    }
    // Seed plan from the requester's preference whenever the modal opens.
    setPlan(preferredPlan);
  }, [open, preferredPlan]);

  const close = useCallback((subscribed: boolean) => {
    resolvePaywall(subscribed);
  }, [resolvePaywall]);

  // ── Subscription path (monthly) ────────────────────────────────────────────
  const startSubscription = useCallback(async () => {
    setError(null);
    setPhase('submitting');
    try {
      const token = getToken();
      if (!token) {
        setError('Please sign in to subscribe.');
        setPhase('idle');
        return;
      }
      const res = await fetch(`${API}/billing/razorpay/subscription`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ coupon_code: coupon?.code ?? null }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: 'Could not start subscription' }));
        const msg = typeof body.detail === 'string'
          ? body.detail
          : body.detail?.message ?? 'Could not start subscription';
        setError(msg);
        setPhase('idle');
        return;
      }
      const data = await res.json() as {
        subscription_id: string;
        razorpay_key_id: string;
        user: { email: string; name: string | null };
      };

      await loadRazorpay();
      const Razorpay = (window as any).Razorpay;
      if (!Razorpay) {
        setError('Could not load Razorpay Checkout.');
        setPhase('idle');
        return;
      }
      const rzp = new Razorpay({
        key: data.razorpay_key_id,
        subscription_id: data.subscription_id,
        name: 'Roammate Plus',
        description: coupon
          ? `Monthly · first cycle ${coupon.display_message}`
          : `Monthly · ₹${entitlement.price_inr} · cancel anytime`,
        prefill: { email: data.user.email, name: data.user.name ?? '' },
        theme: { color: '#4F46E5' },
        handler: () => {
          setPhase('success');
          setTimeout(() => { close(true); }, 2400);
        },
        modal: { ondismiss: () => setPhase('idle') },
      });
      rzp.on?.('payment.failed', (resp: any) => {
        setError(resp?.error?.description || 'Payment failed. Please try again.');
        setPhase('idle');
      });
      rzp.open();
    } catch (e) {
      setError((e as Error).message || 'Something went wrong.');
      setPhase('idle');
    }
  }, [close, coupon, entitlement.price_inr]);

  // ── One-time path (₹200 / 30 days, or free if EARLYACCESS) ────────────────
  const startOneTime = useCallback(async () => {
    setError(null);
    setPhase('submitting');
    try {
      const token = getToken();
      if (!token) {
        setError('Please sign in to purchase.');
        setPhase('idle');
        return;
      }
      const res = await fetch(`${API}/billing/razorpay/one-time`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ coupon_code: coupon?.code ?? null }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: 'Could not start purchase' }));
        const msg = typeof body.detail === 'string'
          ? body.detail
          : body.detail?.message ?? 'Could not start purchase';
        setError(msg);
        setPhase('idle');
        return;
      }
      const data = await res.json() as
        | { granted: true; period_end: string }
        | {
            granted: false;
            order_id: string;
            amount_paise: number;
            razorpay_key_id: string;
            user: { email: string; name: string | null };
            coupon: CouponQuote | null;
          };

      // Free-grant path
      if (data.granted) {
        setPhase('success');
        setTimeout(() => { close(true); }, 2400);
        return;
      }

      // Paid path — open Razorpay in Order mode
      await loadRazorpay();
      const Razorpay = (window as any).Razorpay;
      if (!Razorpay) {
        setError('Could not load Razorpay Checkout.');
        setPhase('idle');
        return;
      }
      const rzp = new Razorpay({
        key: data.razorpay_key_id,
        order_id: data.order_id,
        amount: data.amount_paise,
        currency: 'INR',
        name: 'Roammate Plus',
        description: `One-time · 30 days · ₹${Math.round(data.amount_paise / 100)}`,
        prefill: { email: data.user.email, name: data.user.name ?? '' },
        theme: { color: '#4F46E5' },
        handler: async (resp: any) => {
          // Verify on backend before celebrating
          try {
            const vres = await fetch(`${API}/billing/razorpay/one-time/verify`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({
                order_id: resp.razorpay_order_id,
                payment_id: resp.razorpay_payment_id,
                signature: resp.razorpay_signature,
                coupon_id: coupon?.coupon_id ?? null,
              }),
            });
            if (!vres.ok) {
              const b = await vres.json().catch(() => ({}));
              setError(b.detail?.message || b.detail || 'Could not verify payment.');
              setPhase('idle');
              return;
            }
            setPhase('success');
            setTimeout(() => { close(true); }, 2400);
          } catch {
            setError('Could not verify payment.');
            setPhase('idle');
          }
        },
        modal: { ondismiss: () => setPhase('idle') },
      });
      rzp.on?.('payment.failed', (resp: any) => {
        setError(resp?.error?.description || 'Payment failed. Please try again.');
        setPhase('idle');
      });
      rzp.open();
    } catch (e) {
      setError((e as Error).message || 'Something went wrong.');
      setPhase('idle');
    }
  }, [close, coupon]);

  const startCheckout = plan === 'monthly' ? startSubscription : startOneTime;

  // ── Computed display amounts ──────────────────────────────────────────────
  const baseAmount = plan === 'monthly' ? entitlement.price_inr : entitlement.onetime_price_inr;
  const showFinal = coupon && (
    plan === 'monthly'
      ? coupon.applies_to === 'subscription_first_cycle' || coupon.applies_to === 'any'
      : coupon.applies_to === 'one_time' || coupon.applies_to === 'any'
  );
  const finalRupees = showFinal && coupon ? Math.round(coupon.final_amount_paise / 100) : baseAmount;
  const isFreeGrant = showFinal && coupon && coupon.final_amount_paise === 0;

  const ctaLabel = (() => {
    if (phase === 'submitting') return 'Opening checkout…';
    if (isFreeGrant) return 'Claim 30 free days';
    if (plan === 'monthly') {
      return showFinal
        ? `Start at ₹${finalRupees}, then ₹${entitlement.price_inr}/mo`
        : `Subscribe for ₹${entitlement.price_inr}/mo`;
    }
    return showFinal ? `Pay ₹${finalRupees} · 30 days` : `Pay ₹${entitlement.onetime_price_inr} · 30 days`;
  })();

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="paywall-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2, ease: motionTokens.ease.out }}
          className="fixed inset-0 z-[100] bg-slate-900/40 backdrop-blur-[2px] flex items-end sm:items-center justify-center p-0 sm:p-4"
          onClick={() => close(false)}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            initial={{ opacity: 0, y: reduce ? 0 : 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: reduce ? 0 : 12 }}
            transition={{ duration: 0.26, ease: motionTokens.ease.out }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full sm:max-w-md bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden"
            style={{
              boxShadow: '0 24px 80px -24px rgba(15, 23, 42, 0.35), 0 0 0 1px rgba(79, 70, 229, 0.08)',
            }}
          >
            {phase === 'success' && <ConfettiBurst />}

            <button
              type="button"
              onClick={() => close(false)}
              aria-label="Close"
              className="absolute top-4 right-4 w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors z-10"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="px-6 sm:px-8 pt-8 pb-6">
              {phase !== 'success' ? (
                <>
                  <PlusCrest size={64} className="mb-5" />
                  <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight mb-1.5">
                    {copy.title}
                  </h2>
                  <p className="text-[15px] text-slate-500 leading-snug mb-5">
                    {copy.subtext}
                  </p>

                  <div className="mb-5">
                    <PlanToggle
                      value={plan}
                      monthlyPrice={entitlement.price_inr}
                      oneTimePrice={entitlement.onetime_price_inr}
                      oneTimeDays={entitlement.onetime_duration_days}
                      onChange={setPlan}
                    />
                  </div>

                  <div className="space-y-2 mb-5">
                    <PaywallBullet text="Unlimited AI concierge & brainstorms" />
                    <PaywallBullet text="Offline maps & pins for the road" />
                    <PaywallBullet text="Plan as many trips as you want" />
                  </div>

                  <div className="bg-slate-50 rounded-2xl px-5 py-4 mb-4 border border-slate-100 flex items-baseline gap-2 flex-wrap">
                    {showFinal && coupon && coupon.discount_amount_paise > 0 && !isFreeGrant && (
                      <span className="text-base font-bold text-slate-400 line-through tracking-tight">
                        ₹{baseAmount}
                      </span>
                    )}
                    <span className={`text-2xl font-black tracking-tight ${isFreeGrant ? 'text-emerald-600' : 'text-slate-900'}`}>
                      {isFreeGrant ? 'Free' : `₹${finalRupees}`}
                    </span>
                    <span className="text-sm text-slate-500 font-semibold">
                      {plan === 'monthly' ? '/ month' : '/ 30 days'}
                    </span>
                    <span className="ml-auto text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      {plan === 'monthly' ? 'Auto-renews · cancel anytime' : 'One charge · no renewal'}
                    </span>
                  </div>

                  <div className="mb-5">
                    <CouponInput
                      target={plan === 'monthly' ? 'subscription' : 'one_time'}
                      initialCode={initialPromo}
                      autoApply={Boolean(initialPromo)}
                      onApplied={setCoupon}
                    />
                  </div>

                  {error && (
                    <p className="text-xs font-semibold text-rose-600 mb-3" role="alert">{error}</p>
                  )}

                  <div className="flex flex-col gap-2">
                    <button
                      type="button"
                      onClick={startCheckout}
                      disabled={phase === 'submitting'}
                      className="w-full rounded-full bg-indigo-600 text-white font-bold text-[15px] py-3 px-6 transition-all hover:bg-indigo-700 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
                      style={{ boxShadow: '0 8px 24px -8px rgba(79, 70, 229, 0.55)' }}
                    >
                      {ctaLabel}
                    </button>
                    <button
                      type="button"
                      onClick={() => close(false)}
                      className="w-full rounded-full text-slate-500 hover:text-slate-700 font-semibold text-sm py-2 transition-colors"
                    >
                      Maybe later
                    </button>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center text-center py-6">
                  <PlusCrest size={72} className="mb-5" />
                  <h2 className="text-2xl font-black text-slate-900 tracking-tight mb-1.5">
                    Welcome to <PlusWordmark className="text-2xl" />
                  </h2>
                  <p className="text-[15px] text-slate-500 mb-2">
                    Everything just unlocked.
                  </p>
                  <p className="text-xs text-slate-400">Returning you to where you were…</p>
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}


function PaywallBullet({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2.5 text-sm text-slate-700">
      <div className="w-5 h-5 rounded-full bg-indigo-50 flex items-center justify-center shrink-0">
        <Check className="w-3 h-3 text-indigo-600" strokeWidth={3} />
      </div>
      <span>{text}</span>
    </div>
  );
}
