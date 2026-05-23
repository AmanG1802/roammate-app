'use client';

/**
 * Public Roammate Plus pricing page. Used for SEO + external referrals.
 *
 * Signed-in users tapping Subscribe go straight into the paywall flow.
 * Signed-out users are routed to /login?next=/profile/subscription, then
 * land on the subscription page which lets them subscribe immediately.
 */
import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowRight, ShieldCheck, Infinity as InfinityIcon, Wand2, Sparkles,
  CalendarClock, Zap,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/layout/Navbar';
import { getToken } from '@/lib/auth';
import { motionTokens, useAppMotion } from '@/lib/motion';
import { PlusWordmark } from '@/components/billing/PlusCrest';
import { TierComparison } from '@/components/billing/TierComparison';
import { useEntitlement, type PaywallPlan } from '@/hooks/useEntitlement';


type BillingChoice = PaywallPlan;

const PLUS_FEATURES = [
  { icon: InfinityIcon, text: 'Unlimited AI brainstorms' },
  { icon: Wand2, text: 'Always-on travel co-pilot' },
  { icon: CalendarClock, text: 'Plan Unlimited Trips' },
];

export default function PricingPage() {
  const { entitlement, requirePlus } = useEntitlement();
  const router = useRouter();
  const { reduce } = useAppMotion();
  const [choice, setChoice] = useState<BillingChoice>('monthly');

  const subscribe = async (plan: BillingChoice) => {
    if (!getToken()) {
      router.push('/login?next=/profile/subscription');
      return;
    }
    if (entitlement.tier === 'plus') {
      router.push('/profile/subscription');
      return;
    }
    await requirePlus('concierge', { plan });
  };

  const monthly = entitlement.price_inr;
  const oneTime = entitlement.onetime_price_inr;
  const days = entitlement.onetime_duration_days;

  return (
    <div className="min-h-screen bg-white text-slate-900 overflow-x-hidden">
      <Navbar />

      {/* Decorative background blobs */}
      <div className="absolute inset-x-0 top-0 -z-10 pointer-events-none h-[80vh] overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[55vw] h-[55vw] bg-indigo-300/25 rounded-full blur-[140px]" />
        <div className="absolute top-[20%] right-[-10%] w-[45vw] h-[45vw] bg-fuchsia-300/25 rounded-full blur-[130px]" />
        <div className="absolute top-[10%] left-[40%] w-[25vw] h-[25vw] bg-amber-200/30 rounded-full blur-[120px]" />
      </div>

      {/* Viewport-fitting hero block */}
      <main className="max-w-5xl mx-auto px-6 md:px-10 pt-24 md:pt-28 pb-12">
        <motion.div
          initial={reduce ? undefined : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: motionTokens.ease.out }}
          className="flex flex-col items-center text-center"
        >
          <h1 className="text-5xl sm:text-7xl md:text-8xl font-black tracking-tighter leading-[1.02]">
            <span className="block">Travel further with</span>
            <PlusWordmark className="block text-5xl sm:text-7xl md:text-8xl" />
          </h1>
        </motion.div>

        {/* Features list (bullets with icons) */}
        <motion.ul
          initial="hidden"
          animate="show"
          variants={{
            hidden: {},
            show: { transition: { staggerChildren: 0.07, delayChildren: 0.1 } },
          }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-center gap-3 sm:gap-6 max-w-3xl mx-auto mt-8 mb-8"
        >
          {PLUS_FEATURES.map((f) => (
            <motion.li
              key={f.text}
              variants={{
                hidden: { opacity: 0, x: -10 },
                show: { opacity: 1, x: 0 },
              }}
              transition={{ duration: 0.35, ease: motionTokens.ease.out }}
              className="flex items-center gap-3 text-sm md:text-[15px] font-semibold text-slate-700"
            >
              <span className="inline-flex w-8 h-8 rounded-xl items-center justify-center shrink-0 bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-white shadow-md shadow-indigo-200">
                <f.icon className="w-4 h-4" />
              </span>
              <span>{f.text}</span>
            </motion.li>
          ))}
        </motion.ul>

        {/* Billing toggle */}
        <motion.div
          initial={reduce ? undefined : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2, ease: motionTokens.ease.out }}
          className="flex justify-center mb-6"
        >
          <BillingSegmented value={choice} onChange={setChoice} />
        </motion.div>

        {/* Single animated card */}
        <div className="max-w-md mx-auto" style={{ minHeight: 280 }}>
          <AnimatePresence mode="wait" initial={false}>
            {choice === 'monthly' ? (
              <PlanCard
                key="monthly"
                tone="indigo"
                badge={{ Icon: Sparkles, text: 'Most popular', tint: 'bg-indigo-50 text-indigo-700 border-indigo-100' }}
                title="Monthly"
                tagline="Renew as long as you're roaming."
                price={monthly}
                unit="/ month"
                ctaLabel={entitlement.tier === 'plus' ? 'Manage subscription' : `Subscribe · ₹${monthly}/mo`}
                footnote="UPI · Card · Auto-renews · Cancel anytime · Billed by Razorpay"
                onClick={() => subscribe('monthly')}
              />
            ) : (
              <PlanCard
                key="one_time"
                tone="fuchsia"
                badge={{ Icon: Zap, text: 'One trip, one charge', tint: 'bg-fuchsia-50 text-fuchsia-700 border-fuchsia-100' }}
                title="One-time"
                tagline={`Perfect for a single ${days}-day trip.`}
                price={oneTime}
                unit={`/ ${days} days`}
                ctaLabel={entitlement.tier === 'plus' ? 'Manage subscription' : `Pay ₹${oneTime} · ${days} days`}
                footnote="UPI · Card · One charge · No renewal · Billed by Razorpay"
                onClick={() => subscribe('one_time')}
              />
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Below the fold: comparison table */}
      <section className="max-w-3xl mx-auto px-6 md:px-10 pb-20">
        <motion.div
          initial={reduce ? undefined : { opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.55, ease: motionTokens.ease.out }}
        >
          <h2 className="text-2xl md:text-3xl font-black tracking-tighter text-center mb-8">
            Free vs <PlusWordmark className="text-2xl md:text-3xl" />
          </h2>
          <TierComparison />
        </motion.div>

        <p className="text-center text-xs text-slate-400 mt-12">
          Need a team plan or have a question?{' '}
          <a href="mailto:hello@roammate.xyz" className="text-slate-600 underline-offset-2 hover:underline">
            hello@roammate.xyz
          </a>
        </p>
      </section>
    </div>
  );
}


