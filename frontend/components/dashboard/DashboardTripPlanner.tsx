'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, Loader2, Rocket, X } from 'lucide-react';

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
    <div className="mb-6 bg-white border border-slate-100 rounded-2xl shadow-sm p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-amber-50 rounded-xl flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-amber-600" />
        </div>
        <div>
          <h3 className="text-base font-black text-slate-900 tracking-tight">Plan a new trip</h3>
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">
            AI turns your prompt into a starting brainstorm
          </p>
        </div>
      </div>

      <div className="flex items-end gap-2">
        <textarea
          rows={2}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder='e.g. "5-day Thailand itinerary with street food and temples"'
          className="flex-1 px-4 py-3 text-sm font-medium border border-slate-200 bg-slate-50 rounded-xl resize-none focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
        />
        <button
          onClick={plan}
          disabled={planning || !prompt.trim()}
          className="h-[52px] px-4 bg-slate-900 text-white rounded-xl text-sm font-black uppercase tracking-widest hover:bg-indigo-600 disabled:opacity-40 transition-all whitespace-nowrap flex items-center gap-2"
        >
          {planning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          Plan
        </button>
      </div>

      {error && <p className="text-rose-500 text-xs font-bold mt-2">{error}</p>}

      {preview && (
        <div className="mt-4 p-4 bg-amber-50/50 border border-amber-100 rounded-xl">
          <div className="flex items-start justify-between gap-3 mb-3">
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-amber-600 mb-1">Preview</p>
              <p className="text-base font-black text-slate-900">{preview.trip_name}</p>
              <p className="text-xs font-bold text-slate-500 mt-0.5">
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
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-black uppercase tracking-widest hover:bg-indigo-500 transition-all disabled:opacity-50"
            >
              {creating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Rocket className="w-3.5 h-3.5" />}
              Create Trip and Take Me There
            </button>
            <button
              onClick={() => setPreview(null)}
              className="px-4 py-2.5 bg-white border border-slate-200 text-slate-500 rounded-xl text-xs font-black uppercase tracking-widest hover:bg-slate-50 transition-all"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
