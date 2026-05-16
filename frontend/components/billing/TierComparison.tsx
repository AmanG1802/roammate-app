'use client';

/**
 * Free vs Plus tier comparison table. Used in three places:
 *   - profile/subscription (full)
 *   - PaywallModal (compact)
 *   - /pricing marketing page (full)
 *
 * Rows animate in row-by-row with a 0.06s stagger using Framer Motion.
 */
import { motion } from 'framer-motion';
import {
  Check, Compass, Infinity as InfinityIcon, MapPinned, Sparkles, X,
} from 'lucide-react';
import { motionTokens } from '@/lib/motion';

interface Row {
  label: string;
  free: string;
  plus: string;
  Icon: typeof Sparkles;
  highlight?: boolean; // emphasize this row (Plus column gets brand color)
}

const ROWS: Row[] = [
  {
    label: 'Active trips',
    free: '2 at a time',
    plus: 'Unlimited',
    Icon: Compass,
  },
  {
    label: 'AI brainstorms',
    free: '15 / month',
    plus: 'Unlimited',
    Icon: Sparkles,
  },
  {
    label: 'AI concierge',
    free: '—',
    plus: 'Always on',
    Icon: InfinityIcon,
    highlight: true,
  },
  {
    label: 'Offline maps',
    free: '—',
    plus: 'Included',
    Icon: MapPinned,
    highlight: true,
  },
];


interface Props {
  variant?: 'full' | 'compact';
  className?: string;
}

export function TierComparison({ variant = 'full', className = '' }: Props) {
  const compact = variant === 'compact';
  return (
    <motion.div
      initial="initial"
      animate="animate"
      transition={{ staggerChildren: 0.06 }}
      className={`overflow-hidden rounded-2xl border border-slate-100 bg-white ${className}`}
    >
      {/* Header */}
      <div className="grid grid-cols-[1.4fr_1fr_1fr] items-center px-5 py-3 bg-slate-50 border-b border-slate-100">
        <span className="text-[11px] font-black uppercase tracking-wider text-slate-400">Feature</span>
        <span className="text-[11px] font-black uppercase tracking-wider text-slate-400">Free</span>
        <span className="text-[11px] font-black uppercase tracking-wider"
          style={{
            backgroundImage: 'linear-gradient(135deg, #4F46E5 0%, #D946EF 55%, #F59E0B 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Plus
        </span>
      </div>

      {ROWS.map(({ label, free, plus, Icon, highlight }) => (
        <motion.div
          key={label}
          variants={{
            initial: { opacity: 0, y: 6 },
            animate: { opacity: 1, y: 0, transition: { duration: 0.22, ease: motionTokens.ease.out } },
          }}
          className={`grid grid-cols-[1.4fr_1fr_1fr] items-center px-5 ${compact ? 'py-2.5' : 'py-3.5'} border-b border-slate-50 last:border-b-0`}
        >
          <div className="flex items-center gap-2.5 text-sm font-semibold text-slate-700">
            <Icon className="w-4 h-4 text-slate-400 shrink-0" />
            <span>{label}</span>
          </div>
          <div className={`text-sm ${free === '—' ? 'text-slate-300' : 'text-slate-500'}`}>
            {free === '—' ? <X className="w-4 h-4" /> : free}
          </div>
          <div
            className={`text-sm font-bold flex items-center gap-1.5 ${highlight ? '' : 'text-slate-700'}`}
            style={highlight ? {
              backgroundImage: 'linear-gradient(135deg, #4F46E5 0%, #D946EF 55%, #F59E0B 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            } : undefined}
          >
            {plus === 'Unlimited' || plus === 'Always on'
              ? (
                <>
                  <InfinityIcon className="w-3.5 h-3.5" />
                  {plus}
                </>
              )
              : (
                <>
                  <Check className="w-3.5 h-3.5" />
                  {plus}
                </>
              )
            }
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}
