'use client';

/**
 * Roammate Plus subscription page. Two states keyed off `entitlement.tier`:
 *   - Free  → upsell hero + tier comparison + FAQ
 *   - Plus  → status banner + usage card + manage (cancel)
 *
 * Subscribing uses the same paywall flow as the contextual modal — we just
 * call requirePlus('concierge') as a generic surface; the modal copy is
 * always relevant since the user is sitting on the subscription page.
 */
import { motion } from 'framer-motion';
import {
  Check, CheckCircle2, ChevronDown, Crown, Loader2, ShieldCheck,
} from 'lucide-react';
import { useState } from 'react';
import { api } from '@/lib/api';
import { motionTokens, useAppMotion } from '@/lib/motion';
import { PlusCrest, PlusWordmark } from '@/components/billing/PlusCrest';
import { TierComparison } from '@/components/billing/TierComparison';
import { useEntitlement } from '@/hooks/useEntitlement';

const FAQ_ITEMS = [
  {
    q: 'Can I cancel anytime?',
    a: 'Yes. Your Plus features remain active until the end of your current billing period, then your account reverts to the free tier.',
  },
  {
    q: 'Which payment methods are supported?',
    a: 'UPI (PhonePe, Google Pay, BHIM, Paytm, etc.) and Indian credit / debit cards. We use Razorpay for secure recurring billing with e-mandate auto-debit.',
  },
  {
    q: 'What happens if my payment fails?',
    a: "We'll retry over the next few days. During that time you keep Plus access. If we still can't charge, your account moves back to the free tier and you can re-subscribe anytime.",
  },
  {
    q: 'Do I keep my trips if I cancel?',
    a: "All your trips, ideas, and history are yours. After cancellation, active trips beyond the free limit (2) become read-only — you'll just need to archive a trip to plan a new one.",
  },
];


export default function SubscriptionPage() {
  const { entitlement, isLoading, requirePlus } = useEntitlement();
  const { reduce } = useAppMotion();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-7 h-7 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-black text-slate-900 tracking-tight mb-1">Subscription</h1>
      <p className="text-sm text-slate-500 mb-6">
        {entitlement.tier === 'plus'
          ? "You're on Roammate Plus — thanks for supporting us."
          : 'Free today. Upgrade anytime — no card needed to start.'}
      </p>

      {entitlement.tier === 'plus'
        ? <PlusState requirePlus={requirePlus} />
        : <FreeState requirePlus={requirePlus} />
      }

      {entitlement.tier === 'free' && (
        <motion.section
          initial={reduce ? undefined : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.32, ease: motionTokens.ease.out, delay: 0.1 }}
          className="mt-8"
        >
          <h2 className="text-sm font-black uppercase tracking-wider text-slate-400 mb-3 px-1">
            Frequently asked
          </h2>
          <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
            {FAQ_ITEMS.map((item, i) => (
              <FaqRow key={item.q} q={item.q} a={item.a} last={i === FAQ_ITEMS.length - 1} />
            ))}
          </div>
        </motion.section>
      )}
    </div>
  );
}


// ── Free state ──────────────────────────────────────────────────────────────

function FreeState({ requirePlus }: {
  requirePlus: (f: 'concierge', opts?: { plan?: 'monthly' | 'one_time' }) => Promise<boolean>;
}) {
  const { reduce } = useAppMotion();
  const { entitlement } = useEntitlement();
  return (
    <>
      {/* Hero header */}
      <motion.div
        initial={reduce ? undefined : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.32, ease: motionTokens.ease.out }}
        className="flex flex-col sm:flex-row sm:items-center gap-5 mb-5"
      >
        <PlusCrest size={64} />
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl font-black tracking-tight mb-1">
            <PlusWordmark className="text-2xl" />
          </h2>
          <p className="text-sm text-slate-500 leading-snug">
            Unlimited AI concierge. Offline maps. Built for travelers who
            actually go places.
          </p>
        </div>
      </motion.div>

      {/* Plan cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
        <PlanCard
          tone="primary"
          delay={reduce ? 0 : 0.05}
          badge="RECOMMENDED"
          name="Monthly"
          price={`₹${entitlement.price_inr}`}
          unit="/ month"
          subline="Auto-renews · cancel anytime"
          bullets={[
            'Unlimited everything, every month',
            'Cancel anytime in one tap',
            'UPI AutoPay or card mandate',
          ]}
          cta={`Subscribe for ₹${entitlement.price_inr}/mo`}
          onClick={() => requirePlus('concierge', { plan: 'monthly' })}
        />
        <PlanCard
          tone="secondary"
          delay={reduce ? 0 : 0.12}
          badge="FLEX"
          name="One-time"
          price={`₹${entitlement.onetime_price_inr}`}
          unit={`/ ${entitlement.onetime_duration_days} days`}
          subline="One charge · no auto-renew"
          bullets={[
            `${entitlement.onetime_duration_days} days of full Plus access`,
            'Hard-expires — never charges again',
            'No card mandate required',
          ]}
          cta={`Pay ₹${entitlement.onetime_price_inr} · ${entitlement.onetime_duration_days} days`}
          onClick={() => requirePlus('concierge', { plan: 'one_time' })}
        />
      </div>

      <p className="text-[11px] text-slate-400 mb-7 flex items-center gap-1.5">
        <ShieldCheck className="w-3 h-3" />
        Payments via Razorpay — UPI, cards, netbanking. Coupon codes apply at checkout.
      </p>

      {/* Tier comparison */}
      <TierComparison />
    </>
  );
}

