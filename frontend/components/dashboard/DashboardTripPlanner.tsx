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
    <div className="mb-8 bg-white border border-slate-100 rounded-[2rem] shadow-sm p-7">
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

      <div className="flex items-end gap-2">
        <textarea
          rows={2}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder='e.g. "5-day Thailand itinerary with street food and temples"'
          className="flex-1 px-4 py-3 text-sm font-medium bg-slate-50 border border-slate-100 rounded-xl resize-none focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all"
        />
        <button
          onClick={plan}
          disabled={planning || !prompt.trim()}
          className="h-[52px] px-5 bg-indigo-600 text-white rounded-xl text-sm font-black hover:bg-indigo-700 disabled:opacity-40 transition-all whitespace-nowrap flex items-center gap-2 shadow-lg shadow-indigo-100"
        >
          {planning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          Plan
        </button>
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
    </div>
  );
}
