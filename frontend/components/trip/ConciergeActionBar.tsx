'use client';

import { useState } from 'react';
import { useTripStore } from '@/lib/store';
import { Clock, SkipForward, Coffee, MessageSquare, Loader2, ChevronDown, Check } from 'lucide-react';
import ConciergeChatDrawer from './ConciergeChatDrawer';

const LATE_OPTIONS = [15, 30, 60];

export default function ConciergeActionBar() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showLateMenu, setShowLateMenu] = useState(false);
  const [rippleToast, setRippleToast] = useState<string | null>(null);
  const {
    activeTripId, events, setEvents, loadEvents,
    conciergeOpen, conciergePreAction, openConcierge, closeConcierge,
  } = useTripStore();

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
        const msg = updated.length > 0
          ? `Shifted ${updated.length} event${updated.length > 1 ? 's' : ''} by +${minutes} min`
          : 'No events needed adjustment';
        setRippleToast(msg);
        setTimeout(() => setRippleToast(null), 3000);
      }
    } catch {
      // Fallback: optimistic local shift
      setEvents(
        events.map((e) => ({
          ...e,
          start_time: e.start_time ? new Date(e.start_time.getTime() + minutes * 60_000) : null,
          end_time: e.end_time ? new Date(e.end_time.getTime() + minutes * 60_000) : null,
        }))
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSkipNext = () => {
    const now = new Date();
    const nextEvent = events.find(
      (e) => e.start_time && !e.is_skipped && (e.start_time > now || (e.end_time && e.end_time > now))
    );
    if (!nextEvent) return;

    openConcierge({
      type: 'skip_next',
      payload: { eventId: Number(nextEvent.id), eventTitle: nextEvent.title },
    });
  };

  const handleFindCoffee = () => {
    openConcierge({ type: 'find_coffee' });
  };

  const handleChatNow = () => {
    openConcierge(null);
  };

  return (
    <>
      {rippleToast && (
        <div className="absolute bottom-24 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2 px-4 py-2.5 bg-emerald-600 text-white rounded-xl font-medium text-sm shadow-lg animate-in fade-in slide-in-from-bottom-2 duration-300">
          <Check className="w-4 h-4" />
          {rippleToast}
        </div>
      )}
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
          onClick={handleSkipNext}
          disabled={!events.some((e) => e.start_time && !e.is_skipped && (e.start_time > new Date() || (e.end_time && e.end_time > new Date())))}
          className="p-2.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors disabled:opacity-30"
        >
          <SkipForward className="w-4 h-4" />
        </button>

        <button
          title="Find Coffee"
          onClick={handleFindCoffee}
          className="p-2.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors"
        >
          <Coffee className="w-4 h-4" />
        </button>

        <div className="w-px h-6 bg-slate-200" />

        <button
          onClick={handleChatNow}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-xl font-bold text-sm hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200 active:scale-[0.98]"
        >
          <MessageSquare className="w-4 h-4" />
          Chat Now
        </button>
      </div>

      <ConciergeChatDrawer
        isOpen={conciergeOpen}
        onClose={closeConcierge}
        preAction={conciergePreAction}
      />
    </>
  );
}
