'use client';

import { useEffect, useState, useCallback, useImperativeHandle, forwardRef } from 'react';
import Link from 'next/link';
import { Calendar, Clock, MapPin, ChevronRight, ChevronLeft, Sparkles, Plane, History, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type TodayEvent = {
  id: number;
  title: string;
  location_name: string | null;
  start_time: string | null;
  end_time: string | null;
  is_next: boolean;
  is_ongoing: boolean;
};

type TodayTrip = {
  id: number;
  name: string;
  start_date: string | null;
  end_date: string | null;
};

type Page = {
  state: 'pre_trip' | 'in_trip' | 'post_trip';
  trip: TodayTrip;
  days_until_start?: number | null;
  today_date?: string | null;
  today_events?: TodayEvent[];
  day_number?: number | null;
  total_days?: number | null;
  days_since_end?: number | null;
  total_events?: number | null;
};

type WidgetData = {
  pages: Page[];
  default_index: number;
};

export type TodayWidgetHandle = { refresh: () => void };

const API = process.env.NEXT_PUBLIC_API_URL ?? '';

function authHeaders(): Record<string, string> {
  const t = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  return t ? { Authorization: `Bearer ${t}` } : {};
}

function formatTime(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

const TodayWidget = forwardRef<TodayWidgetHandle, { onNewTrip: () => void }>(
  function TodayWidget({ onNewTrip }, ref) {
    const [data, setData] = useState<WidgetData | null>(null);
    const [loading, setLoading] = useState(true);
    const [pageIdx, setPageIdx] = useState(0);
    const [direction, setDirection] = useState(0);

    const load = useCallback(async () => {
      try {
        const now = new Date();
        const pad = (n: number) => String(n).padStart(2, '0');
        const localISO = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
        const res = await fetch(`${API}/dashboard/today?client_now=${encodeURIComponent(localISO)}`, { headers: authHeaders() });
        if (res.ok) {
          const d: WidgetData = await res.json();
          setData(d);
          setPageIdx(d.default_index);
        }
      } catch { /* ignore */ }
      finally { setLoading(false); }
    }, []);

    useImperativeHandle(ref, () => ({ refresh: load }), [load]);

    useEffect(() => {
      load();
      const onFocus = () => load();
      window.addEventListener('focus', onFocus);
      return () => window.removeEventListener('focus', onFocus);
    }, [load]);

    const goPrev = useCallback(() => {
      setDirection(-1);
      setPageIdx((i) => Math.max(0, i - 1));
    }, []);

    const goNext = useCallback(() => {
      if (!data) return;
      setDirection(1);
      setPageIdx((i) => Math.min(data.pages.length - 1, i + 1));
    }, [data]);

    if (loading) {
      return (
        <div className="rounded-[2rem] border border-slate-100 bg-white p-8 mb-8 flex items-center justify-center min-h-[180px]">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      );
    }

    if (!data || data.pages.length === 0) {
      return (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-[2rem] border border-dashed border-slate-200 bg-white p-8 mb-8 flex items-center justify-between"
        >
          <div>
            <div className="flex items-center gap-2 text-xs font-black text-indigo-500 uppercase tracking-widest mb-2">
              <Sparkles className="w-3.5 h-3.5" /> Today
            </div>
            <h3 className="text-2xl font-black text-slate-900 mb-1">Nothing on the horizon yet.</h3>
            <p className="text-slate-500 font-medium">Spin up your first trip and the dashboard will come alive.</p>
          </div>
          <button
            onClick={onNewTrip}
            className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100"
          >
            Plan a Trip
          </button>
        </motion.div>
      );
    }

    const safeIdx = Math.min(pageIdx, data.pages.length - 1);
    const page = data.pages[safeIdx];
    const hasPrev = safeIdx > 0;
    const hasNext = safeIdx < data.pages.length - 1;
    const totalPages = data.pages.length;

    return (
      <div className="relative mb-8">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={`${page.trip.id}-${page.state}`}
            custom={direction}
            initial={{ opacity: 0, x: direction * 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: direction * -40 }}
            transition={{ duration: 0.2 }}
          >
            {page.state === 'pre_trip' && <PreTripCard page={page} />}
            {page.state === 'in_trip' && <InTripCard page={page} />}
            {page.state === 'post_trip' && <PostTripCard page={page} />}
          </motion.div>
        </AnimatePresence>

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 -mt-4 pb-2 relative z-10">
            <button
              onClick={goPrev}
              disabled={!hasPrev}
              className="w-8 h-8 flex items-center justify-center rounded-full bg-white border border-slate-200 text-slate-400 hover:text-slate-700 hover:border-slate-300 transition-all disabled:opacity-30 disabled:cursor-not-allowed shadow-sm"
              title="Previous trip"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-1.5">
              {data.pages.map((_, i) => (
                <button
                  key={i}
                  onClick={() => { setDirection(i > safeIdx ? 1 : -1); setPageIdx(i); }}
                  className={`w-1.5 h-1.5 rounded-full transition-all ${
                    i === safeIdx ? 'bg-slate-700 w-4' : 'bg-slate-300 hover:bg-slate-400'
                  }`}
                />
              ))}
            </div>
            <button
              onClick={goNext}
              disabled={!hasNext}
              className="w-8 h-8 flex items-center justify-center rounded-full bg-white border border-slate-200 text-slate-400 hover:text-slate-700 hover:border-slate-300 transition-all disabled:opacity-30 disabled:cursor-not-allowed shadow-sm"
              title="Next trip"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    );
  }
);

export default TodayWidget;


function HeroShell({
  badge,
  badgeIcon,
  tone = 'indigo',
  children,
}: {
  badge: string;
  badgeIcon: React.ReactNode;
  tone?: 'indigo' | 'amber' | 'rose';
  children: React.ReactNode;
}) {
  const toneMap = {
    indigo: 'from-indigo-50 to-white text-indigo-600',
    amber: 'from-amber-50 to-white text-amber-600',
    rose: 'from-rose-50 to-white text-rose-600',
  } as const;
  return (
    <div
      className={`rounded-3xl border border-slate-100 bg-gradient-to-br ${toneMap[tone]} p-5 pb-6 shadow-sm min-h-[340px] flex flex-col`}
    >
      <div className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest mb-2">
        {badgeIcon} {badge}
      </div>
      {children}
    </div>
  );
}

type SlotKind = 'ongoing' | 'next' | 'upcoming';

function EventSlot({ event, kind }: { event: TodayEvent | null; kind: SlotKind }) {
  if (!event) {
    return (
      <div className="bg-white/50 rounded-xl border border-dashed border-slate-200 px-3 h-[60px] flex items-center justify-center">
        <p className="text-xs font-bold text-slate-400">Day's all yours from here.</p>
      </div>
    );
  }
  const styles = {
    ongoing: { border: 'border-emerald-100', label: 'Ongoing', labelColor: 'text-emerald-600' },
    next: { border: 'border-amber-100', label: 'Up Next', labelColor: 'text-amber-600' },
    upcoming: { border: 'border-slate-100', label: 'Coming Up', labelColor: 'text-slate-500' },
  }[kind];

  const timeLabel =
    kind === 'ongoing' && event.start_time && event.end_time
      ? `${formatTime(event.start_time)} – ${formatTime(event.end_time)}`
      : event.start_time
        ? formatTime(event.start_time)
        : '';

  return (
    <div className={`bg-white rounded-xl border ${styles.border} px-3 py-2 h-[60px] shadow-sm`}>
      <div className={`text-[9px] font-black ${styles.labelColor} uppercase tracking-widest leading-none`}>
        {styles.label}
      </div>
      <div className="flex items-center justify-between gap-3 mt-0.5">
        <div className="min-w-0">
          <p className="font-black text-slate-900 text-sm truncate leading-tight">{event.title}</p>
          {event.location_name && (
            <div className="flex items-center gap-1 text-[11px] text-slate-500 font-bold truncate leading-tight">
              <MapPin className="w-2.5 h-2.5" /> {event.location_name}
            </div>
          )}
        </div>
        {timeLabel && (
          <div className="flex items-center gap-1 text-xs text-slate-700 font-black shrink-0">
            <Clock className="w-3 h-3" /> {timeLabel}
          </div>
        )}
      </div>
    </div>
  );
}

function PreTripCard({ page }: { page: Page }) {
  const days = page.days_until_start ?? 0;
  const trip = page.trip;
  const startLabel = trip.start_date
    ? new Date(trip.start_date).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
    : 'TBD';
  return (
    <HeroShell badge={days <= 0 ? 'Trip Day' : `${days} day${days === 1 ? '' : 's'} to go`} badgeIcon={<Plane className="w-3.5 h-3.5 -rotate-45" />} tone="indigo">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-xl font-black text-slate-900 mb-1 leading-tight">{trip.name}</h2>
          <div className="flex items-center gap-1.5 text-slate-500 text-xs font-bold">
            <Calendar className="w-3.5 h-3.5" />
            {startLabel}
          </div>
        </div>
        <Link
          href={`/trips/${trip.id}`}
          className="inline-flex items-center gap-1.5 px-3 py-2 bg-indigo-600 text-white rounded-lg font-black text-xs hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100"
        >
          Plan Itinerary <ChevronRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </HeroShell>
  );
}

function InTripCard({ page }: { page: Page }) {
  const trip = page.trip;
  const events = page.today_events ?? [];
  const ongoingIdx = events.findIndex((e) => e.is_ongoing);
  const ongoing = ongoingIdx >= 0 ? events[ongoingIdx] : null;
  const nextIdx = events.findIndex((e) => e.is_next && !e.is_ongoing);
  const upcomingStart = nextIdx >= 0 ? nextIdx : ongoingIdx >= 0 ? ongoingIdx + 1 : 0;
  const upcoming = events.slice(upcomingStart).filter((e) => !e.is_ongoing);

  const slots: Array<{ event: TodayEvent | null; kind: SlotKind }> = ongoing
    ? [
        { event: ongoing, kind: 'ongoing' },
        { event: upcoming[0] ?? null, kind: 'next' },
        { event: upcoming[1] ?? null, kind: 'upcoming' },
      ]
    : [
        { event: upcoming[0] ?? null, kind: 'next' },
        { event: upcoming[1] ?? null, kind: 'upcoming' },
        { event: upcoming[2] ?? null, kind: 'upcoming' },
      ];

  const dayLabel = page.day_number && page.total_days
    ? `Day ${page.day_number} of ${page.total_days}`
    : page.day_number ? `Day ${page.day_number}` : 'Today';

  return (
    <HeroShell badge={dayLabel} badgeIcon={<Sparkles className="w-3.5 h-3.5" />} tone="amber">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <h2 className="text-xl font-black text-slate-900 mb-0.5 leading-tight">{trip.name}</h2>
          <p className="text-slate-500 text-xs font-bold">
            {events.length === 0
              ? 'No events scheduled today.'
              : `${events.length} event${events.length === 1 ? '' : 's'} on deck.`}
          </p>
        </div>
        <Link
          href={`/trips/${trip.id}`}
          className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-900 text-white rounded-lg font-black text-xs hover:bg-indigo-600 transition-all shrink-0"
        >
          Open Trip <ChevronRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="space-y-2">
        {slots.map((s, i) => (
          <EventSlot key={s.event ? s.event.id : `empty-${i}`} event={s.event} kind={s.kind} />
        ))}
      </div>
    </HeroShell>
  );
}

function PostTripCard({ page }: { page: Page }) {
  const trip = page.trip;
  const days = page.days_since_end ?? 0;
  return (
    <HeroShell badge={`Wrapped ${days} day${days === 1 ? '' : 's'} ago`} badgeIcon={<History className="w-3.5 h-3.5" />} tone="rose">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-black text-slate-900 mb-0.5 leading-tight">{trip.name}</h2>
          <p className="text-slate-500 text-xs font-bold">
            {page.total_events ?? 0} memories captured across {page.total_days ?? '—'} days.
          </p>
        </div>
        <Link
          href={`/trips/${trip.id}`}
          className="inline-flex items-center gap-1.5 px-3 py-2 bg-rose-600 text-white rounded-lg font-black text-xs hover:bg-rose-700 transition-all shadow-lg shadow-rose-100"
        >
          See Recap <ChevronRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </HeroShell>
  );
}
