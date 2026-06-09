'use client';

/**
 * Self-contained coupon entry control used by the paywall and the
 * subscription management page.
 *
 * Behavior:
 *   - "Have a code?" link expands to a TextInput + Apply button (Framer
 *     height animation).
 *   - On apply, calls POST /billing/coupons/validate with the active
 *     `target` (one_time | subscription). Surfaces the backend error code
 *     as a human message and emits the quote upward via `onApplied`.
 *   - Plan toggle changes in the parent re-quote automatically by passing
 *     a fresh `target` prop (we re-validate whenever target changes if a
 *     code is already typed).
 */

import { motion, AnimatePresence } from 'framer-motion';
import { Check, Loader2, Sparkles, X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '@/lib/api';
import { motionTokens } from '@/lib/motion';

export type CouponTarget = 'one_time' | 'subscription';

export interface CouponQuote {
  coupon_id: number;
  code: string;
  applies_to: string;
  original_amount_paise: number;
  discount_amount_paise: number;
  final_amount_paise: number;
  razorpay_offer_id: string | null;
  apple_offer_id: string | null;
  display_message: string;
}

interface Props {
  target: CouponTarget;
  initialCode?: string;
  autoApply?: boolean;
  onApplied: (quote: CouponQuote | null) => void;
}

export function CouponInput({ target, initialCode, autoApply, onApplied }: Props) {
  const [expanded, setExpanded] = useState(Boolean(initialCode));
  const [code, setCode] = useState(initialCode?.toUpperCase() ?? '');
  const [quote, setQuote] = useState<CouponQuote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const apply = useCallback(async (codeToTry: string) => {
    const trimmed = codeToTry.trim().toUpperCase();
    if (!trimmed) return;
    setError(null);
    setSubmitting(true);
    try {
      const body = await api<CouponQuote>('/api/billing/coupons/validate', {
        method: 'POST',
        json: { code: trimmed, target },
      });
      setQuote(body);
      onApplied(body);
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = (err.data as any)?.detail;
        const msg =
          (detail && detail.message) ||
          (typeof detail === 'string' ? detail : 'This code is not valid.');
        setError(msg);
      } else {
        setError('Could not check that code. Please try again.');
      }
      setQuote(null);
      onApplied(null);
    } finally {
      setSubmitting(false);
    }
  }, [target, onApplied]);

  // Re-quote when target changes (user toggled plan after applying a code).
  useEffect(() => {
    if (quote) {
      void apply(quote.code);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);

  // Auto-apply from a URL param on mount.
  useEffect(() => {
    if (autoApply && initialCode) {
      setExpanded(true);
      void apply(initialCode);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clear = () => {
    setCode('');
    setQuote(null);
    setError(null);
    onApplied(null);
  };

  return (
    <div className="text-sm">
      {!expanded ? (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="text-xs font-bold uppercase tracking-wider text-indigo-600 hover:text-indigo-700"
        >
          Have a code?
        </button>
      ) : (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          transition={{ duration: 0.2, ease: motionTokens.ease.out }}
          className="overflow-hidden"
        >
          {!quote ? (
            <form
              onSubmit={(e) => { e.preventDefault(); void apply(code); }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="Enter code"
                autoCapitalize="characters"
                autoCorrect="off"
                spellCheck={false}
                className="flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold tracking-wider uppercase focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400"
              />
              <button
                type="submit"
                disabled={submitting || !code.trim()}
                className="rounded-xl bg-slate-900 text-white text-xs font-black uppercase tracking-wider px-4 py-2 disabled:opacity-50"
              >
                {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Apply'}
              </button>
            </form>
          ) : (
            <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2">
              <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center shrink-0">
                <Check className="w-3.5 h-3.5 text-white" strokeWidth={3} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-black tracking-wider text-emerald-700 uppercase">
                  {quote.code}
                </div>
                <div className="text-[11px] text-emerald-600 truncate">
                  {quote.display_message}
                </div>
              </div>
              <button
                type="button"
                onClick={clear}
                aria-label="Remove code"
                className="w-6 h-6 rounded-full hover:bg-emerald-100 flex items-center justify-center text-emerald-700"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.18 }}
                className="overflow-hidden"
              >
                <div className="mt-2 flex items-center gap-1.5 text-xs font-semibold text-rose-600">
                  <Sparkles className="w-3 h-3" />
                  <span>{error}</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </div>
  );
}