interface PlanCardProps {
  tone: 'primary' | 'secondary';
  delay: number;
  badge: string;
  name: string;
  price: string;
  unit: string;
  subline: string;
  bullets: string[];
  cta: string;
  onClick: () => void;
  footnote?: string;
}

function PlanCard(props: PlanCardProps) {
  const isPrimary = props.tone === 'primary';
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: motionTokens.ease.out, delay: props.delay }}
      className={`relative rounded-2xl overflow-hidden border ${
        isPrimary
          ? 'border-indigo-200 shadow-[0_8px_28px_-12px_rgba(79,70,229,0.35)]'
          : 'border-slate-200 shadow-sm'
      } bg-white p-6 flex flex-col`}
    >
      {isPrimary && (
        <div
          className="absolute top-0 left-0 right-0 h-1.5"
          style={{ backgroundImage: 'linear-gradient(90deg, #4F46E5 0%, #D946EF 55%, #F59E0B 100%)' }}
        />
      )}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-black uppercase tracking-wider text-slate-900">{props.name}</span>
        <span
          className={`text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full ${
            isPrimary ? 'bg-indigo-50 text-indigo-700' : 'bg-amber-50 text-amber-700'
          }`}
        >
          {props.badge}
        </span>
      </div>
      <div className="flex items-baseline gap-1 mb-1">
        <span className="text-3xl font-black tracking-tight text-slate-900">{props.price}</span>
        <span className="text-sm font-semibold text-slate-500">{props.unit}</span>
      </div>
      <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">{props.subline}</p>

      <ul className="space-y-2 mb-5 flex-1">
        {props.bullets.map((b) => (
          <li key={b} className="flex items-start gap-2 text-[13px] text-slate-700 leading-snug">
            <div className="w-4 h-4 rounded-full bg-indigo-50 flex items-center justify-center shrink-0 mt-0.5">
              <Check className="w-2.5 h-2.5 text-indigo-600" strokeWidth={3} />
            </div>
            <span>{b}</span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={props.onClick}
        className={`w-full rounded-full font-bold text-sm py-2.5 px-4 transition-all active:scale-[0.98] ${
          isPrimary
            ? 'bg-indigo-600 text-white hover:bg-indigo-700'
            : 'bg-slate-900 text-white hover:bg-slate-800'
        }`}
        style={
          isPrimary
            ? { boxShadow: '0 8px 24px -8px rgba(79, 70, 229, 0.55)' }
            : undefined
        }
      >
        {props.cta}
      </button>
      {props.footnote && (
        <p className="text-[10px] text-slate-400 mt-2.5 text-center font-semibold leading-snug">
          {props.footnote}
        </p>
      )}
    </motion.div>
  );
}


// ── Plus state ──────────────────────────────────────────────────────────────

function PlusState({ requirePlus }: { requirePlus: (f: 'concierge') => Promise<boolean> }) {
  const { entitlement, refresh } = useEntitlement();
  const [cancelling, setCancelling] = useState(false);
  const [confirmingCancel, setConfirmingCancel] = useState(false);

  const periodEnd = entitlement.period_end
    ? new Date(entitlement.period_end).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })
    : null;

  const cancel = async () => {
    setCancelling(true);
    try {
      await api('/api/billing/cancel', { method: 'POST' });
      await refresh();
    } catch {
      // best-effort — reset UI regardless
    } finally {
      setCancelling(false);
      setConfirmingCancel(false);
    }
  };

  return (
    <>
      {/* Status banner */}
      <div
        className="rounded-2xl border border-indigo-100 p-6 sm:p-7 mb-5"
        style={{
          backgroundImage: 'linear-gradient(135deg, #EEF2FF 0%, #FAE8FF 55%, #FEF3C7 100%)',
        }}
      >
        <div className="flex items-start gap-4">
          <PlusCrest size={56} />
          <div className="flex-1">
            <h2 className="text-xl font-black tracking-tight text-slate-900 mb-1">
              You're on <PlusWordmark className="text-xl" />
            </h2>
            {entitlement.status === 'active' && periodEnd && (
              <p className="text-sm text-slate-600">
                Renews on <strong className="text-slate-800">{periodEnd}</strong> · ₹{entitlement.price_inr}/month
              </p>
            )}
            {entitlement.status === 'one_time' && periodEnd && (
              <p className="text-sm text-slate-600">
                One-time plan · Active until <strong className="text-slate-800">{periodEnd}</strong>.
                {' '}After that, your account returns to free unless you switch to monthly.
              </p>
            )}
            {entitlement.status === 'canceled' && periodEnd && (
              <p className="text-sm text-slate-600">
                Active until <strong className="text-slate-800">{periodEnd}</strong>. After that, your account
                will move back to the free tier.
              </p>
            )}
            {entitlement.status === 'past_due' && (
              <p className="text-sm text-rose-700 font-semibold">
                Last payment failed. Update your payment method to keep Plus.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Usage */}
      <div className="bg-white rounded-2xl border border-slate-100 p-5 mb-5 grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Stat label="Active trips" value={String(entitlement.active_trip_count)} sub="No cap" />
        <Stat label="Brainstorms this month" value={String(entitlement.brainstorm_used)} sub="Unlimited" />
        <Stat label="Concierge" value="On" sub="Always available" />
        <Stat label="Offline maps" value="Enabled" sub="Plus" />
      </div>

      {/* Manage */}
      <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
        <ManageRow
          label="Update payment method"
          disabled
          hint="Coming soon"
        />
        <ManageRow
          label="Download invoices"
          disabled
          hint="Coming soon"
        />
        {entitlement.status === 'one_time' ? (
          <ManageRow
            label="Switch to monthly subscription"
            tone="accent"
            onClick={() => { void requirePlus('concierge'); }}
            hint="Keep Plus going for ₹149/mo"
          />
        ) : entitlement.status !== 'canceled' ? (
          confirmingCancel ? (
            <div className="px-5 py-4 bg-rose-50/50 border-t border-slate-100">
              <p className="text-sm text-slate-700 font-semibold mb-1">Cancel Roammate Plus?</p>
              <p className="text-xs text-slate-500 mb-3">
                You'll keep Plus until {periodEnd ?? 'the end of the current period'}. After that, active trips
                beyond 2 become read-only and concierge will lock.
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={cancel}
                  disabled={cancelling}
                  className="rounded-full bg-rose-600 text-white text-xs font-bold px-4 py-2 hover:bg-rose-700 transition-colors disabled:opacity-60"
                >
                  {cancelling ? 'Cancelling…' : 'Yes, cancel'}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmingCancel(false)}
                  className="rounded-full text-slate-500 text-xs font-bold px-4 py-2 hover:bg-slate-100 transition-colors"
                >
                  Keep Plus
                </button>
              </div>
            </div>
          ) : (
            <ManageRow
              label="Cancel subscription"
              tone="danger"
              onClick={() => setConfirmingCancel(true)}
            />
          )
        ) : null}
      </div>
    </>
  );
}


