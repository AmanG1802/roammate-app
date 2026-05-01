'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, Sparkles } from 'lucide-react';
import { PersonaCatalogProvider, usePersonaCatalog } from '@/contexts/PersonaCatalogContext';

type OnboardingPersonaModalProps = {
  onComplete: (personas: string[]) => Promise<void>;
  onSkip: () => Promise<void>;
};

function PickerGrid({ onComplete, onSkip }: OnboardingPersonaModalProps) {
  const { catalog, isLoading } = usePersonaCatalog();
  const [selected, setSelected] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [showFireToast, setShowFireToast] = useState(false);
  const prevCount = useRef(0);

  useEffect(() => {
    if (selected.length >= 5 && prevCount.current < 5) {
      setShowFireToast(true);
      setTimeout(() => setShowFireToast(false), 2500);
    }
    prevCount.current = selected.length;
  }, [selected]);

  const toggle = (slug: string) => {
    setSelected((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]
    );
  };

  const handleContinue = async () => {
    setSaving(true);
    await onComplete(selected);
  };

  const handleSkip = async () => {
    setSaving(true);
    await onSkip();
  };

  return (
    <>
      <div className="px-8 py-6 overflow-y-auto flex-1">
        {isLoading ? (
          <div className="flex flex-wrap gap-3 justify-center py-4">
            {Array.from({ length: 14 }).map((_, i) => (
              <div key={i} className="h-10 w-28 rounded-lg bg-slate-100 animate-pulse" />
            ))}
          </div>
        ) : (
          <>
            <div className="flex flex-wrap gap-2.5 justify-center">
              {catalog.map((item, idx) => {
                const isSelected = selected.includes(item.slug);
                return (
                  <motion.button
                    key={item.slug}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.04, duration: 0.18 }}
                    onClick={() => toggle(item.slug)}
                    role="checkbox"
                    aria-checked={isSelected}
                    className={`relative flex items-center gap-2 py-2.5 px-4 rounded-lg border text-sm font-bold transition-all duration-150 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500
                      ${isSelected
                        ? 'border-indigo-600 border-2 bg-indigo-50 text-indigo-800 scale-105'
                        : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:shadow-sm'
                      }`}
                  >
                    <span role="img" aria-hidden>{item.icon}</span>
                    <span>{item.label}</span>
                    {isSelected && (
                      <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-indigo-600 rounded-full flex items-center justify-center">
                        <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />
                      </span>
                    )}
                  </motion.button>
                );
              })}
            </div>
            <AnimatePresence>
              {showFireToast && (
                <motion.p
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mt-4 text-center text-sm font-bold text-orange-500"
                >
                  🔥 You&apos;re getting specific!
                </motion.p>
              )}
            </AnimatePresence>
          </>
        )}
      </div>

      <div className="px-8 py-5 border-t border-slate-100 flex items-center justify-between bg-white shrink-0">
        <button
          onClick={handleSkip}
          disabled={saving}
          className="text-sm font-bold text-slate-400 hover:text-slate-600 transition-colors cursor-pointer disabled:opacity-50"
        >
          Skip for now
        </button>
        <button
          onClick={handleContinue}
          disabled={saving}
          className="px-6 py-2.5 bg-indigo-600 text-white text-sm font-black rounded-xl hover:bg-indigo-700 transition-colors cursor-pointer disabled:opacity-60"
        >
          {saving ? 'Saving…' : selected.length > 0 ? `Continue (${selected.length})` : 'Continue'}
        </button>
      </div>
    </>
  );
}

export default function OnboardingPersonaModal({ onComplete, onSkip }: OnboardingPersonaModalProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') e.preventDefault();
    };
    document.addEventListener('keydown', handleKeyDown, true);
    return () => document.removeEventListener('keydown', handleKeyDown, true);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const getFocusable = () =>
      Array.from(
        el.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
      );
    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      const focusable = getFocusable();
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last?.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener('keydown', handleTab);
    getFocusable()[0]?.focus();
    return () => document.removeEventListener('keydown', handleTab);
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-md bg-slate-900/40">
      <motion.div
        ref={containerRef}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
        className="w-[90vw] max-w-[640px] bg-white rounded-3xl shadow-2xl flex flex-col max-h-[90vh]"
        role="dialog"
        aria-modal="true"
        aria-label="Set your travel persona"
      >
        <div className="px-8 pt-8 pb-5 border-b border-slate-100 shrink-0">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-indigo-50 rounded-full text-xs font-black text-indigo-600 uppercase tracking-widest mb-4">
            <Sparkles className="w-3 h-3" />
            Welcome to Roammate
          </div>
          <h2 className="text-2xl font-black text-slate-900 leading-tight">
            What makes you tick?
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Select your travel personas — your concierge adapts to match your style.
          </p>
        </div>

        <PersonaCatalogProvider>
          <PickerGrid onComplete={onComplete} onSkip={onSkip} />
        </PersonaCatalogProvider>
      </motion.div>
    </div>
  );
}
