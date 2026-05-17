'use client';

/**
 * Top-of-page banners driven by the entitlement state:
 *
 *   - <PastDueBanner />       — rose, when status === "past_due"
 *   - <ReEngagementBanner />  — indigo nudge, 3rd dashboard load for free
 *   - <FreeUsageStrip />      — compact usage strip for free users
 *   - <OneTimeExpiryBanner /> — amber, days 25–30 of an active one-time plan
 *
 * Each is self-contained: it reads entitlement from context, decides whether
 * to render, and renders nothing otherwise.
 */
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, ArrowRight, Clock3, Sparkles, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motionTokens } from '@/lib/motion';
import { useEntitlement } from '@/hooks/useEntitlement';


export function PastDueBanner() {
  const { entitlement } = useEntitlement();
  if (entitlement.status !== 'past_due') return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: motionTokens.ease.out }}
      role="alert"
      className="flex items-center gap-3 px-4 py-2.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-700"
    >
      <AlertTriangle className="w-4 h-4 shrink-0" />
      <div className="text-xs font-bold leading-snug flex-1">
        We couldn&apos;t renew your Roammate Plus subscription. Update your payment to keep Plus active.
      </div>
      <Link
        href="/profile/subscription"
        className="text-[11px] font-black px-3 py-1.5 bg-rose-600 text-white rounded-full hover:bg-rose-700 transition-colors whitespace-nowrap"
      >
        Update payment
      </Link>
    </motion.div>
  );
}


/**
 * Shown the 3rd time a free user opens the dashboard (and they've created at
 * least one trip — otherwise we don't have permission to push for an upgrade
 * yet). Dismissible. Counter and dismissal state both live in localStorage.
 */
export function ReEngagementBanner({ tripCount }: { tripCount: number }) {
  const { entitlement, requirePlus } = useEntitlement();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (entitlement.tier !== 'free') return;
    if (tripCount < 1) return;
    if (typeof window === 'undefined') return;
    const KEY_COUNT = 'plus_reengagement_open_count';
    const KEY_DISMISSED = 'plus_reengagement_dismissed';
    if (localStorage.getItem(KEY_DISMISSED)) return;
    const count = Number(localStorage.getItem(KEY_COUNT) || '0') + 1;
    localStorage.setItem(KEY_COUNT, String(count));
    if (count >= 3) setVisible(true);
  }, [entitlement.tier, tripCount]);

  const dismiss = () => {
    localStorage.setItem('plus_reengagement_dismissed', '1');
    setVisible(false);
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.22, ease: motionTokens.ease.out }}
          className="flex items-center gap-3 px-4 py-2.5 rounded-xl border"
          style={{
            backgroundImage: 'linear-gradient(135deg, #EEF2FF 0%, #FAE8FF 55%, #FEF3C7 100%)',
            borderColor: 'rgba(79, 70, 229, 0.18)',
          }}
        >
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
            style={{
              backgroundImage: 'linear-gradient(135deg, #4F46E5 0%, #D946EF 55%, #F59E0B 100%)',
            }}
          >
            <Sparkles className="w-3.5 h-3.5 text-white" />
          </div>
          <div className="text-xs font-bold leading-snug flex-1 text-slate-700">
            You&apos;ve planned {tripCount} trip{tripCount === 1 ? '' : 's'} — ready to unlock the concierge?
          </div>
          <button
            type="button"
            onClick={() => requirePlus('concierge')}
            className="inline-flex items-center gap-1 text-[11px] font-black px-3 py-1.5 bg-indigo-600 text-white rounded-full hover:bg-indigo-700 transition-colors whitespace-nowrap"
          >
            Try Plus
            <ArrowRight className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={dismiss}
            aria-label="Dismiss"
            className="w-7 h-7 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-white/40 transition-colors shrink-0"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}


/**
 * Amber expiry warning shown to one-time Plus users in the final 5 days of
 * their 30-day window. Routes to the subscription page where they can
 * "Switch to monthly". Self-hides outside the window and for non-one_time
 * users.
 */
export function OneTimeExpiryBanner() {
  const { entitlement } = useEntitlement();
  if (entitlement.status !== 'one_time') return null;
  if (!entitlement.period_end) return null;
  const end = new Date(entitlement.period_end).getTime();
  const days = Math.max(0, Math.ceil((end - Date.now()) / (24 * 60 * 60 * 1000)));
  if (days > 5) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: motionTokens.ease.out }}
      className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-amber-200 bg-amber-50 text-amber-800"
      role="status"
    >
      <Clock3 className="w-4 h-4 shrink-0" />
      <div className="text-xs font-bold leading-snug flex-1">
        {days === 0
          ? "Your Plus access ends today — switch to monthly to keep going."
          : `Your Plus access ends in ${days} day${days === 1 ? '' : 's'} — switch to monthly for ₹149/mo.`}
      </div>
      <Link
        href="/profile/subscription"
        className="text-[11px] font-black px-3 py-1.5 bg-amber-600 text-white rounded-full hover:bg-amber-700 transition-colors whitespace-nowrap"
      >
        Switch to monthly
      </Link>
    </motion.div>
  );
}


/**
 * Compact "X / 15 brainstorms · Y / 2 active trips" usage strip for free
 * users. Hides entirely for Plus.
 */
export function FreeUsageStrip() {
  const { entitlement, requirePlus } = useEntitlement();
  if (entitlement.tier !== 'free') return null;
  const bsLeft = entitlement.brainstorm_remaining ?? 0;
  const bsCap = entitlement.brainstorm_cap ?? 15;
  const tripCap = entitlement.active_trip_cap ?? 2;
  const tripsUsed = entitlement.active_trip_count;

  const bsTone =
    bsLeft === 0 ? 'text-rose-600'
    : bsLeft <= 3 ? 'text-amber-600'
    : 'text-slate-500';
  const tripsTone =
    tripsUsed >= tripCap ? 'text-amber-600'
    : 'text-slate-500';

  return (
    <button
      type="button"
      onClick={() => requirePlus('concierge')}
      className="group flex items-center gap-4 w-full px-4 py-2.5 rounded-xl bg-white border border-slate-100 hover:border-indigo-200 hover:shadow-sm transition-all text-left"
    >
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
        style={{
          backgroundImage: 'linear-gradient(135deg, #4F46E5 0%, #D946EF 55%, #F59E0B 100%)',
        }}
      >
        <Sparkles className="w-3.5 h-3.5 text-white" />
      </div>
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className="flex flex-col">
          <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">Brainstorms</span>
          <span className={`text-sm font-black tabular-nums ${bsTone}`}>
            {Math.max(bsCap - bsLeft, 0)} / {bsCap}
          </span>
        </div>
        <div className="w-px h-7 bg-slate-100" />
        <div className="flex flex-col">
          <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">Active trips</span>
          <span className={`text-sm font-black tabular-nums ${tripsTone}`}>
            {tripsUsed} / {tripCap}
          </span>
        </div>
      </div>
      <span className="text-[11px] font-black uppercase tracking-wider text-indigo-600 group-hover:translate-x-0.5 transition-transform whitespace-nowrap">
        Upgrade →
      </span>
    </button>
  );
}
