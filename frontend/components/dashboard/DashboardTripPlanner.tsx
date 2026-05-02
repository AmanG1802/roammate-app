'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, Loader2, Rocket, X, Compass } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

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

type Preview = {
  trip_name: string;
  start_date: string | null;
  duration_days: number;
  items: Array<Record<string, any>>;
};

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function DashboardTripPlanner({ onTripCreated }: { onTripCreated?: () => void }) {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [preview, setPreview] = useState<Preview | null>(null);
  const [planning, setPlanning] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [witIdx, setWitIdx] = useState(0);

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
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/llm/plan-trip`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ prompt: p }),
      });
      if (!res.ok) throw new Error('Planner unavailable — try again.');
      setPreview(await res.json());
    } catch (e: any) {
      setError(e?.message ?? 'Something went wrong.');
    } finally {
      setPlanning(false);
    }
  };

  const createTrip = async () => {
    if (!preview) return;
    setCreating(true);
    setError(null);
    try {
      const body: Record<string, any> = { name: preview.trip_name };
      if (preview.start_date) body.start_date = preview.start_date;

      const tripRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(body),
      });
      if (!tripRes.ok) throw new Error('Could not create trip.');
      const trip = await tripRes.json();

      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${trip.id}/brainstorm/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ items: preview.items }),
      });

      onTripCreated?.();
      router.push(`/trips?id=${trip.id}&mode=brainstorm`);
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
        <motion.button
          onClick={plan}
          disabled={planning || !prompt.trim()}
          whileTap={{ scale: 0.97 }}
          transition={{ type: 'spring', stiffness: 380, damping: 32 }}
          className="self-stretch px-6 bg-indigo-600 text-white rounded-xl text-sm font-black hover:bg-indigo-700 disabled:opacity-40 transition-colors whitespace-nowrap flex items-center gap-2 shadow-lg shadow-indigo-100"
        >
          {planning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          Plan
        </motion.button>
      </div>

      {error && <p className="text-rose-500 text-sm font-bold mt-3">{error}</p>}

      {preview && (
        <div className="mt-5 p-5 bg-slate-50 border border-slate-100 rounded-2xl">
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
