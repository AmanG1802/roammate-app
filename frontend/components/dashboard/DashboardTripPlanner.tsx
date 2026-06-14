'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, Loader2, Rocket, X, Compass, AlertTriangle } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { isNeedsPlus, useEntitlement } from '@/hooks/useEntitlement';
import { useTutorial } from '@/hooks/useTutorial';
import VoiceInputButton from '@/components/common/VoiceInputButton';

// Witty messages shown while the AI is planning. Cycled every ~1.8s so the
// user has something to read instead of a static spinner.
const PLANNING_MESSAGES = [
  'Consulting our travel guides…',
  'Sketching the perfect itinerary…',
  'Asking locals where to eat…',
  'Mapping out the route…',
  'Negotiating with the weather…',
  'Hunting for hidden gems…',
  'Booking imaginary llamas…',
  'Pinning the must-sees…',
];

type EnrichmentStatus = {
  status: 'full' | 'partial' | 'none';
  total: number;
  enriched: number;
  skipped: number;
  reason?: string | null;
};

type Preview = {
  trip_name: string;
  start_date: string | null;
  duration_days: number;
  items: Array<Record<string, any>>;
  enrichment?: EnrichmentStatus | null;
  user_output?: string;
  /** IANA tz inferred from the destination on the backend. Null → fall back to browser tz. */
  timezone?: string | null;
  destination_city?: string | null;
  country_code?: string | null;
  destination_lat?: number | null;
  destination_lng?: number | null;
};

type BufferedMessage = { role: 'user' | 'assistant'; content: string };

// Canned preview used by the tutorial demo — mirrors the seeded backend
// fixture so the screen reads as a real planner output.
const CANNED_NYC_PREVIEW: Preview = {
  trip_name: 'New York and its Skylines',
  start_date: null,
  duration_days: 3,
  destination_city: 'New York',
  country_code: 'US',
  timezone: 'America/New_York',
  user_output:
    "Three days in NYC: anchor Day 1 in Midtown (Times Square + MoMA), Day 2 in Central Park + Brooklyn Bridge at sunset, Day 3 around the Village with a Joe's Pizza stop.",
  items: [
    { title: 'Times Square', category: 'landmark', time_category: 'morning' },
    { title: 'Museum of Modern Art', category: 'museum', time_category: 'afternoon' },
    { title: 'Central Park Picnic', category: 'park', time_category: 'midday' },
    { title: 'Brooklyn Bridge Sunset Walk', category: 'landmark', time_category: 'evening' },
    { title: "Joe's Pizza", category: 'restaurant', time_category: 'midday' },
  ],
  enrichment: { status: 'full', total: 5, enriched: 5, skipped: 0 },
};

