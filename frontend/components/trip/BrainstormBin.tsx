'use client';

import { useCallback, useEffect, useImperativeHandle, forwardRef, useState } from 'react';
import { Lightbulb, Trash2, Loader2 } from 'lucide-react';

export type BrainstormItem = {
  id: number;
  title: string;
  description?: string | null;
  category?: string | null;
  photo_url?: string | null;
  rating?: number | null;
  time_hint?: string | null;
  address?: string | null;
};

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export type BrainstormBinHandle = { refresh: () => void };

const BrainstormBin = forwardRef<BrainstormBinHandle, { tripId: string }>(function BrainstormBin(
  { tripId },
  ref,
) {
  const [items, setItems] = useState<BrainstormItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [working, setWorking] = useState(false);

  const refresh = useCallback(() => {
    setLoading(true);
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/brainstorm/items`, {
      headers: authHeaders(),
      cache: 'no-store',
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data: BrainstormItem[]) => setItems(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [tripId]);

  useImperativeHandle(ref, () => ({ refresh }), [refresh]);

  useEffect(() => { refresh(); }, [refresh]);

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const exitSelection = () => {
    setSelectionMode(false);
    setSelected(new Set());
  };

  const promote = async (idsOrAll: number[] | null) => {
    setWorking(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/brainstorm/promote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ item_ids: idsOrAll }),
      });
      if (res.ok) {
        window.dispatchEvent(new CustomEvent('idea-bin:refresh'));
        exitSelection();
        refresh();
      }
    } finally {
      setWorking(false);
    }
  };

  const deleteItem = async (id: number) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/brainstorm/items/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2 shrink-0">
        <div className="p-2 bg-amber-50 text-amber-600 rounded-xl">
          <Lightbulb className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-base font-black text-slate-900 tracking-tight">Brainstorm Bin</h3>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            {items.length} item{items.length === 1 ? '' : 's'}
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        {loading && items.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-slate-300 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 opacity-40">
            <p className="text-sm font-black uppercase tracking-widest text-slate-400">Bin is Empty</p>
            <p className="text-xs font-medium text-slate-400 mt-1">
              Chat on the left, then "Create items from chat".
            </p>
          </div>
        ) : (
          items.map((item) => {
            const isSelected = selected.has(item.id);
            return (
              <div
                key={item.id}
                onClick={() => selectionMode && toggleSelect(item.id)}
                className={`p-4 bg-white rounded-2xl shadow-sm transition-all relative overflow-hidden ${
                  selectionMode
                    ? `cursor-pointer ${
                        isSelected
                          ? 'border-2 border-indigo-500 ring-2 ring-indigo-200'
                          : 'border border-slate-100 hover:border-slate-200'
                      }`
                    : 'border border-slate-100 group'
                }`}
              >
                <div className="absolute top-0 left-0 w-1 h-full bg-amber-200" />
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-black text-slate-800 truncate">{item.title}</span>
                      {item.category && (
                        <span className="px-2 py-0.5 bg-slate-50 text-slate-500 rounded-lg text-[10px] font-bold shrink-0">
                          {item.category}
                        </span>
                      )}
                    </div>
                    {item.photo_url && (
                      <img src={item.photo_url} alt="" className="mt-2 w-full h-24 object-cover rounded-lg" />
                    )}
                    {item.description && (
                      <p className="mt-1 text-[11px] text-slate-500 font-medium line-clamp-2">{item.description}</p>
                    )}
                    <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                      {item.rating != null && (
                        <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-amber-50 text-amber-600 rounded-lg text-[10px] font-bold">
                          ★ {item.rating}
                        </span>
                      )}
                      {item.time_hint && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-50 text-slate-500 rounded-lg text-[10px] font-bold">
                          {item.time_hint}
                        </span>
                      )}
                    </div>
                  </div>
                  {!selectionMode && (
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteItem(item.id); }}
                      className="p-1.5 text-slate-300 hover:text-rose-500 transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {items.length > 0 && (
        <div className="border-t border-slate-100 p-4 flex items-center gap-2 shrink-0 bg-slate-50">
          {!selectionMode ? (
            <>
              <button
                onClick={() => setSelectionMode(true)}
                className="flex-1 px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs font-black uppercase tracking-widest text-slate-700 hover:bg-slate-50 transition-all"
              >
                Select
              </button>
              <button
                onClick={() => promote(null)}
                disabled={working}
                className="flex-1 px-3 py-2 bg-indigo-600 text-white rounded-xl text-xs font-black uppercase tracking-widest hover:bg-indigo-500 transition-all disabled:opacity-50"
              >
                {working ? <Loader2 className="w-3.5 h-3.5 animate-spin mx-auto" /> : 'Add All to Idea Bin'}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={exitSelection}
                className="flex-1 px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs font-black uppercase tracking-widest text-slate-500 hover:bg-slate-50 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={() => promote(Array.from(selected))}
                disabled={working || selected.size === 0}
                className="flex-1 px-3 py-2 bg-indigo-600 text-white rounded-xl text-xs font-black uppercase tracking-widest hover:bg-indigo-500 transition-all disabled:opacity-40"
              >
                {working ? <Loader2 className="w-3.5 h-3.5 animate-spin mx-auto" /> : `Send ${selected.size} to Idea Bin`}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
});

export default BrainstormBin;
