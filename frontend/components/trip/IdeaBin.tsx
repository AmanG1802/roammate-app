'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useTripStore } from '@/lib/store';
import { MapPin, Loader2, Sparkles, Plus, Clock, Pencil, Trash2, Check, X, UserCircle, Info, Star } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import VoteControl from '@/components/trip/VoteControl';
import { categoryAccent } from '@/lib/categoryColors';

/** Extract a time hint from a text fragment, e.g. "Eiffel Tower at 2pm" → "2pm" */
function extractTimeHint(text: string): string | null {
  const match = text.match(
    /(?:at\s+|@\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{2}:\d{2})/i
  );
  return match ? match[1].trim() : null;
}

/** Strip time hint from text so the title is clean */
function stripTimeHint(text: string): string {
  return text
    .replace(/\s+(?:at|@)\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)/gi, '')
    .replace(/\s+\d{2}:\d{2}/g, '')
    .trim();
}

/** Convert a display hint like "2pm", "2:30pm", "14:00" → "HH:MM" for <input type="time"> */
function hintToTimeValue(hint: string | null | undefined): string {
  if (!hint) return '';
  const s = hint.trim().toLowerCase();
  const ampm = s.match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$/);
  if (ampm) {
    let h = parseInt(ampm[1], 10);
    const m = parseInt(ampm[2] ?? '0', 10);
    if (ampm[3] === 'pm' && h !== 12) h += 12;
    if (ampm[3] === 'am' && h === 12) h = 0;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  }
  const mil = s.match(/^(\d{1,2}):(\d{2})$/);
  if (mil) return `${String(mil[1]).padStart(2, '0')}:${mil[2]}`;
  return '';
}

/** Convert "HH:MM" from <input type="time"> → friendly hint like "2pm" or "2:30pm" */
function timeValueToHint(val: string): string | null {
  if (!val) return null;
  const [hStr, mStr] = val.split(':');
  let h = parseInt(hStr, 10);
  const m = parseInt(mStr, 10);
  const ampm = h >= 12 ? 'pm' : 'am';
  if (h > 12) h -= 12;
  if (h === 0) h = 12;
  return m === 0 ? `${h}${ampm}` : `${h}:${String(m).padStart(2, '0')}${ampm}`;
}

const SHOW_PHOTOS =
  (process.env.NEXT_PUBLIC_GOOGLE_MAPS_FETCH_PHOTOS ?? 'true').toLowerCase() === 'true';
const SHOW_RATING =
  (process.env.NEXT_PUBLIC_GOOGLE_MAPS_FETCH_RATING ?? 'true').toLowerCase() === 'true';