export default function DashboardTripPlanner({ onTripCreated }: { onTripCreated?: () => void }) {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [preview, setPreview] = useState<Preview | null>(null);
  const [planning, setPlanning] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [witIdx, setWitIdx] = useState(0);
  // Buffer the user prompts + assistant user_output replies so we can backfill
  // them into the new trip's Brainstorm chat history after createTrip succeeds.
  const planMessagesRef = useRef<BufferedMessage[]>([]);
  const { requirePlus, refresh: refreshEntitlement } = useEntitlement();
  const tutorial = useTutorial();
  /** True while we're running the canned planning simulation for the tutorial. */
  const [tutorialDemoActive, setTutorialDemoActive] = useState(false);
  /** Briefly flashes the Plan button to draw the eye after auto-fill. */
  const [planButtonPulse, setPlanButtonPulse] = useState(false);

  // ── Tutorial demo flow ──────────────────────────────────────────────
  // When the tutorial fires `tutorial:plan-demo`, we simulate a full
  // plan-trip turn without touching the LLM: type out a sample prompt,
  // flash the Plan button, sit on the planning overlay for ~3s, then drop
  // in a canned NYC preview keyed to the user's already-seeded tutorial trip.
  useEffect(() => {
    function onDemo() {
      runTutorialPlanDemo();
    }
    window.addEventListener('tutorial:plan-demo', onDemo as EventListener);
    return () => window.removeEventListener('tutorial:plan-demo', onDemo as EventListener);
  }, []);

  const runTutorialPlanDemo = () => {
    setTutorialDemoActive(true);
    setError(null);
    setPreview(null);

    // 1. Typewriter-fill the prompt so it feels alive (~14ms/char).
    const sample = 'A 3-day New York City trip with iconic landmarks, food, and parks';
    setPrompt('');
    let i = 0;
    const tickType = window.setInterval(() => {
      i += 1;
      setPrompt(sample.slice(0, i));
      if (i >= sample.length) window.clearInterval(tickType);
    }, 18);

    // 2. After typing finishes, pulse the Plan button, then enter the
    //    planning state for ~3s, then show the canned preview.
    const totalTyping = sample.length * 18 + 200;
    window.setTimeout(() => {
      setPlanButtonPulse(true);
      window.setTimeout(() => setPlanButtonPulse(false), 700);
      setPlanning(true);
      window.setTimeout(() => {
        setPlanning(false);
        setPreview(CANNED_NYC_PREVIEW);
        // Advance to the "preview shown" step.
        window.dispatchEvent(
          new CustomEvent('tutorial:advance', { detail: { to: 3 } }),
        );
      }, 3000);
    }, totalTyping);
  };

  // Rotate witty messages while planning is in flight.
  useEffect(() => {
    if (!planning) return;
    setWitIdx(Math.floor(Math.random() * PLANNING_MESSAGES.length));
    const t = setInterval(() => {
      setWitIdx((i) => (i + 1) % PLANNING_MESSAGES.length);
    }, 3000);
    return () => clearInterval(t);
  }, [planning]);

  const plan = async () => {
    const p = prompt.trim();
    if (!p) return;
    setPlanning(true);
    setError(null);
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const data = await api<Preview>('/api/llm/plan-trip', {
        method: 'POST',
        json: { prompt: p, timezone },
      });
      planMessagesRef.current.push({ role: 'user', content: p });
      if (data.user_output) {
        planMessagesRef.current.push({ role: 'assistant', content: data.user_output });
      }
      setPreview(data);
      void refreshEntitlement();
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        const needs = isNeedsPlus(err.data);
        const subscribed = await requirePlus(needs?.feature ?? 'brainstorm_quota');
        if (subscribed) {
          await refreshEntitlement();
          setPlanning(false);
          plan();
          return;
        }
        setError("You have used up this month's free planner messages.");
        return;
      }
      setError((err as any)?.message ?? 'Something went wrong — your prompt is saved, just hit Plan again.');
    } finally {
      setPlanning(false);
    }
  };

  const createTrip = async () => {
    if (!preview) return;
    setCreating(true);
    setError(null);

    // Tutorial demo: skip the real /trips POST entirely — the user already
    // has a seeded tutorial trip. Just navigate there and advance the tour.
    if (tutorialDemoActive && tutorial.trip_id) {
      try {
        window.dispatchEvent(
          new CustomEvent('tutorial:advance', { detail: { to: 4 } }),
        );
        setPreview(null);
        setPrompt('');
        setTutorialDemoActive(false);
        router.push(`/trips/${tutorial.trip_id}`);
      } finally {
        setCreating(false);
      }
      return;
    }
    try {
      const body: Record<string, any> = { name: preview.trip_name };
      if (preview.start_date) body.start_date = preview.start_date;
      body.timezone = preview.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (preview.destination_city) body.destination_city = preview.destination_city;
      if (preview.country_code) body.country_code = preview.country_code;
      if (preview.destination_lat != null) body.destination_lat = preview.destination_lat;
      if (preview.destination_lng != null) body.destination_lng = preview.destination_lng;

      const trip = await api<{ id: string }>('/api/trips', {
        method: 'POST',
        json: body,
      });

      await api(`/api/trips/${trip.id}/brainstorm/bulk`, {
        method: 'POST',
        json: { items: preview.items },
      });

      // Backfill the planning conversation as the first Brainstorm chat.
      // Failure is non-fatal — trip + items are already saved.
      if (planMessagesRef.current.length > 0) {
        try {
          await api(`/api/trips/${trip.id}/brainstorm/messages/seed`, {
            method: 'POST',
            json: { messages: planMessagesRef.current },
          });
        } catch {
          // ignore — seed is best-effort
        }
      }
      planMessagesRef.current = [];

      onTripCreated?.();
      router.push(`/trips/${trip.id}`);
    } catch (e: any) {
      setError(e?.message ?? 'Something went wrong.');
      setCreating(false);
    }
  };

  return (
    <div className="relative mb-8 bg-white border border-slate-100 rounded-[2rem] shadow-sm p-7 overflow-hidden">
      {/* Inner content — blurs/dims while planning so the overlay reads as
          a clear "system is working" state. */}
      <motion.div
        animate={{
          filter: planning ? 'blur(6px)' : 'blur(0px)',
          opacity: planning ? 0.45 : 1,
        }}
        transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
        // Block clicks on the underlying form while planning so users can't
        // re-trigger or edit mid-request.
        style={{ pointerEvents: planning ? 'none' : 'auto' }}
      >
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 bg-indigo-50 rounded-xl flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-indigo-600" />
        </div>
        <div>
          <h3 className="text-xl font-black text-slate-900 leading-tight">Plan a new trip</h3>
          <p className="text-slate-500 text-sm font-medium">
            AI turns your prompt into a starting brainstorm.
          </p>
        </div>
      </div>

      {/* items-stretch + self-stretch on the button so it matches the
          textarea's natural height (which scales with rows). */}
      <div className="flex items-stretch gap-2">
        <textarea
          rows={2}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder='e.g. "5-day Thailand itinerary with street food and temples"'
          className="flex-1 px-4 py-3 text-sm font-medium bg-slate-50 border border-slate-100 rounded-xl resize-none focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all"
        />
        <VoiceInputButton
          value={prompt}
          onChange={setPrompt}
          disabled={planning}
          className="self-center bg-slate-50 hover:bg-white border border-slate-100"
        />
        <motion.button
          onClick={plan}
          disabled={planning || !prompt.trim()}
          whileTap={{ scale: 0.97 }}
          animate={
            planButtonPulse
              ? { scale: [1, 1.08, 0.96, 1], boxShadow: '0 0 0 8px rgba(99,102,241,0.25)' }
              : { scale: 1 }
          }
          transition={{ type: 'spring', stiffness: 380, damping: 18 }}
          className="self-stretch px-6 bg-indigo-600 text-white rounded-xl text-sm font-black hover:bg-indigo-700 disabled:opacity-40 transition-colors whitespace-nowrap flex items-center gap-2 shadow-lg shadow-indigo-100"
        >
          {planning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          Plan
        </motion.button>
      </div>

      {error && <p className="text-rose-500 text-sm font-bold mt-3">{error}</p>}

      {preview && (
        <div
          data-tutorial="plan-preview-card"
          className="mt-5 p-5 bg-slate-50 border border-slate-100 rounded-2xl"
        >
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-indigo-600 mb-1">Preview</p>
              <p className="text-lg font-black text-slate-900 leading-tight">{preview.trip_name}</p>
              <p className="text-xs font-bold text-slate-400 mt-1">
                {preview.duration_days} days · {preview.items.length} brainstorm items
              </p>
            </div>
            <button
              onClick={() => setPreview(null)}
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-white rounded-lg transition-all"
              title="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          {preview.enrichment && preview.enrichment.status !== 'full' && (
            <p className="flex items-center gap-1.5 text-xs font-bold text-amber-600 mb-3">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              {preview.enrichment.skipped} of {preview.enrichment.total} places couldn&apos;t be loaded.
            </p>
          )}
          <div className="flex gap-2">
            <button
              onClick={createTrip}
              disabled={creating}
              className="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-indigo-600 text-white rounded-xl text-sm font-black hover:bg-indigo-700 transition-all disabled:opacity-50 shadow-lg shadow-indigo-100"
            >
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Rocket className="w-4 h-4" />}
              Create Trip and Take Me There
            </button>
            <button
              onClick={() => setPreview(null)}
              className="px-5 py-3 bg-white border border-slate-100 text-slate-500 rounded-xl text-sm font-black hover:bg-slate-50 hover:text-slate-700 transition-all"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
      </motion.div>

      {/* Planning overlay — blurred backdrop, animated icon, witty rotating
          message. Sits absolutely over the inner content; AnimatePresence
          fades it in/out without remounting the form. */}
      <AnimatePresence>
        {planning && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/55 backdrop-blur-md rounded-[2rem]"
            aria-live="polite"
            aria-busy="true"
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2.4, repeat: Infinity, ease: 'linear' }}
              className="relative mb-5"
            >
              <motion.div
                animate={{ scale: [1, 1.06, 1] }}
                transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
                className="w-14 h-14 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-xl shadow-indigo-200"
              >
                <Compass className="w-7 h-7 text-white" />
              </motion.div>
              <div className="absolute inset-0 rounded-2xl bg-indigo-500/30 blur-xl -z-10" />
            </motion.div>

            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-indigo-600 mb-2">
              Planning your trip
            </p>
            <AnimatePresence mode="wait">
              <motion.p
                key={witIdx}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
                className="text-sm font-bold text-slate-700 max-w-xs text-center"
              >
                {PLANNING_MESSAGES[witIdx]}
              </motion.p>
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
