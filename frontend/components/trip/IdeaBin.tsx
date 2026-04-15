'use client';

import { useState, useEffect } from 'react';
import { useTripStore } from '@/lib/store';
import { MapPin, Loader2, Sparkles, Plus, Clock } from 'lucide-react';
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

export default function IdeaBin({ tripId }: { tripId: string | null }) {
  const [inputText, setInputText] = useState('');
  const [isIngesting, setIsIngesting] = useState(false);
  const { ideas, addIdea, setIdeas } = useTripStore();

  // Load ideas from API on mount
  useEffect(() => {
    if (!tripId) return;
    const token = localStorage.getItem('token');
    if (!token) return;

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/ideas`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((data: any[]) => {
        setIdeas(
          data.map((item) => ({
            id: item.id.toString(),
            title: item.title,
            lat: item.lat ?? 0,
            lng: item.lng ?? 0,
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
              time_hint: extractTimeHint(fragment),
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
              /*
               * NOTE: draggable + onDragStartCapture MUST be on the motion.div itself.
               * Putting them on a wrapper div causes framer-motion's inner pointer-event
               * listeners (for layout animation tracking) to swallow the mousedown before
               * the browser can recognise a native drag on the parent.
               *
               * onDragStartCapture (capture phase) is used instead of onDragStart because
               * framer-motion overrides the onDragStart prop with its own pointer-event
               * handler type. The capture variant is not overridden and receives the correct
               * React.DragEvent type with a valid dataTransfer object.
               */
              <motion.div
                key={idea.id}
                layout
                initial={{ opacity: 0, scale: 0.9, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8 }}
                draggable
                onDragStartCapture={(e) => e.dataTransfer.setData('ideaId', idea.id)}
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
                    {idea.time_hint && (
                      <span
                        data-testid={`time-hint-badge-${idea.id}`}
                        className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 bg-amber-50 text-amber-600 rounded-lg text-[10px] font-bold"
                      >
                        <Clock className="w-2.5 h-2.5" />
                        {idea.time_hint}
                      </span>
                    )}
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
