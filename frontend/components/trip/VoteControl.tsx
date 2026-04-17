'use client';

import { useCallback, useEffect, useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';

type Kind = 'idea' | 'event';

type Tally = { up: number; down: number; my_vote: number };

const API = process.env.NEXT_PUBLIC_API_URL ?? '';

function authHeaders(): Record<string, string> {
  const t = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  return t ? { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

export default function VoteControl({
  kind,
  id,
  canVote,
  initial,
  size = 'md',
}: {
  kind: Kind;
  id: number | string;
  canVote: boolean;
  initial?: Tally;
  size?: 'sm' | 'md';
}) {
  const [tally, setTally] = useState<Tally>(initial ?? { up: 0, down: 0, my_vote: 0 });
  const [loading, setLoading] = useState(!initial);
  const [pending, setPending] = useState(false);

  const path = kind === 'idea' ? `ideas/${id}` : `events/${id}`;

  const fetchTally = useCallback(async () => {
    try {
      const res = await fetch(`${API}/${path}/votes`, { headers: authHeaders() });
      if (res.ok) setTally(await res.json());
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [path]);

  useEffect(() => {
    if (!initial) fetchTally();
  }, [initial, fetchTally]);

  const cast = useCallback(async (want: 1 | -1) => {
    if (!canVote || pending) return;
    const prev = tally;
    const nextValue = tally.my_vote === want ? 0 : want;

    // Optimistic update
    const optimistic: Tally = { up: tally.up, down: tally.down, my_vote: nextValue };
    if (tally.my_vote === 1) optimistic.up = Math.max(0, optimistic.up - 1);
    if (tally.my_vote === -1) optimistic.down = Math.max(0, optimistic.down - 1);
    if (nextValue === 1) optimistic.up += 1;
    if (nextValue === -1) optimistic.down += 1;
    setTally(optimistic);

    setPending(true);
    try {
      const res = await fetch(`${API}/${path}/vote`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ value: nextValue }),
      });
      if (res.ok) {
        setTally(await res.json());
      } else {
        setTally(prev);
      }
    } catch {
      setTally(prev);
    } finally {
      setPending(false);
    }
  }, [canVote, pending, tally, path]);

  const btnBase = size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-1 text-xs';
  const iconCls = size === 'sm' ? 'w-2.5 h-2.5' : 'w-3 h-3';
  const containerCls = size === 'sm' ? 'gap-1' : 'gap-1.5';

  const disabledCls = canVote ? '' : 'opacity-60 cursor-not-allowed';
  const upActive = tally.my_vote === 1;
  const downActive = tally.my_vote === -1;

  return (
    <div
      className={`inline-flex items-center ${containerCls}`}
      onClick={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
      title={canVote ? undefined : 'Your role is view-only and cannot vote'}
    >
      <button
        type="button"
        onClick={() => cast(1)}
        disabled={!canVote || pending || loading}
        className={`${btnBase} rounded-lg font-black inline-flex items-center gap-1 transition-colors ${disabledCls} ${
          upActive
            ? 'bg-emerald-100 text-emerald-700'
            : 'bg-slate-50 text-slate-500 hover:bg-emerald-50 hover:text-emerald-600'
        }`}
        aria-label="Upvote"
      >
        <ThumbsUp className={iconCls} />
        {tally.up}
      </button>
      <button
        type="button"
        onClick={() => cast(-1)}
        disabled={!canVote || pending || loading}
        className={`${btnBase} rounded-lg font-black inline-flex items-center gap-1 transition-colors ${disabledCls} ${
          downActive
            ? 'bg-rose-100 text-rose-700'
            : 'bg-slate-50 text-slate-500 hover:bg-rose-50 hover:text-rose-600'
        }`}
        aria-label="Downvote"
      >
        <ThumbsDown className={iconCls} />
        {tally.down}
      </button>
    </div>
  );
}
