'use client';

import { useState, useEffect } from 'react';
import { useTripStore, Event, Idea } from '@/lib/store';
import { format } from 'date-fns';
import { Clock, MapPin, MoreVertical, AlertCircle, Pencil, X, GripVertical, Undo2, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface TimelineProps {
  tripId: string | null;
  /** When set (Concierge mode), only events on this day are shown. */
  filterDay?: Date;
  /** When true, hides move-to-bin, time editing, and drag reorder. */
  readOnly?: boolean;
}

/** Returns true if event A's end_time overlaps event B's start_time. */
function hasConflict(a: Event, b: Event): boolean {
  if (!a.end_time || !b.start_time) return false;
  return a.end_time > b.start_time;
}

/** Parse a time string like "2pm", "14:00", "2:30 PM" into a Date for today. */
function parseTimeString(raw: string): Date | null {
  const s = raw.trim().toLowerCase();
  const ampmMatch = s.match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$/);
  const militaryMatch = s.match(/^(\d{1,2}):(\d{2})$/);

  const d = new Date();
  if (ampmMatch) {
    let h = parseInt(ampmMatch[1], 10);
    const m = parseInt(ampmMatch[2] ?? '0', 10);
    if (ampmMatch[3] === 'pm' && h !== 12) h += 12;
    if (ampmMatch[3] === 'am' && h === 12) h = 0;
    d.setHours(h, m, 0, 0);
    return d;
  }
  if (militaryMatch) {
    d.setHours(parseInt(militaryMatch[1], 10), parseInt(militaryMatch[2], 10), 0, 0);
    return d;
  }
  return null;
}

