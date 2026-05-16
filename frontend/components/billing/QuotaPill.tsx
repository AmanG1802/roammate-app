'use client';

/**
 * Tiny pill that surfaces a usage counter and color-shifts as the user
 * approaches a cap. Used today for the monthly brainstorm quota; reusable
 * for any other counted free-tier resource.
 */
import { Sparkles } from 'lucide-react';
import { useEntitlement } from '@/hooks/useEntitlement';

interface Props {
  className?: string;
  onClick?: () => void;
}

export function BrainstormQuotaPill({ className = '', onClick }: Props) {
  const { entitlement, requirePlus } = useEntitlement();
  // Plus = unlimited: nothing to show.
  if (entitlement.brainstorm_remaining === null) return null;

  const remaining = entitlement.brainstorm_remaining;
  const cap = entitlement.brainstorm_cap ?? 15;

  let tone: 'ok' | 'warn' | 'danger' = 'ok';
  if (remaining === 0) tone = 'danger';
  else if (remaining <= 3) tone = 'warn';

  const palette =
    tone === 'danger'
      ? 'bg-rose-50 text-rose-700 border-rose-200'
      : tone === 'warn'
        ? 'bg-amber-50 text-amber-700 border-amber-200'
        : 'bg-indigo-50 text-indigo-700 border-indigo-100';

  const handleClick = onClick ?? (() => { if (remaining === 0) requirePlus('brainstorm_quota'); });

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-black uppercase tracking-wider transition-colors ${palette} ${className}`}
    >
      <Sparkles className="w-3 h-3" />
      {remaining === 0
        ? 'No brainstorms left'
        : `${remaining} / ${cap} left`}
    </button>
  );
}
