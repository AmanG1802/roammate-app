'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { LayoutGrid, Map as MapIcon, Sparkles, ChevronLeft, Share2, ChevronDown } from 'lucide-react';
import { ProtectedRoute } from '@/hooks/useAuth';
import Timeline from '@/components/trip/Timeline';
import IdeaBin from '@/components/trip/IdeaBin';
import GoogleMap from '@/components/map/GoogleMap';
import Collaborators from '@/components/layout/Collaborators';
import ConciergeActionBar from '@/components/trip/ConciergeActionBar';
import { addDays, format, isToday, parseISO } from 'date-fns';

type Mode = 'plan' | 'concierge';

function buildTripDays(startDate: string | null, endDate: string | null): Date[] {
  if (!startDate) {
    // Default: 7-day trip starting today
    return Array.from({ length: 7 }, (_, i) => addDays(new Date(), i));
  }
  const start = parseISO(startDate);
  const end = endDate ? parseISO(endDate) : addDays(start, 6);
  const days: Date[] = [];
  let cur = start;
  while (cur <= end) {
    days.push(cur);
    cur = addDays(cur, 1);
  }
  return days;
}

export default function TripPlannerPage() {
  const searchParams = useSearchParams();
  const tripId = searchParams.get('id');
  const [trip, setTrip] = useState<any>(null);
  const [mode, setMode] = useState<Mode>('plan');
  const [selectedDayIdx, setSelectedDayIdx] = useState(0);

  useEffect(() => {
    if (!tripId) return;
    const fetchTrip = async () => {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setTrip(await res.json());
    };
    fetchTrip();
  }, [tripId]);

  const tripDays = useMemo(
    () => buildTripDays(trip?.start_date ?? null, trip?.end_date ?? null),
    [trip]
  );

  const selectedDay = tripDays[selectedDayIdx] ?? tripDays[0];
  const isCurrentDay = selectedDay ? isToday(selectedDay) : false;

  const sidebarBtn = (m: Mode, icon: React.ReactNode, label: string) => (
    <button
      onClick={() => setMode(m)}
      title={label}
      className={`flex flex-col items-center gap-1.5 p-3 rounded-2xl transition-all ${
        mode === m
          ? 'bg-white/15 text-white'
          : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
      }`}
    >
      {icon}
      <span className="text-[9px] font-black uppercase tracking-widest">{label}</span>
    </button>
  );

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-white overflow-hidden">
        {/* ── Icon sidebar ───────────────────────────────────────────────── */}
        <aside className="w-[72px] bg-slate-900 flex flex-col items-center py-6 gap-3 shrink-0 z-30">
          <Link
            href="/dashboard"
            className="w-11 h-11 bg-indigo-600 rounded-2xl flex items-center justify-center font-black text-white text-xl shadow-lg shadow-indigo-900/50 hover:scale-105 transition-transform mb-4"
          >
            R
          </Link>

          <nav className="flex flex-col gap-2 w-full px-2">
            {sidebarBtn('plan', <MapIcon className="w-5 h-5" />, 'Plan')}
            {sidebarBtn('concierge', <Sparkles className="w-5 h-5" />, 'Live')}
          </nav>

          <div className="mt-auto flex flex-col items-center gap-4 pb-2">
            <Link
              href="/dashboard"
              title="Dashboard"
              className="p-3 text-slate-500 hover:text-white transition-colors"
            >
              <LayoutGrid className="w-5 h-5" />
            </Link>
          </div>
        </aside>

        {/* ── Main area ──────────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <header className="h-16 border-b border-slate-100 flex items-center justify-between px-8 bg-white shrink-0">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="p-2 hover:bg-slate-50 rounded-xl transition-colors">
                <ChevronLeft className="w-5 h-5 text-slate-400" />
              </Link>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-lg font-black text-slate-900 tracking-tight">
                    {trip?.name ?? 'Loading…'}
                  </h1>
                  <span className={`px-2.5 py-0.5 text-[9px] font-black uppercase tracking-[0.2em] rounded-full border ${
                    mode === 'concierge'
                      ? 'bg-green-50 text-green-600 border-green-100'
                      : 'bg-indigo-50 text-indigo-600 border-indigo-100'
                  }`}>
                    {mode === 'plan' ? 'Planning' : 'Live Concierge'}
                  </span>
                </div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  {mode === 'plan' ? 'Full Itinerary View' : 'Day-by-Day View'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <Collaborators />
              <div className="w-px h-6 bg-slate-100" />
              <button className="flex items-center gap-2 px-4 py-2.5 bg-slate-900 text-white rounded-xl font-black text-sm hover:bg-indigo-600 transition-all">
                <Share2 className="w-4 h-4" />
                Invite
              </button>
            </div>
          </header>

          {/* ── Plan Mode ─────────────────────────────────────────────────── */}
          {mode === 'plan' && (
            <div className="flex-1 flex overflow-hidden bg-slate-50">
              {/* Timeline */}
              <div className="w-[420px] shrink-0 border-r border-slate-100 bg-white overflow-hidden flex flex-col">
                <Timeline tripId={tripId} />
              </div>
              {/* Map */}
              <div className="flex-1 relative">
                <GoogleMap />
              </div>
              {/* Idea Bin */}
              <div className="w-80 shrink-0 border-l border-slate-100 bg-white overflow-hidden flex flex-col">
                <IdeaBin tripId={tripId} />
              </div>
            </div>
          )}

          {/* ── Concierge / Live Mode ──────────────────────────────────────── */}
          {mode === 'concierge' && (
            <div className="flex-1 flex overflow-hidden">
              {/* Day Timeline */}
              <div className="w-[380px] shrink-0 border-r border-slate-100 bg-white overflow-hidden flex flex-col">
                {/* Day selector header */}
                <div className="px-6 pt-5 pb-4 border-b border-slate-50 shrink-0">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Select Day</p>
                  <div className="relative">
                    <select
                      value={selectedDayIdx}
                      onChange={(e) => setSelectedDayIdx(Number(e.target.value))}
                      className="w-full appearance-none pl-4 pr-10 py-2.5 bg-slate-50 border border-slate-100 rounded-xl text-sm font-black text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
                    >
                      {tripDays.map((day, idx) => (
                        <option key={idx} value={idx}>
                          Day {idx + 1} — {format(day, 'EEE, MMM d')}{isToday(day) ? ' (Today)' : ''}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                  </div>
                </div>
                <Timeline tripId={tripId} filterDay={selectedDay} />
              </div>

              {/* Map + optional concierge overlay */}
              <div className="flex-1 relative">
                <GoogleMap />
                {/* Concierge action bar — only on today */}
                {isCurrentDay && (
                  <ConciergeActionBar />
                )}
                {/* Future-day message */}
                {!isCurrentDay && selectedDay && (
                  <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 px-5 py-3 bg-white/80 backdrop-blur border border-slate-200 rounded-2xl shadow-lg">
                    <p className="text-xs font-black text-slate-500 uppercase tracking-widest">
                      Concierge activates on {format(selectedDay, 'EEE, MMM d')}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
