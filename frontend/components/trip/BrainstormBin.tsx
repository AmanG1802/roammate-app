'use client';

import { useCallback, useEffect, useImperativeHandle, forwardRef, useRef, useState } from 'react';
import { Lightbulb, Trash2, Loader2, MapPin, Info, Star, Clock, X, PackagePlus } from 'lucide-react';
import { categoryAccent } from '@/lib/categoryColors';

export type BrainstormItem = {
  id: number;
  title: string;
  description?: string | null;
  category?: string | null;
  photo_url?: string | null;
  rating?: number | null;
  time_hint?: string | null;
  time_category?: string | null;
  address?: string | null;
};

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const SHOW_PHOTOS =
  (process.env.NEXT_PUBLIC_GOOGLE_MAPS_FETCH_PHOTOS ?? 'true').toLowerCase() === 'true';
const SHOW_RATING =
  (process.env.NEXT_PUBLIC_GOOGLE_MAPS_FETCH_RATING ?? 'true').toLowerCase() === 'true';

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
  const [openId, setOpenId] = useState<number | null>(null);
  const [popoverTop, setPopoverTop] = useState<number>(0);
  const [clearConfirm, setClearConfirm] = useState(false);
  const cardRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const gridRef = useRef<HTMLDivElement>(null);

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

  const clearAll = async () => {
    if (!clearConfirm) { setClearConfirm(true); return; }
    setClearConfirm(false);
    setItems([]);
    setOpenId(null);
    exitSelection();
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/brainstorm/items`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
  };

  const toggleDetails = (id: number) => {
    if (openId === id) { setOpenId(null); return; }
    const card = cardRefs.current[id];
    if (card) setPopoverTop(card.offsetTop + card.offsetHeight + 8);
    setOpenId(id);
  };

  const openItem = openId != null ? items.find((i) => i.id === openId) ?? null : null;

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-3 shrink-0">
        <div className="p-2.5 bg-gradient-to-br from-amber-400 to-orange-500 text-white rounded-xl shadow-sm shadow-amber-200/60 shrink-0">
          <Lightbulb className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-black text-slate-900 tracking-tight">Brainstorm Bin</h3>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Saved ideas
          </p>
        </div>
        {items.length > 0 && (
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              onClick={clearAll}
              onBlur={() => setClearConfirm(false)}
              title={clearConfirm ? 'Click again to confirm' : 'Clear all items'}
              className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-black transition-all cursor-pointer border ${
                clearConfirm
                  ? 'bg-rose-500 text-white border-rose-500'
                  : 'bg-white text-rose-400 border-rose-100 hover:bg-rose-50 hover:border-rose-200'
              }`}
            >
              <Trash2 className="w-2.5 h-2.5" />
              {clearConfirm ? 'Sure?' : 'Clear'}
            </button>
            <span className="px-2.5 py-1 bg-amber-50 text-amber-600 rounded-full text-[10px] font-black border border-amber-100 tabular-nums">
              {items.length}
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && items.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-slate-300 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            <div className="w-14 h-14 bg-slate-50 border border-slate-100 rounded-2xl flex items-center justify-center">
              <Lightbulb className="w-7 h-7 text-slate-300" />
            </div>
            <div className="text-center max-w-[180px]">
              <p className="text-sm font-black text-slate-400 uppercase tracking-widest">Bin is Empty</p>
              <p className="text-xs font-medium text-slate-400 mt-1.5 leading-relaxed">
                Chat on the left, then &quot;Create items from chat&quot;.
              </p>
            </div>
          </div>
        ) : (
          <div ref={gridRef} className="grid grid-cols-2 gap-3 relative">
            {items.map((item) => {
              const isSelected = selected.has(item.id);
              const isOpen = openId === item.id;
              const accent = categoryAccent(item.category);
              return (
                <div
                  key={item.id}
                  ref={(el) => { cardRefs.current[item.id] = el; }}
                  onClick={() => selectionMode && toggleSelect(item.id)}
                  className={`relative min-w-0 bg-white rounded-2xl p-3 pl-4 flex flex-col gap-1.5 transition-all group overflow-hidden cursor-pointer ${
                    selectionMode
                      ? isSelected
                        ? 'border-2 border-indigo-500 ring-2 ring-indigo-100 shadow-md shadow-indigo-100/50'
                        : 'border border-slate-100 hover:border-indigo-100 hover:shadow-sm'
                      : `border ${isOpen ? 'border-indigo-200 ring-2 ring-indigo-100 shadow-md shadow-indigo-100/40' : 'border-slate-100 hover:border-indigo-100 hover:shadow-sm'}`
                  }`}
                >
                  {/* Left accent bar */}
                  <div className={`absolute left-0 top-0 w-1 h-full ${accent.bar} rounded-l-2xl transition-all group-hover:w-1.5`} />

                  {/* Row 1: [MapPin slot] Title + Trash */}
                  <div className="flex items-start gap-1.5 min-w-0">
                    <div className="w-3.5 flex justify-center shrink-0 pt-0.5">
                      <MapPin className="w-3 h-3 text-indigo-400" />
                    </div>
                    <span className="text-xs font-black text-slate-900 leading-snug flex-1 min-w-0 line-clamp-2">
                      {item.title}
                    </span>
                    {!selectionMode && (
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteItem(item.id); }}
                        className="p-0.5 text-slate-300 hover:text-rose-500 transition-colors opacity-0 group-hover:opacity-100 shrink-0 cursor-pointer"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>

                  {/* Row 2: [Info slot] Rating + Time category */}
                  <div className="flex items-center gap-1.5 min-w-0">
                    <div className="w-3.5 flex justify-center shrink-0">
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleDetails(item.id); }}
                        className={`-m-0.5 p-0.5 rounded-md transition-colors cursor-pointer ${
                          isOpen
                            ? 'bg-indigo-600 text-white'
                            : 'text-slate-400 hover:text-indigo-600 hover:bg-indigo-50'
                        }`}
                        title="Details"
                      >
                        <Info className="w-3 h-3" />
                      </button>
                    </div>
                    {SHOW_RATING && item.rating != null && (
                      <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-slate-500 shrink-0">
                        <Star className="w-2.5 h-2.5 text-amber-400" /> {item.rating}
                      </span>
                    )}
                    {(item.time_category ?? item.time_hint) && (
                      <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-slate-400 truncate min-w-0">
                        <Clock className="w-2.5 h-2.5 text-slate-300 shrink-0" />
                        <span className="truncate">{item.time_category ?? item.time_hint}</span>
                      </span>
                    )}
                  </div>

                  {/* Row 3: [spacer] Category badge */}
                  <div className="flex items-center gap-1.5 min-w-0">
                    <div className="w-3.5 shrink-0" />
                    <div className="min-w-0">
                      {item.category ? (
                        <span className={`inline-block text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-md truncate max-w-full ${accent.badge}`}>
                          {item.category}
                        </span>
                      ) : (
                        <span className="text-[9px] font-bold uppercase tracking-widest text-slate-300">—</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Detail popover — absolutely positioned inside the grid */}
            {openItem && (
              <div
                className="absolute left-0 right-0 z-20"
                style={{ top: popoverTop, height: 280 }}
              >
                <DetailPopover item={openItem} onClose={() => setOpenId(null)} />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer actions */}
      {items.length > 0 && (
        <div className="border-t border-slate-100 px-4 py-3 flex items-center justify-center gap-2 shrink-0 bg-white">
          {!selectionMode ? (
            <>
              <button
                onClick={() => setSelectionMode(true)}
                className="px-3.5 py-2 bg-white text-slate-600 border border-slate-200 rounded-xl text-xs font-black hover:bg-slate-50 hover:border-slate-300 transition-all cursor-pointer"
              >
                Select
              </button>
              <button
                onClick={() => promote(null)}
                disabled={working}
                className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-indigo-500 to-violet-500 text-white rounded-xl text-xs font-black hover:from-indigo-600 hover:to-violet-600 transition-all shadow-sm shadow-indigo-200/40 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {working
                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  : <PackagePlus className="w-3.5 h-3.5" />}
                Add All to Idea Bin
              </button>
            </>
          ) : (
            <>
              <button
                onClick={exitSelection}
                className="px-3.5 py-2 bg-white text-slate-600 border border-slate-200 rounded-xl text-xs font-black hover:bg-slate-50 transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => promote(Array.from(selected))}
                disabled={working || selected.size === 0}
                className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-indigo-500 to-violet-500 text-white rounded-xl text-xs font-black hover:from-indigo-600 hover:to-violet-600 transition-all shadow-sm shadow-indigo-200/40 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                {working
                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  : <PackagePlus className="w-3.5 h-3.5" />}
                {selected.size > 0 ? `Send ${selected.size} to Idea Bin` : 'Select items'}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
});

function DetailPopover({ item, onClose }: { item: BrainstormItem; onClose: () => void }) {
  const accent = categoryAccent(item.category);
  return (
    <div className="h-full bg-white border border-slate-200 rounded-2xl shadow-xl flex flex-col overflow-hidden">
      {/* Popover header */}
      <div className="flex items-start justify-between gap-2 px-4 py-3 border-b border-slate-100 shrink-0">
        <div className="flex items-start gap-2 min-w-0">
          <div className={`w-1 self-stretch rounded-full shrink-0 ${accent.bar}`} />
          <div className="min-w-0">
            <p className="text-sm font-black text-slate-900 leading-tight truncate">{item.title}</p>
            {item.address && (
              <p className="text-[11px] font-medium text-slate-500 truncate mt-0.5">{item.address}</p>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-50 rounded-lg transition-colors shrink-0 cursor-pointer"
          title="Close"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {SHOW_PHOTOS && item.photo_url && (
          <div className="relative w-full h-36 rounded-xl overflow-hidden border border-slate-100">
            <img
              src={item.photo_url}
              alt=""
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />
          </div>
        )}

        <div className="flex items-center gap-2 flex-wrap">
          {SHOW_RATING && item.rating != null && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-50 text-amber-700 rounded-lg text-xs font-bold border border-amber-100">
              <Star className="w-3 h-3 text-amber-400" /> {item.rating}
            </span>
          )}
          {item.time_hint && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-50 text-slate-700 rounded-lg text-xs font-bold border border-slate-100">
              <Clock className="w-3 h-3 text-slate-400" /> {item.time_hint}
            </span>
          )}
          {item.category && (
            <span className={`px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest ${accent.badge}`}>
              {item.category}
            </span>
          )}
        </div>

        {item.description && (
          <p className="text-sm font-medium text-slate-500 leading-relaxed">{item.description}</p>
        )}

        {(!SHOW_PHOTOS || !item.photo_url) && !item.description && !item.address && (
          <p className="text-xs font-medium text-slate-400 italic">No additional details available.</p>
        )}
      </div>
    </div>
  );
}

export default BrainstormBin;
