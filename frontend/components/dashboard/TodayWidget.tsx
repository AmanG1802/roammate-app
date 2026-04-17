'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { Calendar, Clock, MapPin, ChevronRight, Sparkles, Plane, History, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

type State = 'none' | 'pre_trip' | 'in_trip' | 'post_trip';

type TodayEvent = {
  id: number;
  title: string;
  location_name: string | null;
  start_time: string | null;
  end_time: string | null;
  is_next: boolean;
};

type TodayTrip = {
  id: number;
  name: string;
  start_date: string | null;
  end_date: string | null;
};

type TodayWidget = {
  state: State;
  trip: TodayTrip | null;
  days_until_start?: number | null;
  today_date?: string | null;
  today_events?: TodayEvent[];
  day_number?: number | null;
  total_days?: number | null;
  days_since_end?: number | null;
  total_events?: number | null;
};

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

export default function TodayWidget({ onNewTrip }: { onNewTrip: () => void }) {
  const [data, setData] = useState<TodayWidget | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/dashboard/today`, { headers: authHeaders() });
      if (res.ok) setData(await res.json());
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    load();
    const onFocus = () => load();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [load]);

  if (loading) {
    return (
      <div className="rounded-[2rem] border border-slate-100 bg-white p-8 mb-8 flex items-center justify-center min-h-[180px]">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (!data || data.state === 'none' || !data.trip) {
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

  if (data.state === 'pre_trip') return <PreTripCard data={data} />;
  if (data.state === 'in_trip') return <InTripCard data={data} />;
  if (data.state === 'post_trip') return <PostTripCard data={data} />;
  return null;
}

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
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-[2rem] border border-slate-100 bg-gradient-to-br ${toneMap[tone]} p-8 mb-8 shadow-sm`}
    >
      <div className="flex items-center gap-2 text-xs font-black uppercase tracking-widest mb-3">
        {badgeIcon} {badge}
      </div>
      {children}
    </motion.div>
  );
}

function PreTripCard({ data }: { data: TodayWidget }) {
  const days = data.days_until_start ?? 0;
  const trip = data.trip!;
  const startLabel = trip.start_date
    ? new Date(trip.start_date).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
    : 'TBD';
  return (
    <HeroShell badge={days <= 0 ? 'Trip Day' : `${days} day${days === 1 ? '' : 's'} to go`} badgeIcon={<Plane className="w-3.5 h-3.5 -rotate-45" />} tone="indigo">
      <div className="flex items-end justify-between flex-wrap gap-6">
        <div>
          <h2 className="text-3xl font-black text-slate-900 mb-1 leading-tight">{trip.name}</h2>
          <div className="flex items-center gap-2 text-slate-500 text-sm font-bold">
            <Calendar className="w-4 h-4" />
            {startLabel}
          </div>
        </div>
        <Link
          href={`/trips/${trip.id}`}
          className="inline-flex items-center gap-2 px-5 py-3 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100"
        >
          Plan Itinerary <ChevronRight className="w-4 h-4" />
        </Link>
      </div>
    </HeroShell>
  );
}

function InTripCard({ data }: { data: TodayWidget }) {
  const trip = data.trip!;
  const events = data.today_events ?? [];
  const next = events.find((e) => e.is_next) ?? null;
  const dayLabel = data.day_number && data.total_days
    ? `Day ${data.day_number} of ${data.total_days}`
    : data.day_number ? `Day ${data.day_number}` : 'Today';

  return (
    <HeroShell badge={dayLabel} badgeIcon={<Sparkles className="w-3.5 h-3.5" />} tone="amber">
      <div className="flex items-start justify-between gap-6 mb-5">
        <div>
          <h2 className="text-3xl font-black text-slate-900 mb-1 leading-tight">{trip.name}</h2>
          <p className="text-slate-500 text-sm font-bold">
            {events.length === 0
              ? 'No events scheduled today.'
              : `${events.length} event${events.length === 1 ? '' : 's'} on deck.`}
          </p>
        </div>
        <Link
          href={`/trips/${trip.id}`}
          className="inline-flex items-center gap-2 px-5 py-3 bg-slate-900 text-white rounded-xl font-black text-sm hover:bg-indigo-600 transition-all shrink-0"
        >
          Open Trip <ChevronRight className="w-4 h-4" />
        </Link>
      </div>

      {next && (
        <div className="bg-white rounded-2xl border border-amber-100 p-4 mb-3 shadow-sm">
          <div className="text-[10px] font-black text-amber-600 uppercase tracking-widest mb-1">Up Next</div>
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="font-black text-slate-900 truncate">{next.title}</p>
              {next.location_name && (
                <div className="flex items-center gap-1 text-xs text-slate-500 font-bold mt-0.5 truncate">
                  <MapPin className="w-3 h-3" /> {next.location_name}
                </div>
              )}
            </div>
            {next.start_time && (
              <div className="flex items-center gap-1 text-sm text-slate-700 font-black shrink-0">
                <Clock className="w-3.5 h-3.5" /> {formatTime(next.start_time)}
              </div>
            )}
          </div>
        </div>
      )}

      {events.length > 0 && (
        <div className="space-y-1">
          {events.map((e) => (
            <div
              key={e.id}
              className={`flex items-center justify-between gap-4 px-3 py-2 rounded-xl ${
                e.is_next ? 'bg-white/60' : 'hover:bg-white/40'
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className={`w-1.5 h-1.5 rounded-full ${e.is_next ? 'bg-amber-500' : 'bg-slate-300'}`} />
                <span className="font-bold text-slate-700 text-sm truncate">{e.title}</span>
              </div>
              <span className="text-xs text-slate-400 font-bold shrink-0">{formatTime(e.start_time)}</span>
            </div>
          ))}
        </div>
      )}
    </HeroShell>
  );
}

function PostTripCard({ data }: { data: TodayWidget }) {
  const trip = data.trip!;
  const days = data.days_since_end ?? 0;
  return (
    <HeroShell badge={`Wrapped ${days} day${days === 1 ? '' : 's'} ago`} badgeIcon={<History className="w-3.5 h-3.5" />} tone="rose">
      <div className="flex items-end justify-between gap-6 flex-wrap">
        <div>
          <h2 className="text-3xl font-black text-slate-900 mb-1 leading-tight">{trip.name}</h2>
          <p className="text-slate-500 text-sm font-bold">
            {data.total_events ?? 0} memories captured across {data.total_days ?? '—'} days.
          </p>
        </div>
        <Link
          href={`/trips/${trip.id}`}
          className="inline-flex items-center gap-2 px-5 py-3 bg-rose-600 text-white rounded-xl font-black text-sm hover:bg-rose-700 transition-all shadow-lg shadow-rose-100"
        >
          See Recap <ChevronRight className="w-4 h-4" />
        </Link>
      </div>
    </HeroShell>
  );
}
