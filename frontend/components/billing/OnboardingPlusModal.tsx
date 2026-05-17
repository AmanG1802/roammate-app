'use client';

/**
 * Two-step onboarding modal that follows the persona picker:
 *   A. "Here's what you can do free"  — sets free-tier expectations
 *   B. "Want the full Roammate?"      — soft Plus pitch (skippable)
 *
 * One-time per user. Triggered from the dashboard right after the persona
 * modal closes. No card capture; if the user picks "See Plus" we route them
 * to the contextual paywall flow.
 */

import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowRight, Calendar, CheckCircle2, Infinity as InfinityIcon,
  MapPinned, MessageCircle, Sparkles, X,
} from 'lucide-react';
import { useState } from 'react';
import { motionTokens, useAppMotion } from '@/lib/motion';
import { PlusCrest, PlusWordmark } from './PlusCrest';
import { useEntitlement } from '@/hooks/useEntitlement';


type Step = 'free' | 'plus';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function OnboardingPlusModal({ open, onClose }: Props) {
  const [step, setStep] = useState<Step>('free');
  const { reduce } = useAppMotion();
  const { requirePlus } = useEntitlement();

  const handleSeePlus = async () => {
    onClose();
    // Let the persona/onboarding modal animation finish before stacking another.
    setTimeout(() => { void requirePlus('concierge'); }, 250);
  };

  const handleSubsequentClose = () => {
    setStep('free'); // reset for next time (should never re-open, but cheap insurance)
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="onboard-plus-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[90] bg-slate-900/40 backdrop-blur-[2px] flex items-end sm:items-center justify-center p-0 sm:p-4"
        >
          <motion.div
            initial={{ opacity: 0, y: reduce ? 0 : 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: reduce ? 0 : 12 }}
            transition={{ duration: 0.32, ease: motionTokens.ease.out }}
            className="relative w-full sm:max-w-md bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden"
            style={{
              boxShadow: '0 24px 80px -24px rgba(15, 23, 42, 0.35), 0 0 0 1px rgba(79, 70, 229, 0.08)',
            }}
            role="dialog"
            aria-modal="true"
          >
            {/* Close (skip) */}
            <button
              type="button"
              onClick={handleSubsequentClose}
              aria-label="Skip onboarding"
              className="absolute top-4 right-4 w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors z-10"
            >
              <X className="w-4 h-4" />
            </button>

            <AnimatePresence mode="wait">
              {step === 'free' && (
                <motion.div
                  key="free"
                  initial={{ opacity: 0, x: reduce ? 0 : 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: reduce ? 0 : -12 }}
                  transition={{ duration: 0.22, ease: motionTokens.ease.out }}
                  className="px-6 sm:px-8 pt-8 pb-6"
                >
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 rounded-full text-[11px] font-black text-emerald-700 uppercase tracking-widest mb-4">
                    <Sparkles className="w-3 h-3" />
                    You're in
                  </div>
                  <h2 className="text-2xl font-black text-slate-900 tracking-tight mb-1.5">
                    Here&apos;s what you can do — free.
                  </h2>
                  <p className="text-[15px] text-slate-500 leading-snug mb-6">
                    No card, no clock. Plan, brainstorm, and explore on us.
                  </p>

                  <motion.div
                    initial="initial"
                    animate="animate"
                    transition={{ staggerChildren: 0.08 }}
                    className="space-y-2.5 mb-7"
                  >
                    <FreeFeatureRow
                      Icon={Calendar}
                      title="Plan 2 trips at a time"
                      sub="Past trips stay forever — read-only history."
                    />
                    <FreeFeatureRow
                      Icon={Sparkles}
                      title="15 AI brainstorms each month"
                      sub="More than enough to scope your next adventure."
                    />
                    <FreeFeatureRow
                      Icon={MapPinned}
                      title="Visual map planning"
                      sub="Drag, drop, and route — across every trip."
                    />
                  </motion.div>

                  <button
                    type="button"
                    onClick={() => setStep('plus')}
                    className="w-full rounded-full bg-slate-900 text-white font-bold text-[15px] py-3 px-6 inline-flex items-center justify-center gap-2 transition-all hover:bg-slate-800 active:scale-[0.98]"
                  >
                    Start planning
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </motion.div>
              )}

              {step === 'plus' && (
                <motion.div
                  key="plus"
                  initial={{ opacity: 0, x: reduce ? 0 : 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: reduce ? 0 : -12 }}
                  transition={{ duration: 0.22, ease: motionTokens.ease.out }}
                  className="px-6 sm:px-8 pt-8 pb-6"
                >
                  <PlusCrest size={56} className="mb-5" />
                  <h2 className="text-2xl font-black text-slate-900 tracking-tight mb-1.5">
                    Want the full Roammate?
                  </h2>
                  <p className="text-[15px] text-slate-500 leading-snug mb-6">
                    <PlusWordmark className="text-[15px] inline" /> unlocks the
                    concierge, unlimited brainstorms, and offline maps.
                  </p>

                  <motion.div
                    initial="initial"
                    animate="animate"
                    transition={{ staggerChildren: 0.1 }}
                    className="space-y-2 mb-7"
                  >
                    <PlusBullet text="Unlimited AI brainstorms" />
                    <PlusBullet text="Always-on AI concierge" />
                    <PlusBullet text="Offline maps & pins" />
                  </motion.div>

                  <div className="flex flex-col gap-2">
                    <button
                      type="button"
                      onClick={handleSeePlus}
                      className="w-full rounded-full text-white font-bold text-[15px] py-3 px-6 transition-all active:scale-[0.98]"
                      style={{
                        backgroundImage: 'linear-gradient(135deg, #4F46E5 0%, #D946EF 55%, #F59E0B 100%)',
                        boxShadow: '0 12px 32px -12px rgba(79, 70, 229, 0.55)',
                      }}
                    >
                      See Plus — ₹149/mo
                    </button>
                    <button
                      type="button"
                      onClick={handleSubsequentClose}
                      className="w-full rounded-full text-slate-500 hover:text-slate-700 font-semibold text-sm py-2 transition-colors"
                    >
                      Maybe later
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}


function FreeFeatureRow({
  Icon, title, sub,
}: { Icon: typeof Calendar; title: string; sub: string }) {
  return (
    <motion.div
      variants={{
        initial: { opacity: 0, y: 6 },
        animate: { opacity: 1, y: 0, transition: { duration: 0.26, ease: motionTokens.ease.out } },
      }}
      className="flex items-start gap-3 bg-slate-50 rounded-2xl p-4 border border-slate-100"
    >
      <div className="w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center shrink-0">
        <Icon className="w-5 h-5 text-indigo-600" strokeWidth={2.2} />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-black text-slate-900">{title}</p>
        <p className="text-xs text-slate-500 mt-0.5 leading-snug">{sub}</p>
      </div>
    </motion.div>
  );
}


function PlusBullet({ text }: { text: string }) {
  return (
    <motion.div
      variants={{
        initial: { opacity: 0, y: 6 },
        animate: { opacity: 1, y: 0, transition: { duration: 0.22, ease: motionTokens.ease.out } },
      }}
      className="flex items-center gap-2.5 text-sm text-slate-700 font-semibold"
    >
      <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2.4} />
      {text}
    </motion.div>
  );
}
