'use client';

/**
 * Segmented Monthly / One-time control used at the top of the paywall.
 * Sliding indigo pill animates between options.
 */

import { motion } from 'framer-motion';
import { motionTokens } from '@/lib/motion';

export type PlanChoice = 'monthly' | 'one_time';

interface Props {
  value: PlanChoice;
  monthlyPrice: number;
  oneTimePrice: number;
  oneTimeDays: number;
  onChange: (v: PlanChoice) => void;
}

export function PlanToggle({ value, monthlyPrice, oneTimePrice, oneTimeDays, onChange }: Props) {
  const options: { id: PlanChoice; label: string; sub: string }[] = [
    { id: 'monthly', label: 'Monthly', sub: `₹${monthlyPrice} / mo` },
    { id: 'one_time', label: 'One-time', sub: `₹${oneTimePrice} · ${oneTimeDays}d` },
  ];
  return (
    <div className="relative grid grid-cols-2 gap-1 p-1 bg-slate-100 rounded-2xl">
      {options.map((opt) => {
        const active = value === opt.id;
        return (
          <button
            key={opt.id}
            type="button"
            onClick={() => onChange(opt.id)}
            className="relative z-10 flex flex-col items-center py-2 px-2 rounded-xl transition-colors"
          >
            <span className={`text-xs font-black uppercase tracking-wider ${active ? 'text-white' : 'text-slate-500'}`}>
              {opt.label}
            </span>
            <span className={`text-[10px] mt-0.5 font-semibold ${active ? 'text-white/85' : 'text-slate-400'}`}>
              {opt.sub}
            </span>
          </button>
        );
      })}
      <motion.div
        layout
        className="absolute top-1 bottom-1 rounded-xl bg-slate-900"
        style={{ width: 'calc(50% - 4px)' }}
        animate={{ left: value === 'monthly' ? 4 : 'calc(50% + 0px)' }}
        transition={{ duration: 0.22, ease: motionTokens.ease.out }}
      />
    </div>
  );
}
