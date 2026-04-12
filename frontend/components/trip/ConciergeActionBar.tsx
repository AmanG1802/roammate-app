'use client';

import { useState } from 'react';
import { useTripStore } from '@/lib/store';
import { Clock, SkipForward, Coffee, MessageSquare, Loader2, ChevronDown } from 'lucide-react';

const LATE_OPTIONS = [15, 30, 60];

export default function ConciergeActionBar() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showLateMenu, setShowLateMenu] = useState(false);
  const { activeTripId, events, setEvents } = useTripStore();

  const handleRunningLate = async (minutes: number) => {
    setShowLateMenu(false);
    if (!activeTripId || events.length === 0) return;
    setIsProcessing(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/events/ripple/${activeTripId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            delta_minutes: minutes,
            start_from_time: new Date().toISOString(),
          }),
        }
      );
      if (res.ok) {
        const updated = await res.json();
        setEvents(
          updated.map((e: any) => ({
            ...e,
            start_time: new Date(e.start_time),
            end_time: new Date(e.end_time),
          }))
        );
      } else {
        // Optimistic local shift if API not yet wired
        setEvents(
          events.map((e) => ({
            ...e,
            start_time: new Date(e.start_time.getTime() + minutes * 60_000),
            end_time: new Date(e.end_time.getTime() + minutes * 60_000),
          }))
        );
      }
    } catch {
      // Fallback: optimistic local shift
      setEvents(
        events.map((e) => ({
          ...e,
          start_time: new Date(e.start_time.getTime() + minutes * 60_000),
          end_time: new Date(e.end_time.getTime() + minutes * 60_000),
        }))
      );
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 p-2 bg-white/85 backdrop-blur-md border border-slate-200 rounded-2xl shadow-2xl">
      {/* Running Late */}
      <div className="relative">
        <button
          onClick={() => setShowLateMenu((v) => !v)}
          disabled={isProcessing || events.length === 0}
          className="flex items-center gap-2 px-4 py-2.5 bg-rose-50 text-rose-600 rounded-xl font-bold text-sm hover:bg-rose-100 transition-colors disabled:opacity-40"
        >
          {isProcessing ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Clock className="w-4 h-4" />
          )}
          Running Late
          <ChevronDown className="w-3.5 h-3.5" />
        </button>
        {showLateMenu && (
          <div className="absolute bottom-full mb-2 left-0 bg-white border border-slate-100 rounded-xl shadow-xl overflow-hidden min-w-[130px]">
            {LATE_OPTIONS.map((min) => (
              <button
                key={min}
                onClick={() => handleRunningLate(min)}
                className="w-full text-left px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-rose-50 hover:text-rose-600 transition-colors"
              >
                +{min} min
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="w-px h-6 bg-slate-200" />

      <button
        title="Skip Next"
        className="p-2.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors"
      >
        <SkipForward className="w-4 h-4" />
      </button>

      <button
        title="Find Coffee"
        className="p-2.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors"
      >
        <Coffee className="w-4 h-4" />
      </button>

      <div className="w-px h-6 bg-slate-200" />

      <button className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-xl font-bold text-sm hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200">
        <MessageSquare className="w-4 h-4" />
        Chat Now
      </button>
    </div>
  );
}
