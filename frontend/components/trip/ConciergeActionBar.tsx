'use client';

import { useEffect, useRef, useState } from 'react';
import { useTripStore, Event } from '@/lib/store';
import { getToken } from '@/lib/auth';
import { toastBus } from '@/lib/toast-bus';
import { combineInTz } from '@/lib/time';
import { Clock, SkipForward, Coffee, MessageSquare, Loader2, ChevronDown, Check, Sparkles } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useEntitlement } from '@/hooks/useEntitlement';
const ConciergeChatDrawer = dynamic(() => import('./ConciergeChatDrawer'), { ssr: false });

const LATE_OPTIONS = [15, 30, 60];

export default function ConciergeActionBar() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showLateMenu, setShowLateMenu] = useState(false);
  const [rippleToast, setRippleToast] = useState<string | null>(null);
  const rippleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (rippleTimerRef.current) clearTimeout(rippleTimerRef.current);
    };
  }, []);

  const {
    activeTripId, events, setEvents, loadEvents,
    conciergeOpen, conciergePreAction, openConcierge, closeConcierge,
  } = useTripStore();

  const { entitlement, requirePlus } = useEntitlement();
  const conciergeLocked = !entitlement.can_use_concierge;

  const gateConcierge = async (run: () => void) => {
    if (!conciergeLocked) { run(); return; }
    const ok = await requirePlus('concierge');
    if (ok) run();
  };

  const handleRunningLate = async (minutes: number) => {
    setShowLateMenu(false);
    if (!activeTripId || events.length === 0) return;
    setIsProcessing(true);
    try {
      const token = getToken();
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
        // Backend returns TIME-only strings ("HH:MM:SS") — pass through.
        setEvents(updated as Event[]);
        const msg = updated.length > 0
          ? `Shifted ${updated.length} event${updated.length > 1 ? 's' : ''} by +${minutes} min`
          : 'No events needed adjustment';
        setRippleToast(msg);
        if (rippleTimerRef.current) clearTimeout(rippleTimerRef.current);
        rippleTimerRef.current = setTimeout(() => setRippleToast(null), 3000);
      } else {
        toastBus("Couldn't shift schedule — please try again", { kind: 'error' });
      }
    } catch {
      toastBus('Network error — schedule not updated', { kind: 'error' });
    } finally {
      setIsProcessing(false);
    }
  };

  // ConciergeActionBar is used "in the moment"; we don't have Trip.timezone
  // wired into the store yet, so fall back to the browser tz. This is right
  // when the user is physically in the trip's tz (typical "Running Late"
  // / "Skip Next" usage). If the user opens the app from a different tz,
  // the check will be off — acceptable for the action-bar quick decisions.
  const browserTz = typeof Intl !== 'undefined'
    ? Intl.DateTimeFormat().resolvedOptions().timeZone
    : 'UTC';

  const isStillUpcoming = (e: Event, now: Date): boolean => {
    const start = combineInTz(e.day_date, e.start_time, browserTz);
    const end = combineInTz(e.day_date, e.end_time, browserTz);
    if (!start) return false;
    if (start > now) return true;
    return !!(end && end > now);
  };

  const handleSkipNext = () => {
    const now = new Date();
    const nextEvent = events.find(
      (e) => e.start_time && !e.is_skipped && isStillUpcoming(e, now),
    );
    if (!nextEvent) return;

    gateConcierge(() => openConcierge({
      type: 'skip_next',
      payload: { eventId: Number(nextEvent.id), eventTitle: nextEvent.title },
    }));
  };

  const handleFindCoffee = () => {
    gateConcierge(() => openConcierge({ type: 'find_coffee' }));
  };

  const handleChatNow = () => {
    gateConcierge(() => openConcierge(null));
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
            className="flex items-center gap-2 px-4 py-2.5 bg-rose-50 text-rose-600 rounded-xl font-bold text-sm hover:bg-rose-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]"
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
          aria-label="Skip next event"
          onClick={handleSkipNext}
          disabled={!events.some((e) => e.start_time && !e.is_skipped && isStillUpcoming(e, new Date()))}
          className="p-2.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors disabled:opacity-30 disabled:cursor-not-allowed active:scale-95"
        >
          <SkipForward className="w-4 h-4" />
        </button>

        <button
          title="Find Coffee"
          aria-label="Find coffee nearby"
          onClick={handleFindCoffee}
          className="p-2.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors active:scale-95"
        >
          <Coffee className="w-4 h-4" />
        </button>

        <div className="w-px h-6 bg-slate-200" />

        <button
          onClick={handleChatNow}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm transition-all active:scale-[0.98] ${
            conciergeLocked
              ? 'text-white shadow-lg'
              : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg shadow-indigo-200'
          }`}
          style={
            conciergeLocked
              ? {
                  backgroundImage: 'linear-gradient(135deg, #4F46E5 0%, #D946EF 55%, #F59E0B 100%)',
                  boxShadow: '0 8px 24px -8px rgba(79, 70, 229, 0.55)',
                }
              : undefined
          }
        >
          {conciergeLocked ? <Sparkles className="w-4 h-4" /> : <MessageSquare className="w-4 h-4" />}
          {conciergeLocked ? 'Unlock Concierge' : 'Chat Now'}
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
