'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useTripStore, Event, Idea, legsKey, RouteLeg } from '@/lib/store';
import { format } from 'date-fns';
import { Clock, MapPin, MoreVertical, AlertCircle, Pencil, X, GripVertical, Undo2, Check, Info, Star, UserCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import VoteControl from '@/components/trip/VoteControl';
import { categoryAccent } from '@/lib/categoryColors';

const SHOW_PHOTOS =
  (process.env.NEXT_PUBLIC_GOOGLE_MAPS_FETCH_PHOTOS ?? 'true').toLowerCase() === 'true';
const SHOW_RATING =
  (process.env.NEXT_PUBLIC_GOOGLE_MAPS_FETCH_RATING ?? 'true').toLowerCase() === 'true';

interface TimelineProps {
  tripId: string | null;
  /** When set (Concierge mode), only events on this day are shown. */
  filterDay?: Date;
  /** When true, hides move-to-bin, time editing, and drag reorder. */
  readOnly?: boolean;
  /** When true, user may cast votes on events (admin or view_with_vote). */
  canVote?: boolean;
}

/**
 * Returns the set of event IDs that conflict with any prior event in the list.
 * An event conflicts if its start_time falls before the maximum end_time of any
 * earlier event in the rendered order. Only the later item(s) in an overlap are
 * flagged. TBD events (no start_time / end_time) are skipped.
 */
function computeConflicts(events: Event[]): Set<string> {
  const conflicts = new Set<string>();
  let maxEndSoFar: Date | null = null;
  for (const ev of events) {
    if (ev.start_time && maxEndSoFar && ev.start_time < maxEndSoFar) {
      conflicts.add(ev.id);
    }
    if (ev.end_time && (!maxEndSoFar || ev.end_time > maxEndSoFar)) {
      maxEndSoFar = ev.end_time;
    }
  }
  return conflicts;
}

/** Number of dots to render between two adjacent cards (floor of hour gap, 0 if <1h or TBD). */
function gapDotCount(prev: Event, next: Event): number {
  if (!prev.end_time || !next.start_time) return 0;
  const ms = next.start_time.getTime() - prev.end_time.getTime();
  if (ms < 60 * 60 * 1000) return 0;
  return Math.floor(ms / (60 * 60 * 1000));
}

/** Format leg duration: "<60min" → "X min"; "≥60min" → "Hh" or "Hh Mm". */
function formatTravelTime(seconds: number): string {
  const mins = Math.max(1, Math.round(seconds / 60));
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

function GapDots({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <div
      data-testid={`gap-dots-${count}`}
      aria-label={`${count} hour gap`}
      className="relative py-2"
      style={{ paddingLeft: '40px' }}
    >
      <div className="absolute left-[17px] top-0 bottom-0 w-0.5 bg-indigo-100/60" />
      <div
        className="absolute flex flex-col gap-1.5"
        style={{ left: '15px', top: '8px' }}
      >
        {Array.from({ length: count }).map((_, i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full relative z-10 bg-indigo-400/70"
          />
        ))}
      </div>
      <div style={{ height: `${count * 12 + 4}px` }} />
    </div>
  );
}

/** Heuristic until backend exposes travel mode: < ~10 km/h average → walk, else drive. */
function travelMode(leg: { duration_s: number; distance_m: number }): 'walk' | 'drive' {
  const speed = leg.duration_s > 0 ? leg.distance_m / leg.duration_s : 0;
  return speed < 2.8 ? 'walk' : 'drive';
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
        className="flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-black text-amber-600 bg-amber-50 border border-amber-100 hover:bg-amber-100 transition-colors"
      >
        <Clock className="w-2.5 h-2.5" />
        TBD
        <Pencil className="w-2.5 h-2.5 ml-0.5" />
      </button>
    );
  }
  return (
    <button
      onClick={onEdit}
      data-testid={`time-badge-${event.id}`}
      className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-black transition-colors ${
        isConflict
          ? 'text-red-600 bg-red-50 border border-red-400 ring-1 ring-red-300'
          : 'text-indigo-600 bg-indigo-50 border border-indigo-100 hover:bg-indigo-100'
      }`}
    >
      {isConflict && <AlertCircle className="w-2.5 h-2.5" data-testid="conflict-icon" />}
      {format(event.start_time, 'h:mm a')}
      {event.end_time && (
        <>
          <span className="mx-0.5">–</span>
          {format(event.end_time, 'h:mm a')}
        </>
      )}
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
  const initialStart = event.start_time ? format(event.start_time, 'HH:mm') : '';
  const initialEnd = event.end_time ? format(event.end_time, 'HH:mm') : '';

  const [startVal, setStartVal] = useState(initialStart);
  const [endVal, setEndVal] = useState(initialEnd);
  const ref = useRef<HTMLDivElement>(null);

  const isDirty = startVal !== initialStart || endVal !== initialEnd;

  const handleConfirm = () => {
    const startDate = startVal ? parseTimeString(startVal) : null;
    const endDate = endVal ? parseTimeString(endVal) : null;
    if (startDate && endDate && endDate <= startDate) {
      endDate.setTime(startDate.getTime() + 3600_000);
    }
    onConfirm(startDate, endDate);
  };

  const handleClickOutside = useCallback(
    (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node) && !isDirty) {
        onCancel();
      }
    },
    [isDirty, onCancel],
  );

  useEffect(() => {
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [handleClickOutside]);

  return (
    <div ref={ref} data-testid={`time-editor-${event.id}`} className="mt-1.5 flex items-center gap-1 p-1 bg-slate-50 rounded-lg border border-slate-200">
      <input
        type="time"
        value={startVal}
        onChange={(e) => setStartVal(e.target.value)}
        aria-label="Start time"
        className="text-[11px] font-bold text-slate-700 bg-white border border-slate-200 rounded-md px-1 py-0.5 flex-1 min-w-0 focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      <span className="text-[10px] text-slate-400 shrink-0">→</span>
      <input
        type="time"
        value={endVal}
        onChange={(e) => setEndVal(e.target.value)}
        aria-label="End time"
        className="text-[11px] font-bold text-slate-700 bg-white border border-slate-200 rounded-md px-1 py-0.5 flex-1 min-w-0 focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      <div className="flex items-center gap-0.5 shrink-0">
        <button
          onClick={handleConfirm}
          disabled={!isDirty}
          aria-label="Confirm time"
          className={`p-1 rounded-md transition-colors ${
            isDirty
              ? 'bg-indigo-600 text-white hover:bg-indigo-700'
              : 'bg-indigo-300 text-indigo-100 cursor-not-allowed'
          }`}
        >
          <Check className="w-3 h-3" />
        </button>
        <button
          onClick={onCancel}
          aria-label="Cancel time edit"
          className="p-1 bg-slate-200 text-slate-500 rounded-md hover:bg-slate-300 hover:text-slate-700 transition-colors"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

export default function Timeline({ tripId, filterDay, readOnly = false, canVote = false }: TimelineProps) {
  const { events, ideas, loadEvents, moveIdeaToTimeline, moveEventToIdea, updateEventTime, reorderEvent, setEventsRaw, tripDays, legsByDay } =
    useTripStore();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [tooltipId, setTooltipId] = useState<string | null>(null);

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

  const conflictSet = computeConflicts(visibleEvents);

  const dayLegs: RouteLeg[] | null =
    tripId && filterDayStr ? legsByDay[legsKey(tripId, filterDayStr)] ?? null : null;
  const legByPair = new Map<string, RouteLeg>();
  if (dayLegs) for (const l of dayLegs) legByPair.set(`${l.from_event_id}::${l.to_event_id}`, l);

  const noDaysExist = tripDays.length === 0;

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
    e.stopPropagation();

    const token = localStorage.getItem('token');

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
              const dots = prevEvent ? gapDotCount(prevEvent, event) : 0;
              const isConflict = conflictSet.has(event.id);
              const isDragging = draggingId === event.id;
              const isDragTarget = dragOverId === event.id;
              const isTooltipOpen = tooltipId === event.id;
              const accent = categoryAccent(event.category);
              const hasDetails = !!(event.description || (SHOW_PHOTOS && event.photo_url) || (SHOW_RATING && event.rating != null) || event.address || event.added_by);

              const nextEvent = index < visibleEvents.length - 1 ? visibleEvents[index + 1] : null;
              const legToNext = nextEvent ? legByPair.get(`${event.id}::${nextEvent.id}`) : undefined;
              const travelLabel = legToNext ? formatTravelTime(legToNext.duration_s) : null;
              const travelModeLabel = legToNext ? travelMode(legToNext) : null;

              const cardEls: JSX.Element[] = [];
              if (dots > 0) {
                cardEls.push(
                  <GapDots key={`gap-${event.id}`} count={dots} />
                );
              }
              cardEls.push(
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

                  {/* Timeline dot — colored by category */}
                  <div className="absolute left-0 top-5 w-9 h-9 flex items-center justify-center">
                    <div className={`w-3.5 h-3.5 ${accent.dot} rounded-full border-[3px] border-white shadow-sm group-hover:scale-110 transition-transform z-10`} />
                  </div>

                  <div className={`p-4 bg-white border rounded-2xl shadow-sm hover:shadow-md transition-all ${
                    isConflict ? 'border-red-200' : 'border-slate-100 hover:border-indigo-100'
                  }`}>
                    {/* Row 1: grip + title (full width) */}
                    <div className="flex items-start gap-2">
                      {!readOnly && <GripVertical className="w-4 h-4 text-slate-300 group-hover:text-slate-400 shrink-0 mt-0.5 cursor-grab active:cursor-grabbing" />}
                      <h4 className="font-black text-slate-900 leading-tight flex-1 min-w-0">
                        {event.title}
                      </h4>
                    </div>

                    {/* Rows 2-4 + detail panel: indented to align with title start */}
                    <div className={!readOnly ? 'ml-6' : undefined}>
                      {/* Row 2: time range + move-to-bin */}
                      <div className="flex items-center justify-between mt-1.5">
                        <div className="flex items-center gap-2">
                          {readOnly ? (
                            event.start_time ? (
                              <span
                                data-testid={`time-badge-${event.id}`}
                                className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-black ${
                                  isConflict
                                    ? 'text-red-600 bg-red-50 border border-red-400 ring-1 ring-red-300'
                                    : 'text-indigo-600 bg-indigo-50 border border-indigo-100'
                                }`}
                              >
                                {isConflict && <AlertCircle className="w-2.5 h-2.5" />}
                                {format(event.start_time, 'h:mm a')}
                                {event.end_time && (
                                  <>
                                    <span className="mx-0.5">–</span>
                                    {format(event.end_time, 'h:mm a')}
                                  </>
                                )}
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-black text-amber-600 bg-amber-50 border border-amber-100">
                                <Clock className="w-2.5 h-2.5" />
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
                        </div>
                        {!readOnly && (
                          <button
                            title="Send back to Idea Bin"
                            data-testid={`move-to-bin-${event.id}`}
                            onClick={() => {
                              const token = localStorage.getItem('token');
                              moveEventToIdea(event.id, tripId, token);
                            }}
                            className="flex items-center gap-1 text-[10px] font-bold text-slate-400 hover:text-red-500 uppercase tracking-tighter transition-colors opacity-0 group-hover:opacity-100"
                          >
                            <Undo2 className="w-2.5 h-2.5" />
                            Move to bin
                          </button>
                        )}
                      </div>

                      {/* Time editor (inserted below time row, pushes rows 3-4 down) */}
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

                      {/* Row 3: category */}
                      <div className="mt-1.5">
                        {event.category ? (
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${accent.badge}`}>
                            {event.category}
                          </span>
                        ) : (
                          <div className="flex items-center gap-1 text-slate-400 text-[10px] font-bold">
                            <MapPin className="w-2.5 h-2.5" />
                            <span>Activity</span>
                          </div>
                        )}
                      </div>

                      {/* Row 4: details + votes */}
                      <div className="flex items-center justify-between mt-1.5">
                        <div>
                          {hasDetails && (
                            <button
                              onClick={() => setTooltipId(isTooltipOpen ? null : event.id)}
                            className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-bold transition-colors ${
                              isTooltipOpen
                                ? 'bg-indigo-600 text-white'
                                : 'text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 border border-transparent hover:border-indigo-100'
                            }`}
                              title="Details"
                            >
                              <Info className="w-3 h-3" />
                              {isTooltipOpen ? 'Hide' : 'Details'}
                            </button>
                          )}
                        </div>
                        <div onClick={(e) => e.stopPropagation()} onMouseDown={(e) => e.stopPropagation()}>
                          <VoteControl kind="event" id={event.id} canVote={canVote} size="sm" initial={event.up != null ? { up: event.up ?? 0, down: event.down ?? 0, my_vote: event.my_vote ?? 0 } : undefined} />
                        </div>
                      </div>

                      {/* Inline detail panel */}
                      <AnimatePresence>
                        {isTooltipOpen && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-3 p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-2">
                              {SHOW_PHOTOS && event.photo_url && (
                                <img
                                  src={event.photo_url}
                                  alt=""
                                  className="w-full h-28 object-cover rounded-lg border border-slate-100"
                                />
                              )}
                              <div className="flex items-center gap-1.5 flex-wrap">
                                {SHOW_RATING && event.rating != null && (
                                  <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-amber-50 text-amber-700 rounded-md text-[10px] font-bold border border-amber-100">
                                    <Star className="w-2.5 h-2.5 text-amber-400" /> {event.rating}
                                  </span>
                                )}
                                {event.added_by && (
                                  <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-slate-100 text-slate-600 rounded-md text-[10px] font-bold">
                                    <UserCircle className="w-2.5 h-2.5" /> {event.added_by}
                                  </span>
                                )}
                              </div>
                              {event.address && (
                                <div className="flex items-start gap-1 text-[10px] font-medium text-slate-500">
                                  <MapPin className="w-2.5 h-2.5 shrink-0 mt-0.5 text-slate-400" />
                                  <span>{event.address}</span>
                                </div>
                              )}
                              {event.description && (
                                <p className="text-xs font-medium text-slate-500 leading-relaxed">{event.description}</p>
                              )}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                  </div>
                  {travelLabel && travelModeLabel && (
                    <p
                      data-testid={`travel-hint-${event.id}`}
                      className="mt-1.5 text-center text-[11px] italic text-slate-400 font-medium"
                    >
                      {travelLabel} {travelModeLabel} to next destination
                    </p>
                  )}
                </motion.div>
              );
              return cardEls;
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
