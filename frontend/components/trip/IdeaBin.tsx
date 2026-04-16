'use client';

import { useState, useEffect } from 'react';
import { useTripStore } from '@/lib/store';
import { MapPin, Loader2, Sparkles, Plus, Clock, Pencil, Trash2, Check, X, UserCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

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

export default function IdeaBin({ tripId, readOnly = false }: { tripId: string | null; readOnly?: boolean }) {
  // readOnly = non-admin user. They CAN add ideas but CANNOT delete/edit time/drag-to-timeline.
  const [inputText, setInputText] = useState('');
  const [isIngesting, setIsIngesting] = useState(false);
  const [editingTimeId, setEditingTimeId] = useState<string | null>(null);
  const [editingTimeVal, setEditingTimeVal] = useState('');
  const { ideas, addIdea, setIdeas, removeIdea } = useTripStore();

  // Load ideas from API on mount
  useEffect(() => {
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
          }))
        );
      })
      .catch(() => {});
  }, [tripId, setIdeas]);

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

      // Fallback / demo mode: parse locally with time extraction
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

      <div className="flex-1 overflow-y-auto p-6 space-y-3">
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
            ideas.map((idea) => (
              <motion.div
                key={idea.id}
                layout
                initial={{ opacity: 0, scale: 0.9, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8 }}
                draggable={!readOnly}
                onDragStartCapture={(e) => { if (!readOnly) e.dataTransfer.setData('ideaId', idea.id); }}
                data-testid={`idea-card-${idea.id}`}
                className="p-4 bg-white border border-slate-100 rounded-2xl shadow-sm cursor-grab active:cursor-grabbing hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-50/50 transition-all group relative overflow-hidden"
              >
                <div className="absolute top-0 left-0 w-1 h-full bg-indigo-100 group-hover:bg-indigo-500 transition-colors" />
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-slate-50 text-slate-400 group-hover:bg-indigo-50 group-hover:text-indigo-600 rounded-xl transition-colors shrink-0 mt-0.5">
                    <MapPin className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-black text-slate-800 block truncate">
                      {idea.title}
                    </span>

                    {!readOnly && editingTimeId === idea.id ? (
                      <div className="flex items-center gap-1.5 mt-1.5">
                        <input
                          autoFocus
                          type="time"
                          value={editingTimeVal}
                          onChange={(e) => setEditingTimeVal(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleSaveTime(idea.id)}
                          className="w-24 px-2 py-0.5 text-[11px] font-bold border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
                        />
                        <button
                          onClick={() => handleSaveTime(idea.id)}
                          className="p-0.5 bg-indigo-600 text-white rounded-md hover:bg-indigo-500 transition-colors"
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
                      <div className="flex items-center gap-1.5 mt-1">
                        {idea.time_hint ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-50 text-amber-600 rounded-lg text-[10px] font-bold">
                            <Clock className="w-2.5 h-2.5" />
                            {idea.time_hint}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-50 text-slate-400 rounded-lg text-[10px] font-bold">
                            <Clock className="w-2.5 h-2.5" />
                            No time
                          </span>
                        )}
                        {!readOnly && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingTimeVal(hintToTimeValue(idea.time_hint));
                              setEditingTimeId(idea.id);
                            }}
                            className="p-0.5 text-slate-300 hover:text-indigo-500 transition-colors opacity-0 group-hover:opacity-100"
                            title="Edit time"
                          >
                            <Pencil className="w-2.5 h-2.5" />
                          </button>
                        )}
                      </div>
                    )}
                    {idea.added_by && (
                      <div className="flex items-center gap-1 mt-1">
                        <UserCircle className="w-2.5 h-2.5 text-slate-400" />
                        <span className="text-[10px] font-bold text-slate-400">{idea.added_by}</span>
                      </div>
                    )}
                  </div>

                  {!readOnly && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteIdea(idea.id); }}
                      className="p-1.5 text-slate-300 hover:text-rose-500 transition-colors opacity-0 group-hover:opacity-100 shrink-0"
                      title="Delete idea"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
