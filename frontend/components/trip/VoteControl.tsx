'use client';

import { useCallback, useEffect, useRef, useState, memo } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { api } from '@/lib/api';

type Kind = 'idea' | 'event';

type Tally = { up: number; down: number; my_vote: number };
type VoterList = { up_voters: { name: string; avatar_url?: string | null }[]; down_voters: { name: string; avatar_url?: string | null }[] };

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

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 1).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function VoterPopup({ voters }: { voters: { name: string; avatar_url?: string | null }[] }) {
  if (voters.length === 0) return null;
  const shown = voters.length <= 4 ? voters : voters.slice(0, 3);
  const extra = voters.length <= 4 ? 0 : voters.length - 3;
  return (
    <div role="tooltip" aria-hidden="true" className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 z-50 pointer-events-none">
      <div className="bg-white border border-slate-200 rounded-full shadow-lg px-1.5 py-1 flex items-center gap-1">
        {shown.map((v, i) => (
          <div
            key={i}
            title={v.name}
            className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-[9px] font-black flex items-center justify-center overflow-hidden shrink-0"
          >
            {v.avatar_url
              ? <img src={v.avatar_url} alt={v.name} className="w-full h-full object-cover" />
              : initialsOf(v.name)
            }
          </div>
        ))}
        {extra > 0 && (
          <div className="w-5 h-5 rounded-full bg-indigo-600 text-white text-[9px] font-black flex items-center justify-center">
            +{extra}
          </div>
        )}
      </div>
    </div>
  );
}

function VoteControl({
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
  const prevInitial = useRef(initial);

  const path = kind === 'idea' ? `ideas/${id}` : `events/${id}`;

  const fetchTally = useCallback(async () => {
    try {
      const data = await api<Tally>(`/api/${path}/votes`);
      setTally(data);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [path]);

  const fetchVoters = useCallback(async () => {
    if (votersFetched.current) return;
    votersFetched.current = true;
    try {
      const data = await api<VoterList>(`/api/${path}/voters`);
      setVoters(data);
    } catch { /* ignore */ }
  }, [path]);

  useEffect(() => {
    if (!initial) fetchTally();
  }, [initial, fetchTally]);

  useEffect(() => {
    votersFetched.current = false;
    setVoters(null);
  }, [path]);

  // Sync from parent only when the actual values change (not just object reference).
  // Prevents hover-driven re-renders in Timeline from resetting the optimistic update.
  useEffect(() => {
    if (!initial) return;
    const prev = prevInitial.current;
    prevInitial.current = initial;
    if (prev && prev.up === initial.up && prev.down === initial.down && prev.my_vote === initial.my_vote) return;
    setTally(initial);
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
      const data = await api<Tally>(`/api/${path}/vote`, {
        method: 'POST',
        json: { value: nextValue },
      });
      setTally(data);
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
          <VoterPopup voters={voters.up_voters} />
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
          <VoterPopup voters={voters.down_voters} />
        )}
      </div>
    </div>
  );
}

export default memo(VoteControl, (prev, next) =>
  prev.kind === next.kind &&
  prev.id === next.id &&
  prev.canVote === next.canVote &&
  prev.size === next.size &&
  prev.initial?.up === next.initial?.up &&
  prev.initial?.down === next.initial?.down &&
  prev.initial?.my_vote === next.initial?.my_vote
);
