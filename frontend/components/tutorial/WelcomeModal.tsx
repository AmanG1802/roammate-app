'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, MapPin, Compass } from 'lucide-react';

export type WelcomeModalProps = {
  open: boolean;
  onStart: () => void;
  onSkip: () => void;
  starting?: boolean;
};

const FEATURES = [
  { icon: MapPin, label: 'A canned 3-day NYC trip to play with' },
  { icon: Compass, label: '8 quick steps — Timeline, Brainstorm, Concierge' },
  { icon: Sparkles, label: 'No quota burned, no Plus required for this tour' },
];

export default function WelcomeModal({ open, onStart, onSkip, starting }: WelcomeModalProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[90] bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: 6 }}
            transition={{ type: 'spring', stiffness: 260, damping: 26 }}
            className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden"
          >
            <div className="relative px-7 pt-7 pb-6 bg-gradient-to-br from-indigo-600 via-indigo-500 to-violet-500 text-white">
              <motion.div
                aria-hidden
                initial={{ opacity: 0, rotate: -10 }}
                animate={{ opacity: 1, rotate: 0 }}
                transition={{ delay: 0.05, duration: 0.4 }}
                className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-white/10 blur-xl"
              />
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/15 text-[11px] font-medium uppercase tracking-wide">
                <Sparkles size={12} />
                Quick tour
              </div>
              <h2 className="mt-3 text-2xl font-semibold leading-tight">
                Welcome to Roammate
              </h2>
              <p className="mt-1.5 text-sm text-indigo-50/90 leading-relaxed">
                Two minutes, no commitment. We&apos;ll walk you through planning a
                real-feeling NYC trip using every part of the app.
              </p>
            </div>

            <div className="px-7 py-5">
              <ul className="space-y-2.5">
                {FEATURES.map((f, i) => (
                  <motion.li
                    key={f.label}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.08 + i * 0.05 }}
                    className="flex items-center gap-3 text-sm text-slate-700"
                  >
                    <span className="h-7 w-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                      <f.icon size={15} />
                    </span>
                    {f.label}
                  </motion.li>
                ))}
              </ul>
            </div>

            <div className="px-7 pb-6 flex items-center gap-2">
              <button
                onClick={onSkip}
                className="flex-1 text-sm font-medium px-4 py-2.5 rounded-xl text-slate-600 hover:bg-slate-100 transition-colors"
              >
                Skip for now
              </button>
              <button
                onClick={onStart}
                disabled={starting}
                className="flex-1 text-sm font-semibold px-4 py-2.5 rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 shadow-md transition-colors disabled:opacity-60"
              >
                {starting ? 'Setting up…' : 'Start tour'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
