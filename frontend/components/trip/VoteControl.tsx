'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';

type Kind = 'idea' | 'event';

type Tally = { up: number; down: number; my_vote: number };
type VoterList = { up_voters: { name: string }[]; down_voters: { name: string }[] };

const API = process.env.NEXT_PUBLIC_API_URL ?? '';

function authHeaders(): Record<string, string> {
  const t = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  return t ? { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

function AnimatedCount({ value, className }: { value: number; className?: string }) {
  const [display, setDisplay] = useState(value);
  const [animating, setAnimating] = useState(false);
  const prevRef = useRef(value);

  useEffect(() => {
    if (value !== prevRef.current) {
      setAnimating(true);
      const timer = setTimeout(() => {
        setDisplay(value);
        setAnimating(false);
      }, 100);
      prevRef.current = value;
      return () => clearTimeout(timer);
    }
    setDisplay(value);
  }, [value]);

  return (
    <span
      className={`inline-block transition-all duration-200 ${animating ? 'scale-125 opacity-70' : 'scale-100 opacity-100'} ${className ?? ''}`}
    >
      {display}
    </span>
  );
}

function VoterPopup({ names }: { names: string[] }) {
  if (names.length === 0) return null;
  return (
    <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1.5 z-50 pointer-events-none">
      <div className="bg-slate-800 text-white text-[10px] font-bold rounded-lg px-2.5 py-1.5 shadow-lg whitespace-nowrap max-w-[180px]">
        {names.map((n, i) => (
          <div key={i} className="truncate leading-relaxed">{n}</div>
        ))}
      </div>
    </div>
  );
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
  const [voters, setVoters] = useState<VoterList | null>(null);
  const [hoverUp, setHoverUp] = useState(false);
  const [hoverDown, setHoverDown] = useState(false);
  const votersFetched = useRef(false);

  const path = kind === 'idea' ? `ideas/${id}` : `events/${id}`;

  const fetchTally = useCallback(async () => {
    try {
      const res = await fetch(`${API}/${path}/votes`, { headers: authHeaders() });
      if (res.ok) setTally(await res.json());
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [path]);

  const fetchVoters = useCallback(async () => {
    if (votersFetched.current) return;
    votersFetched.current = true;
    try {
      const res = await fetch(`${API}/${path}/voters`, { headers: authHeaders() });
      if (res.ok) setVoters(await res.json());
    } catch { /* ignore */ }
  }, [path]);

  useEffect(() => {
    if (!initial) fetchTally();
  }, [initial, fetchTally]);

  useEffect(() => {
    if (initial) setTally(initial);
  }, [initial]);

  const cast = useCallback(async (want: 1 | -1) => {
    if (!canVote || pending) return;
    const prev = tally;
    const nextValue = tally.my_vote === want ? 0 : want;

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
      votersFetched.current = false;
    }
  }, [canVote, pending, tally, path]);

  const handleHoverUp = () => {
    setHoverUp(true);
    if (tally.up > 0 || tally.down > 0) fetchVoters();
  };
  const handleHoverDown = () => {
    setHoverDown(true);
    if (tally.up > 0 || tally.down > 0) fetchVoters();
  };

  const net = tally.up - tally.down;
  const btnBase = size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-1 text-xs';
  const iconCls = size === 'sm' ? 'w-2.5 h-2.5' : 'w-3 h-3';
  const containerCls = size === 'sm' ? 'gap-1' : 'gap-1.5';

  const disabledCls = canVote ? '' : 'opacity-60 cursor-not-allowed';
  const upActive = tally.my_vote === 1;
  const downActive = tally.my_vote === -1;

  const netColor = net > 0 ? 'text-emerald-600' : net < 0 ? 'text-rose-600' : 'text-slate-400';
  const netSize = size === 'sm' ? 'text-[10px]' : 'text-xs';

  return (
    <div
      className={`inline-flex items-center ${containerCls}`}
      onClick={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
      title={canVote ? undefined : 'Your role is view-only and cannot vote'}
    >
      <div
        className="relative"
        onMouseEnter={handleHoverUp}
        onMouseLeave={() => setHoverUp(false)}
      >
        <button
          type="button"
          onClick={() => cast(1)}
          disabled={!canVote || pending || loading}
          className={`${btnBase} rounded-lg font-black inline-flex items-center gap-1 transition-all ${disabledCls} ${
            upActive
              ? 'bg-emerald-100 text-emerald-700 shadow-sm shadow-emerald-200/50'
              : 'bg-slate-50 text-slate-500 hover:bg-emerald-50 hover:text-emerald-600'
          }`}
          aria-label="Upvote"
        >
          <ThumbsUp className={`${iconCls} transition-transform ${upActive ? 'scale-110' : ''}`} />
          <AnimatedCount value={tally.up} />
        </button>
        {hoverUp && voters && voters.up_voters.length > 0 && (
          <VoterPopup names={voters.up_voters.map(v => v.name)} />
        )}
      </div>
      <div
        className="relative"
        onMouseEnter={handleHoverDown}
        onMouseLeave={() => setHoverDown(false)}
      >
        <button
          type="button"
          onClick={() => cast(-1)}
          disabled={!canVote || pending || loading}
          className={`${btnBase} rounded-lg font-black inline-flex items-center gap-1 transition-all ${disabledCls} ${
            downActive
              ? 'bg-rose-100 text-rose-700 shadow-sm shadow-rose-200/50'
              : 'bg-slate-50 text-slate-500 hover:bg-rose-50 hover:text-rose-600'
          }`}
          aria-label="Downvote"
        >
          <ThumbsDown className={`${iconCls} transition-transform ${downActive ? 'scale-110' : ''}`} />
          <AnimatedCount value={tally.down} />
        </button>
        {hoverDown && voters && voters.down_voters.length > 0 && (
          <VoterPopup names={voters.down_voters.map(v => v.name)} />
        )}
      </div>
      {(tally.up > 0 || tally.down > 0) && (
        <span className={`${netSize} font-black ${netColor} min-w-[1.5em] text-center tabular-nums`} aria-label={`Net score: ${net}`}>
          <AnimatedCount value={net} className={netColor} />
        </span>
      )}
    </div>
  );
}
