'use client';

import { useCallback, useEffect, useImperativeHandle, forwardRef, useRef, useState } from 'react';
import { Lightbulb, Trash2, Loader2, MapPin, Info, Star, Clock, X } from 'lucide-react';

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
  const [openId, setOpenId] = useState<number | null>(null);
  const [popoverTop, setPopoverTop] = useState<number>(0);
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

  const toggleDetails = (id: number) => {
    if (openId === id) { setOpenId(null); return; }
    const card = cardRefs.current[id];
    if (card) setPopoverTop(card.offsetTop + card.offsetHeight + 8);
    setOpenId(id);
  };

  const openItem = openId != null ? items.find((i) => i.id === openId) ?? null : null;

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2 shrink-0">
        <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
          <Lightbulb className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-base font-black text-slate-900 tracking-tight">Brainstorm Bin</h3>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            {items.length} item{items.length === 1 ? '' : 's'}
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading && items.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-slate-300 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 opacity-40">
            <p className="text-sm font-black uppercase tracking-widest text-slate-400">Bin is Empty</p>
            <p className="text-xs font-medium text-slate-400 mt-1">
              Chat on the left, then &quot;Create items from chat&quot;.
            </p>
          </div>
        ) : (
          <div ref={gridRef} className="grid grid-cols-3 gap-3 relative">
            {items.map((item) => {
              const isSelected = selected.has(item.id);
              const isOpen = openId === item.id;
              return (
                <div
                  key={item.id}
                  ref={(el) => { cardRefs.current[item.id] = el; }}
                  onClick={() => selectionMode && toggleSelect(item.id)}
                  className={`min-w-0 bg-white rounded-xl p-2 flex flex-col gap-1.5 transition-all relative group ${
                    selectionMode
                      ? `cursor-pointer ${
                          isSelected
                            ? 'border-2 border-indigo-500 ring-2 ring-indigo-100'
                            : 'border border-slate-100 hover:border-indigo-100'
                        }`
                      : `border ${isOpen ? 'border-indigo-200 ring-2 ring-indigo-100' : 'border-slate-100 hover:border-indigo-100'}`
                  }`}
                >
                  {/* Row 1: MapPin | Title | Trash */}
                  <div className="flex items-center gap-1.5 min-w-0">
                    <MapPin className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                    <span className="text-[11px] font-black text-slate-900 leading-tight truncate flex-1 min-w-0">
                      {item.title}
                    </span>
                    {!selectionMode && (
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteItem(item.id); }}
                        className="p-0.5 text-slate-300 hover:text-rose-500 transition-colors opacity-0 group-hover:opacity-100 shrink-0"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>

                  {/* Row 2: Info | Rating | Time */}
                  <div className="flex items-center gap-1.5 min-w-0">
                    <button
                      onClick={(e) => { e.stopPropagation(); toggleDetails(item.id); }}
                      className={`p-0.5 rounded-md transition-colors shrink-0 ${
                        isOpen
                          ? 'bg-indigo-600 text-white'
                          : 'text-slate-400 hover:text-indigo-600 hover:bg-indigo-50'
                      }`}
                      title="Details"
                    >
                      <Info className="w-3 h-3" />
                    </button>
                    {item.rating != null && (
                      <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-slate-500 shrink-0">
                        <Star className="w-2.5 h-2.5 text-slate-400" /> {item.rating}
                      </span>
                    )}
                    {item.time_hint && (
                      <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-slate-500 truncate min-w-0">
                        <Clock className="w-2.5 h-2.5 shrink-0" /> <span className="truncate">{item.time_hint}</span>
                      </span>
                    )}
                  </div>

                  {/* Row 3: Category */}
                  <div className="min-w-0">
                    {item.category ? (
                      <span className="inline-block text-[9px] font-black uppercase tracking-widest text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded-md truncate max-w-full">
                        {item.category}
                      </span>
                    ) : (
                      <span className="text-[9px] font-bold uppercase tracking-widest text-slate-300">—</span>
                    )}
                  </div>
                </div>
              );
            })}

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

      {items.length > 0 && (
        <div className="border-t border-slate-100 px-4 py-3 flex items-center justify-center gap-2 shrink-0 bg-white">
          {!selectionMode ? (
            <>
              <button
                onClick={() => setSelectionMode(true)}
                className="px-3 py-1.5 bg-indigo-50 text-indigo-600 border border-indigo-100 rounded-lg text-xs font-black hover:bg-indigo-100 transition-all"
              >
                Select
              </button>
              <button
                onClick={() => promote(null)}
                disabled={working}
                className="px-3 py-1.5 bg-indigo-100 text-indigo-700 rounded-lg text-xs font-black hover:bg-indigo-200 transition-all disabled:opacity-50"
              >
                {working ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Add All to Idea Bin'}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={exitSelection}
                className="px-3 py-1.5 bg-slate-50 text-slate-600 border border-slate-200 rounded-lg text-xs font-black hover:bg-slate-100 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={() => promote(Array.from(selected))}
                disabled={working || selected.size === 0}
                className="px-3 py-1.5 bg-indigo-100 text-indigo-700 rounded-lg text-xs font-black hover:bg-indigo-200 transition-all disabled:opacity-40"
              >
                {working ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : `Send ${selected.size} to Idea Bin`}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
});

function DetailPopover({ item, onClose }: { item: BrainstormItem; onClose: () => void }) {
  return (
    <div className="h-full bg-white border border-slate-200 rounded-2xl shadow-xl flex flex-col overflow-hidden">
      <div className="flex items-start justify-between gap-2 px-4 py-3 border-b border-slate-100 shrink-0">
        <div className="flex items-start gap-2 min-w-0">
          <MapPin className="w-4 h-4 text-indigo-500 shrink-0 mt-0.5" />
          <div className="min-w-0">
            <p className="text-sm font-black text-slate-900 leading-tight truncate">{item.title}</p>
            {item.address && (
              <p className="text-[11px] font-medium text-slate-500 truncate mt-0.5">{item.address}</p>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-50 rounded-lg transition-colors shrink-0"
          title="Close"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {item.photo_url && (
          <img
            src={item.photo_url}
            alt=""
            className="w-full h-36 object-cover rounded-xl border border-slate-100"
          />
        )}

        <div className="flex items-center gap-2 flex-wrap">
          {item.rating != null && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-slate-50 text-slate-700 rounded-lg text-xs font-bold">
              <Star className="w-3 h-3 text-slate-500" /> {item.rating}
            </span>
          )}
          {item.time_hint && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-slate-50 text-slate-700 rounded-lg text-xs font-bold">
              <Clock className="w-3 h-3 text-slate-500" /> {item.time_hint}
            </span>
          )}
          {item.category && (
            <span className="px-2 py-1 bg-indigo-50 text-indigo-600 rounded-lg text-[10px] font-black uppercase tracking-widest">
              {item.category}
            </span>
          )}
        </div>

        {item.description && (
          <p className="text-sm font-medium text-slate-500 leading-relaxed">{item.description}</p>
        )}

        {!item.photo_url && !item.description && !item.address && (
          <p className="text-xs font-medium text-slate-400 italic">No additional details available.</p>
        )}
      </div>
    </div>
  );
}

export default BrainstormBin;