function TimeDisplay({
  event,
  isConflict,
  onEdit,
}: {
  event: Event;
  isConflict: boolean;
  onEdit: () => void;
}) {
  if (!event.start_time) {
    return (
      <button
        onClick={onEdit}
        data-testid={`tbd-badge-${event.id}`}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-black text-amber-600 bg-amber-50 border border-amber-100 hover:bg-amber-100 transition-colors"
      >
        <Clock className="w-3 h-3" />
        TBD
        <Pencil className="w-2.5 h-2.5 ml-0.5" />
      </button>
    );
  }
  return (
    <button
      onClick={onEdit}
      data-testid={`time-badge-${event.id}`}
      className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-black transition-colors ${
        isConflict
          ? 'text-red-600 bg-red-50 border border-red-400 ring-1 ring-red-300'
          : 'text-indigo-600 bg-indigo-50 border border-indigo-100 hover:bg-indigo-100'
      }`}
    >
      {isConflict && <AlertCircle className="w-3 h-3" data-testid="conflict-icon" />}
      {format(event.start_time, 'h:mm a')}
      <Pencil className="w-2.5 h-2.5 ml-0.5" />
    </button>
  );
}

function TimeEditor({
  event,
  onConfirm,
  onCancel,
}: {
  event: Event;
  onConfirm: (start: Date | null, end: Date | null) => void;
  onCancel: () => void;
}) {
  const [startVal, setStartVal] = useState(
    event.start_time ? format(event.start_time, 'HH:mm') : ''
  );
  const [endVal, setEndVal] = useState(
    event.end_time ? format(event.end_time, 'HH:mm') : ''
  );

  const handleConfirm = () => {
    const startDate = startVal ? parseTimeString(startVal) : null;
    const endDate = endVal ? parseTimeString(endVal) : null;
    if (startDate && endDate && endDate <= startDate) {
      endDate.setTime(startDate.getTime() + 3600_000);
    }
    onConfirm(startDate, endDate);
  };

  return (
    <div data-testid={`time-editor-${event.id}`} className="mt-2 flex items-center gap-2 p-2 bg-slate-50 rounded-xl border border-slate-200">
      <input
        type="time"
        value={startVal}
        onChange={(e) => setStartVal(e.target.value)}
        aria-label="Start time"
        className="text-xs font-bold text-slate-700 bg-white border border-slate-200 rounded-lg px-2 py-1 w-28 focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      <span className="text-xs text-slate-400">→</span>
      <input
        type="time"
        value={endVal}
        onChange={(e) => setEndVal(e.target.value)}
        aria-label="End time"
        className="text-xs font-bold text-slate-700 bg-white border border-slate-200 rounded-lg px-2 py-1 w-28 focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      <button
        onClick={handleConfirm}
        aria-label="Confirm time"
        className="p-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
      >
        <Check className="w-3 h-3" />
      </button>
      <button
        onClick={onCancel}
        aria-label="Cancel time edit"
        className="p-1.5 text-slate-400 hover:text-slate-600 transition-colors"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}

export default function Timeline({ tripId, filterDay, readOnly = false }: TimelineProps) {
  const { events, ideas, loadEvents, moveIdeaToTimeline, moveEventToIdea, updateEventTime, reorderEvent, setEventsRaw, tripDays } =
    useTripStore();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);

  // Load persisted events from API on mount
  useEffect(() => {
    if (!tripId) return;
    const token = localStorage.getItem('token');
    if (!token) return;
    loadEvents(tripId, token);
  }, [tripId, loadEvents]);

  const filterDayStr = filterDay
    ? `${filterDay.getFullYear()}-${String(filterDay.getMonth() + 1).padStart(2, '0')}-${String(filterDay.getDate()).padStart(2, '0')}`
    : null;

  const visibleEvents = filterDayStr
    ? events.filter((e) => e.day_date === filterDayStr)
    : events;

  const noDaysExist = tripDays.length === 0;

  // ── Drag from Idea Bin → Timeline (onto empty area) ───────────────────────
  const handleDropFromBin = (e: React.DragEvent) => {
    e.preventDefault();
    if (readOnly) return;
    const ideaId = e.dataTransfer.getData('ideaId');
    if (!ideaId) return;
    if (noDaysExist) return;
    const token = localStorage.getItem('token');
    const idea = ideas.find((i: Idea) => i.id === ideaId);
    const startTime = idea?.time_hint ? parseTimeString(idea.time_hint) : null;
    moveIdeaToTimeline(ideaId, tripId, token, startTime, filterDayStr);
  };

  // ── Per-event drag handlers ───────────────────────────────────────────────
  const handleEventDragStart = (e: React.DragEvent, eventId: string) => {
    e.dataTransfer.setData('reorderEventId', eventId);
    setDraggingId(eventId);
  };

  const handleEventDragOver = (e: React.DragEvent, overEventId: string) => {
    e.preventDefault();
    setDragOverId(overEventId);
  };

  const handleEventDrop = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    // Stop propagation so the outer handleDropFromBin doesn't also fire
    e.stopPropagation();

    const token = localStorage.getItem('token');

    // ── Case 1: idea dropped from Idea Bin onto an event card ─────────────
    const ideaId = e.dataTransfer.getData('ideaId');
    if (ideaId) {
      if (noDaysExist) { setDraggingId(null); setDragOverId(null); return; }
      const idea = ideas.find((i: Idea) => i.id === ideaId);
      const startTime = idea?.time_hint ? parseTimeString(idea.time_hint) : null;
      moveIdeaToTimeline(ideaId, tripId, token, startTime, filterDayStr);
      setDraggingId(null);
      setDragOverId(null);
      return;
    }

    // ── Case 2: event reorder (drag within timeline) ───────────────────────
    const sourceId = e.dataTransfer.getData('reorderEventId');
    if (!sourceId || sourceId === targetId) {
      setDraggingId(null);
      setDragOverId(null);
      return;
    }

    const ordered = [...events];
    const srcIdx = ordered.findIndex((ev) => ev.id === sourceId);
    if (srcIdx === -1) return;

    const [moved] = ordered.splice(srcIdx, 1);
    const insertAt = ordered.findIndex((ev) => ev.id === targetId);
    if (insertAt === -1) return;
    ordered.splice(insertAt, 0, moved);

    const updated = ordered.map((ev, i) => ({ ...ev, sort_order: i }));
    // Use setEventsRaw so sortEvents doesn't undo the manual drag order.
    setEventsRaw(updated);
    updated.forEach((ev) => reorderEvent(ev.id, ev.sort_order, token));

    setDraggingId(null);
    setDragOverId(null);
  };

  const handleEventDragEnd = () => {
    setDraggingId(null);
    setDragOverId(null);
  };

  return (
    <div
      data-testid="timeline-container"
      className="flex-1 overflow-y-auto p-5"
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDropFromBin}
    >
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-black text-slate-900 tracking-tight">
          {filterDay ? format(filterDay, 'EEEE, MMM d') : 'Full Itinerary'}
        </h2>
        <button className="p-1.5 text-slate-400 hover:text-slate-600 transition-colors">
          <MoreVertical className="w-4 h-4" />
        </button>
      </div>

      {visibleEvents.length === 0 ? (
        <div
          data-testid="empty-drop-zone"
          className="flex flex-col items-center justify-center py-20 border-2 border-dashed border-slate-200 rounded-[2rem] opacity-60"
        >
          <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center mb-3">
            <Clock className="w-7 h-7 text-indigo-400" />
          </div>
          <p className="text-base font-black text-slate-900 mb-1">
            {noDaysExist ? 'Add a day first' : filterDay ? 'No events for this day' : 'Build your day'}
          </p>
          <p className="text-sm text-slate-400 font-medium text-center px-4">
            {noDaysExist ? 'Click "Add Day" before adding items.' : 'Drag items from the Idea Bin to start.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3 relative before:absolute before:left-[17px] before:top-4 before:bottom-4 before:w-0.5 before:bg-indigo-100/60">
          <AnimatePresence initial={false}>
            {visibleEvents.map((event, index) => {
              const prevEvent = index > 0 ? visibleEvents[index - 1] : null;
              const isConflict = prevEvent ? hasConflict(prevEvent, event) : false;
              const isDragging = draggingId === event.id;
              const isDragTarget = dragOverId === event.id;

              return (
                /*
                 * draggable + drag handlers are on motion.div directly.
                 *
                 * onDragStartCapture (capture phase) is used instead of onDragStart because
                 * framer-motion overrides the onDragStart prop with its own pointer-event
                 * handler. The capture variant is not overridden and carries the correct
                 * React.DragEvent type with a valid dataTransfer object.
                 *
                 * onDragOver, onDrop, onDragEndCapture are standard React HTML events that
                 * framer-motion does NOT override, so they work without the Capture suffix.
                 */
                <motion.div
                  key={event.id}
                  layout
                  initial={{ opacity: 0, x: -16 }}
                  animate={{ opacity: isDragging ? 0.4 : 1, x: 0 }}
                  exit={{ opacity: 0, x: -16 }}
                  draggable={!readOnly}
                  onDragStartCapture={(e) => { if (!readOnly) handleEventDragStart(e, event.id); }}
                  onDragOver={(e) => { if (!readOnly) handleEventDragOver(e, event.id); }}
                  onDrop={(e) => { if (!readOnly) handleEventDrop(e, event.id); }}
                  onDragEndCapture={() => { if (!readOnly) handleEventDragEnd(); }}
                  data-testid={`event-card-${event.id}`}
                  className={`relative pl-10 group transition-all ${isDragTarget ? 'scale-[1.02]' : ''}`}
                >
                  {isDragTarget && (
                    <div className="absolute top-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-full -translate-y-2" />
                  )}

                  <div className="absolute left-0 top-5 w-9 h-9 flex items-center justify-center">
                    <div className="w-3.5 h-3.5 bg-indigo-600 rounded-full border-[3px] border-white shadow-sm group-hover:scale-110 transition-transform z-10" />
                  </div>

                  <div className={`p-4 bg-white border rounded-2xl shadow-sm hover:shadow-md transition-all ${
                    isConflict ? 'border-red-200' : 'border-slate-100 hover:border-indigo-100'
                  }`}>
                    <div className="flex justify-between items-start">
                      <div className="flex items-start gap-2 flex-1 min-w-0">
                        {!readOnly && <GripVertical className="w-4 h-4 text-slate-300 group-hover:text-slate-400 shrink-0 mt-0.5 cursor-grab active:cursor-grabbing" />}
                        <div className="flex-1 min-w-0">
                          <h4 className="font-black text-slate-900 leading-tight mb-0.5 truncate">
                            {event.title}
                          </h4>
                          <div className="flex items-center gap-1 text-slate-400 text-[10px] font-bold uppercase tracking-widest">
                            <MapPin className="w-2.5 h-2.5" />
                            <span>Activity</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-col items-end gap-1 shrink-0 ml-3">
                        {readOnly ? (
                          /* Read-only time badge — no pencil, no click */
                          event.start_time ? (
                            <span className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-black ${
                              isConflict
                                ? 'text-red-600 bg-red-50 border border-red-400 ring-1 ring-red-300'
                                : 'text-indigo-600 bg-indigo-50 border border-indigo-100'
                            }`}>
                              {isConflict && <AlertCircle className="w-3 h-3" />}
                              {format(event.start_time, 'h:mm a')}
                            </span>
                          ) : (
                            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-black text-amber-600 bg-amber-50 border border-amber-100">
                              <Clock className="w-3 h-3" />
                              TBD
                            </span>
                          )
                        ) : (
                          <TimeDisplay
                            event={event}
                            isConflict={isConflict}
                            onEdit={() => setEditingId(event.id)}
                          />
                        )}
                        {!readOnly && (
                          <button
                            title="Send back to Idea Bin"
                            data-testid={`move-to-bin-${event.id}`}
                            onClick={() => {
                              const token = localStorage.getItem('token');
                              moveEventToIdea(event.id, tripId, token);
                            }}
                            className="flex items-center gap-1 text-[9px] font-black text-slate-400 hover:text-red-500 uppercase tracking-tighter transition-colors opacity-0 group-hover:opacity-100"
                          >
                            <Undo2 className="w-2.5 h-2.5" />
                            Move to bin
                          </button>
                        )}
                      </div>
                    </div>

                    {!readOnly && editingId === event.id && (
                      <TimeEditor
                        event={event}
                        onConfirm={(start, end) => {
                          const token = localStorage.getItem('token');
                          updateEventTime(event.id, start, end, token);
                          setEditingId(null);
                        }}
                        onCancel={() => setEditingId(null)}
                      />
                    )}

                    {event.start_time && event.end_time && editingId !== event.id && (
                      <div className="mt-2 text-xs text-slate-400 font-medium">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {format(event.start_time, 'h:mm a')} – {format(event.end_time, 'h:mm a')}
                      </div>
                    )}

                    {index < visibleEvents.length - 1 && !filterDay && (
                      <div className="mt-3 flex items-center gap-2 px-3 py-2 bg-slate-50 rounded-xl text-[10px] text-slate-500 font-bold">
                        <span>~15 min transit</span>
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
