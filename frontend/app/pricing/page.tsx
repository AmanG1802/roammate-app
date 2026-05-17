'use client';

/**
 * Public Roammate Plus pricing page. Used for SEO + external referrals.
 *
 * Signed-in users tapping Subscribe go straight into the paywall flow.
 * Signed-out users are routed to /login?next=/profile/subscription, then
 * land on the subscription page which lets them subscribe immediately.
 */
import { motion } from 'framer-motion';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getToken } from '@/lib/auth';
import { motionTokens, useAppMotion } from '@/lib/motion';
import { PlusCrest, PlusWordmark } from '@/components/billing/PlusCrest';
import { TierComparison } from '@/components/billing/TierComparison';
import { useEntitlement } from '@/hooks/useEntitlement';


export default function PricingPage() {
  const { entitlement, requirePlus } = useEntitlement();
  const router = useRouter();
  const { reduce } = useAppMotion();

  const subscribe = async () => {
    if (!getToken()) {
      router.push('/login?next=/profile/subscription');
      return;
    }
    if (entitlement.tier === 'plus') {
      router.push('/profile/subscription');
      return;
    }
    await requirePlus('concierge');
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top nav */}
      <header className="h-14 bg-white border-b border-slate-100 flex items-center px-6 gap-4">
        <Link href="/" className="text-sm font-black text-slate-900 tracking-tight">
          Roammate
        </Link>
        <div className="flex-1" />
        <Link href="/login" className="text-sm font-bold text-slate-500 hover:text-slate-800 transition-colors">
          Sign in
        </Link>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-14 sm:py-20">
        <motion.div
          initial={reduce ? undefined : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: motionTokens.ease.out }}
          className="flex flex-col items-center text-center mb-12"
        >
          <PlusCrest size={88} className="mb-6" />
          <h1 className="text-4xl sm:text-5xl font-black tracking-tight mb-3">
            <PlusWordmark className="text-4xl sm:text-5xl" />
          </h1>
          <p className="text-lg text-slate-500 max-w-md leading-snug">
            Unlimited AI concierge. Offline maps. Built for travelers who
            actually go places.
          </p>

          <div className="mt-8 flex items-baseline gap-2">
            <span className="text-5xl font-black text-slate-900 tracking-tighter">₹149</span>
            <span className="text-base text-slate-500 font-semibold">/ month</span>
          </div>

          <button
            type="button"
            onClick={subscribe}
            className="mt-6 group inline-flex items-center gap-2 rounded-full bg-indigo-600 text-white font-bold text-base py-3.5 px-7 transition-all hover:bg-indigo-700 active:scale-[0.98]"
            style={{ boxShadow: '0 12px 32px -12px rgba(79, 70, 229, 0.6)' }}
          >
            {entitlement.tier === 'plus' ? 'Manage subscription' : 'Subscribe for ₹149/mo'}
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
          </button>
          <p className="text-[11px] text-slate-400 mt-3 flex items-center gap-1.5">
            <ShieldCheck className="w-3 h-3" />
            UPI · Card · Cancel anytime · Billed by Razorpay
          </p>
        </motion.div>

        <motion.div
          initial={reduce ? undefined : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: motionTokens.ease.out, delay: 0.15 }}
        >
          <TierComparison />
        </motion.div>

        <p className="text-center text-xs text-slate-400 mt-10">
          Need a team plan or have a question?{' '}
          <a href="mailto:hello@roammate.xyz" className="text-slate-600 underline-offset-2 hover:underline">
            hello@roammate.xyz
          </a>
        </p>
      </main>
    </div>
  );
}