export default function IdeaBin({ tripId, readOnly = false, canVote = false }: { tripId: string | null; readOnly?: boolean; canVote?: boolean }) {
  const [inputText, setInputText] = useState('');
  const [isIngesting, setIsIngesting] = useState(false);
  const [editingTimeId, setEditingTimeId] = useState<string | null>(null);
  const [editingTimeVal, setEditingTimeVal] = useState('');
  const [extras, setExtras] = useState<Record<string, { description?: string | null; photo_url?: string | null; rating?: number | null; address?: string | null; category?: string | null }>>({});
  const [openId, setOpenId] = useState<string | null>(null);
  const [popoverTop, setPopoverTop] = useState<number>(0);
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const { ideas, addIdea, setIdeas, removeIdea } = useTripStore();

  const loadIdeas = useCallback(() => {
    if (!tripId) return;
    const token = localStorage.getItem('token');
    if (!token) return;

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/ideas`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((data: any[]) => {
        setIdeas(
          data.map((item) => ({
            id: item.id.toString(),
            title: item.title,
            lat: item.lat ?? 0,
            lng: item.lng ?? 0,
            time_hint: item.time_hint ?? null,
            added_by: item.added_by ?? null,
            up: item.up ?? 0,
            down: item.down ?? 0,
            my_vote: item.my_vote ?? 0,
          }))
        );
        const extraMap: Record<string, { description?: string | null; photo_url?: string | null; rating?: number | null; address?: string | null; category?: string | null }> = {};
        for (const item of data) {
          extraMap[item.id.toString()] = {
            description: item.description ?? null,
            photo_url: item.photo_url ?? null,
            rating: item.rating ?? null,
            address: item.address ?? null,
            category: item.category ?? null,
          };
        }
        setExtras(extraMap);
      })
      .catch(() => {});
  }, [tripId, setIdeas]);

  useEffect(() => { loadIdeas(); }, [loadIdeas]);

  useEffect(() => {
    const handler = () => loadIdeas();
    window.addEventListener('idea-bin:refresh', handler);
    return () => window.removeEventListener('idea-bin:refresh', handler);
  }, [loadIdeas]);

  const handleIngest = async () => {
    if (!inputText.trim()) return;
    setIsIngesting(true);

    try {
      const token = localStorage.getItem('token');

      if (tripId && token) {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/ingest`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ text: inputText }),
          }
        );

        if (response.ok) {
          const newItems = await response.json();
          const fragments = inputText.split(/[,\n]/);
          newItems.forEach((item: any, idx: number) => {
            const fragment = fragments[idx] ?? '';
            addIdea({
              id: item.id.toString(),
              title: item.title,
              lat: item.lat,
              lng: item.lng,
              time_hint: item.time_hint ?? extractTimeHint(fragment),
              added_by: item.added_by ?? null,
            });
          });
          setInputText('');
          return;
        }
      }

      const fragments = inputText.split(/[,\n]/);
      fragments
        .map((raw) => {
          const trimmed = raw.trim();
          if (!trimmed) return null;
          const timeHint = extractTimeHint(trimmed);
          const title = stripTimeHint(trimmed) || trimmed;
          return { id: Math.random().toString(36).slice(2, 9), title, lat: 41.8902, lng: 12.4922, time_hint: timeHint };
        })
        .filter(Boolean)
        .forEach((idea: any) => addIdea(idea));
      setInputText('');
    } finally {
      setIsIngesting(false);
    }
  };

  const handleDeleteIdea = async (ideaId: string) => {
    removeIdea(ideaId);
    if (!tripId) return;
    const token = localStorage.getItem('token');
    if (!token) return;
    const numericId = parseInt(ideaId, 10);
    if (isNaN(numericId)) return;
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/ideas/${numericId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch { /* optimistic removal already done */ }
  };

  const handleSaveTime = async (ideaId: string) => {
    const newHint = timeValueToHint(editingTimeVal);
    setIdeas(ideas.map((i) => i.id === ideaId ? { ...i, time_hint: newHint } : i));
    setEditingTimeId(null);

    if (!tripId) return;
    const token = localStorage.getItem('token');
    if (!token) return;
    const numericId = parseInt(ideaId, 10);
    if (isNaN(numericId)) return;
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/ideas/${numericId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ time_hint: newHint }),
      });
    } catch { /* optimistic update already done */ }
  };

  return (
    <div className="flex flex-col h-full bg-white border-l border-slate-100 w-80 shadow-2xl shadow-slate-200">
      <div className="p-6 border-b border-slate-50">
        <div className="flex items-center gap-2 mb-2">
          <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
            <Sparkles className="w-5 h-5" />
          </div>
          <h3 className="text-xl font-black text-slate-900 tracking-tight">Idea Bin</h3>
        </div>
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">
          Smart location ingestion
        </p>

        <div className="relative group">
          <textarea
            className="w-full p-4 pr-12 text-sm font-medium border border-slate-100 bg-slate-50/50 rounded-2xl focus:ring-4 focus:ring-indigo-50/50 focus:border-indigo-200 focus:bg-white outline-none resize-none h-32 transition-all"
            placeholder="Paste locations, URLs, or notes..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />
          <button
            onClick={handleIngest}
            disabled={isIngesting || !inputText.trim()}
            className="absolute bottom-3 right-3 p-3 bg-slate-900 text-white rounded-xl hover:bg-indigo-600 disabled:opacity-30 disabled:hover:bg-slate-900 transition-all shadow-lg"
          >
            {isIngesting ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Plus className="w-5 h-5" />
            )}
          </button>
        </div>

        <p className="mt-2 text-[10px] text-slate-400 font-medium">
          Tip: include times like &ldquo;Eiffel Tower at 2pm&rdquo; for auto-scheduling
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-3 relative">
        <AnimatePresence initial={false}>
          {ideas.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-20 opacity-20"
            >
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <MapPin className="w-8 h-8 text-slate-400" />
              </div>
              <p className="text-sm font-black uppercase tracking-widest">Bin is Empty</p>
            </motion.div>
          ) : (
            ideas.map((idea) => {
              const isOpen = openId === idea.id;
              const accent = categoryAccent(extras[idea.id]?.category);
              return (
              <motion.div
                key={idea.id}
                layout
                initial={{ opacity: 0, scale: 0.9, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8 }}
                draggable={!readOnly}
                onDragStartCapture={(e) => { if (!readOnly) e.dataTransfer.setData('ideaId', idea.id); }}
                data-testid={`idea-card-${idea.id}`}
                ref={(el) => { cardRefs.current[idea.id] = el; }}
                className={`p-3 pl-4 bg-white border rounded-2xl shadow-sm cursor-grab active:cursor-grabbing transition-all group relative overflow-hidden flex flex-col gap-1.5 ${
                  isOpen ? 'border-indigo-200 ring-2 ring-indigo-100' : 'border-slate-100 hover:border-indigo-100 hover:shadow-md'
                }`}
              >
                {/* Left accent bar */}
                <div className={`absolute left-0 top-0 w-1 h-full ${accent.bar} rounded-l-2xl transition-all group-hover:w-1.5`} />

                {/* Row 1: [MapPin slot] Title | Trash */}
                <div className="flex items-start gap-1.5 min-w-0">
                  <div className="w-3.5 flex justify-center shrink-0 pt-0.5">
                    <MapPin className="w-3 h-3 text-indigo-400" />
                  </div>
                  <span className="text-sm font-black text-slate-900 truncate leading-tight flex-1 min-w-0">
                    {idea.title}
                  </span>
                  {!readOnly && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteIdea(idea.id); }}
                      className="p-0.5 text-slate-300 hover:text-rose-500 transition-colors opacity-0 group-hover:opacity-100 shrink-0"
                      title="Delete idea"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Row 2: [Info slot] Rating | Time | Pencil */}
                <div className="flex items-center gap-1.5 min-w-0">
                  <div className="w-3.5 flex justify-center shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (openId === idea.id) { setOpenId(null); return; }
                        const card = cardRefs.current[idea.id];
                        if (card) setPopoverTop(card.offsetTop + card.offsetHeight + 8);
                        setOpenId(idea.id);
                      }}
                      className={`-m-0.5 p-0.5 rounded-md transition-colors ${
                        isOpen ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-indigo-600 hover:bg-indigo-50'
                      }`}
                      title="Details"
                    >
                      <Info className="w-3 h-3" />
                    </button>
                  </div>
                  {SHOW_RATING && extras[idea.id]?.rating != null && (
                    <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-slate-500 shrink-0">
                      <Star className="w-2.5 h-2.5 text-amber-400" /> {extras[idea.id]!.rating}
                    </span>
                  )}
                  {!readOnly && editingTimeId === idea.id ? (
                    <div className="flex items-center gap-1 min-w-0">
                      <input
                        autoFocus
                        type="time"
                        value={editingTimeVal}
                        onChange={(e) => setEditingTimeVal(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSaveTime(idea.id)}
                        className="w-20 px-1.5 py-0.5 text-[11px] font-bold border border-slate-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
                      />
                      <button
                        onClick={() => handleSaveTime(idea.id)}
                        className="p-0.5 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                      >
                        <Check className="w-2.5 h-2.5" />
                      </button>
                      <button
                        onClick={() => setEditingTimeId(null)}
                        className="p-0.5 text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        <X className="w-2.5 h-2.5" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-slate-500 truncate min-w-0">
                        <Clock className="w-2.5 h-2.5 text-slate-400 shrink-0" />
                        <span className="truncate">{idea.time_hint ?? 'No time'}</span>
                      </span>
                      {!readOnly && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingTimeVal(hintToTimeValue(idea.time_hint));
                            setEditingTimeId(idea.id);
                          }}
                          className="p-0.5 text-slate-300 hover:text-indigo-600 transition-colors opacity-0 group-hover:opacity-100 shrink-0"
                          title="Edit time"
                        >
                          <Pencil className="w-2.5 h-2.5" />
                        </button>
                      )}
                    </>
                  )}
                </div>

                {/* Row 3: [spacer] Category */}
                <div className="flex items-center gap-1.5 min-w-0">
                  <div className="w-3.5 shrink-0" />
                  <div className="min-w-0">
                    {extras[idea.id]?.category ? (
                      <span className={`inline-block text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-md truncate max-w-full ${accent.badge}`}>
                        {extras[idea.id]!.category}
                      </span>
                    ) : (
                      <span className="text-[9px] font-bold uppercase tracking-widest text-slate-300">—</span>
                    )}
                  </div>
                </div>

                {/* Row 4: [spacer] added_by | Vote */}
                <div className="flex items-center gap-1.5 min-w-0">
                  <div className="w-3.5 shrink-0" />
                  <div className="flex items-center gap-1 flex-1 min-w-0">
                    {idea.added_by ? (
                      <>
                        <UserCircle className="w-2.5 h-2.5 text-slate-400 shrink-0" />
                        <span className="text-[10px] font-bold text-slate-400 truncate">{idea.added_by}</span>
                      </>
                    ) : (
                      <span className="text-[10px] font-bold text-slate-300">—</span>
                    )}
                  </div>
                  <VoteControl kind="idea" id={idea.id} canVote={canVote} size="sm" initial={idea.up != null ? { up: idea.up ?? 0, down: idea.down ?? 0, my_vote: idea.my_vote ?? 0 } : undefined} />
                </div>
              </motion.div>
              );
            })
          )}
        </AnimatePresence>

        {openId != null && (() => {
          const idea = ideas.find((i) => i.id === openId);
          if (!idea) return null;
          const ex = extras[idea.id] ?? {};
          const accent = categoryAccent(ex.category);
          return (
            <div
              className="absolute left-5 right-5 z-20"
              style={{ top: popoverTop, height: 220 }}
            >
              <div className="h-full bg-white border border-slate-200 rounded-2xl shadow-xl flex flex-col overflow-hidden">
                <div className="flex items-start justify-between gap-2 px-3 py-2.5 border-b border-slate-100 shrink-0">
                  <div className="flex items-start gap-2 min-w-0">
                    <div className={`w-1 self-stretch rounded-full shrink-0 ${accent.bar}`} />
                    <div className="min-w-0">
                      <p className="text-xs font-black text-slate-900 leading-tight truncate">{idea.title}</p>
                      {ex.address && (
                        <p className="text-[10px] font-medium text-slate-500 truncate mt-0.5">{ex.address}</p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => setOpenId(null)}
                    className="p-0.5 text-slate-400 hover:text-slate-700 hover:bg-slate-50 rounded-md transition-colors shrink-0"
                    title="Close"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-3 space-y-2">
                  {SHOW_PHOTOS && ex.photo_url && (
                    <img
                      src={ex.photo_url}
                      alt=""
                      className="w-full h-24 object-cover rounded-lg border border-slate-100"
                    />
                  )}
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {SHOW_RATING && ex.rating != null && (
                      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded-md text-[10px] font-bold border border-amber-100">
                        <Star className="w-2.5 h-2.5 text-amber-400" /> {ex.rating}
                      </span>
                    )}
                    {idea.time_hint && (
                      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-slate-50 text-slate-700 rounded-md text-[10px] font-bold">
                        <Clock className="w-2.5 h-2.5 text-slate-500" /> {idea.time_hint}
                      </span>
                    )}
                    {ex.category && (
                      <span className={`px-1.5 py-0.5 rounded-md text-[9px] font-black uppercase tracking-widest ${accent.badge}`}>
                        {ex.category}
                      </span>
                    )}
                  </div>
                  {ex.description && (
                    <p className="text-[11px] font-medium text-slate-500 leading-relaxed">{ex.description}</p>
                  )}
                  {(!SHOW_PHOTOS || !ex.photo_url) && !ex.description && !ex.address && (
                    <p className="text-[11px] font-medium text-slate-400 italic">No additional details available.</p>
                  )}
                </div>
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