function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div>
      <p className="text-[11px] font-black uppercase tracking-wider text-slate-400">{label}</p>
      <p className="text-lg font-black text-slate-900 mt-0.5">{value}</p>
      <p className="text-xs text-slate-400">{sub}</p>
    </div>
  );
}


function ManageRow({
  label, onClick, disabled, hint, tone,
}: {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  hint?: string;
  tone?: 'danger' | 'accent';
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`w-full flex items-center justify-between px-5 py-4 border-t first:border-t-0 border-slate-100 text-left transition-colors
        ${disabled ? 'cursor-not-allowed' : 'hover:bg-slate-50'}
        ${tone === 'danger'
          ? 'text-rose-600 hover:bg-rose-50/60'
          : tone === 'accent'
            ? 'text-indigo-600 hover:bg-indigo-50/60'
            : 'text-slate-700'}
      `}
    >
      <span className="text-sm font-bold">{label}</span>
      {hint && <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">{hint}</span>}
    </button>
  );
}


function FaqRow({ q, a, last }: { q: string; a: string; last: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={last ? '' : 'border-b border-slate-100'}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full px-5 py-4 flex items-center justify-between gap-4 text-left hover:bg-slate-50 transition-colors"
      >
        <span className="text-sm font-bold text-slate-800">{q}</span>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      <motion.div
        initial={false}
        animate={{ height: open ? 'auto' : 0, opacity: open ? 1 : 0 }}
        transition={{ duration: 0.22, ease: motionTokens.ease.out }}
        className="overflow-hidden"
      >
        <p className="px-5 pb-4 text-sm text-slate-500 leading-relaxed">{a}</p>
      </motion.div>
    </div>
  );
}