// ── Billing toggle ──────────────────────────────────────────────────────────

function BillingSegmented({
  value, onChange,
}: { value: BillingChoice; onChange: (v: BillingChoice) => void }) {
  const options: { id: BillingChoice; label: string }[] = [
    { id: 'monthly', label: 'Monthly' },
    { id: 'one_time', label: 'One-time' },
  ];
  return (
    <div className="relative grid grid-cols-2 gap-1 p-1.5 bg-slate-100 rounded-full border border-slate-200 shadow-sm">
      {options.map((opt) => {
        const active = value === opt.id;
        return (
          <button
            key={opt.id}
            type="button"
            onClick={() => onChange(opt.id)}
            className="relative z-10 px-7 py-2.5 rounded-full transition-colors min-w-[140px]"
          >
            <span className={`text-xs font-black uppercase tracking-[0.15em] transition-colors ${active ? 'text-white' : 'text-slate-500'}`}>
              {opt.label}
            </span>
          </button>
        );
      })}
      <motion.div
        layout
        className="absolute top-1.5 bottom-1.5 rounded-full bg-slate-900 shadow-md"
        style={{ width: 'calc(50% - 6px)' }}
        animate={{ left: value === 'monthly' ? 6 : 'calc(50% + 0px)' }}
        transition={{ type: 'spring', stiffness: 380, damping: 30 }}
      />
    </div>
  );
}


// ── Plan card ───────────────────────────────────────────────────────────────

function PlanCard({
  tone, badge, title, tagline, price, unit, ctaLabel, onClick, footnote,
}: {
  tone: 'indigo' | 'fuchsia';
  badge: { Icon: React.ComponentType<{ className?: string }>; text: string; tint: string };
  title: string;
  tagline: string;
  price: number;
  unit: string;
  ctaLabel: string;
  onClick: () => void;
  footnote: string;
}) {
  const toneClasses = tone === 'indigo'
    ? {
        cta: 'bg-indigo-600 hover:bg-indigo-700',
        ctaShadow: '0 14px 36px -14px rgba(79, 70, 229, 0.65)',
        ring: 'ring-indigo-200/60',
        glow: 'shadow-indigo-200/60',
      }
    : {
        cta: 'bg-fuchsia-600 hover:bg-fuchsia-700',
        ctaShadow: '0 14px 36px -14px rgba(217, 70, 239, 0.55)',
        ring: 'ring-fuchsia-200/60',
        glow: 'shadow-fuchsia-200/60',
      };

  return (
    <motion.div
      key={title}
      initial={{ opacity: 0, y: 18, scale: 0.96, filter: 'blur(8px)' }}
      animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
      exit={{ opacity: 0, y: -14, scale: 0.97, filter: 'blur(6px)' }}
      transition={{ duration: 0.42, ease: motionTokens.ease.out }}
      className={`relative rounded-3xl bg-white p-7 sm:p-8 border border-transparent ring-2 ${toneClasses.ring} shadow-2xl ${toneClasses.glow}`}
    >
      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${badge.tint}`}>
        <badge.Icon className="w-3 h-3" />
        {badge.text}
      </span>

      <h3 className="mt-5 text-2xl font-black tracking-tighter text-slate-900">
        {title}
      </h3>
      <p className="text-sm text-slate-500 font-medium mb-5">{tagline}</p>

      <div className="flex items-baseline gap-2 mb-7">
        <motion.span
          key={`price-${title}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
          className="text-5xl font-black tracking-tighter text-slate-900"
        >
          ₹{price}
        </motion.span>
        <span className="text-base text-slate-500 font-semibold">{unit}</span>
      </div>

      <button
        type="button"
        onClick={onClick}
        className={`group w-full inline-flex items-center justify-center gap-2 rounded-full text-white font-bold text-[15px] py-3.5 px-6 transition-all active:scale-[0.98] ${toneClasses.cta}`}
        style={{ boxShadow: toneClasses.ctaShadow }}
      >
        {ctaLabel}
        <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
      </button>
      <p className="text-[11px] text-slate-400 mt-3 flex items-center justify-center gap-1.5 text-center">
        <ShieldCheck className="w-3 h-3 shrink-0" />
        {footnote}
      </p>
    </motion.div>
  );
}
