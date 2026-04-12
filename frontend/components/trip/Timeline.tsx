'use client';

import { useTripStore } from '@/lib/store';
import { format, isSameDay } from 'date-fns';
import { Clock, Navigation, MapPin, MoreVertical, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';

interface TimelineProps {
  tripId: string | null;
  /** When set (Concierge mode), only events on this day are shown. */
  filterDay?: Date;
}

export default function Timeline({ tripId, filterDay }: TimelineProps) {
  const { events, moveIdeaToTimeline } = useTripStore();

  const visibleEvents = filterDay
    ? events.filter((e) => isSameDay(new Date(e.start_time), filterDay))
    : events;

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const ideaId = e.dataTransfer.getData('ideaId');
    if (!ideaId) return;
    const lastEvent = events[events.length - 1];
    const nextTime = lastEvent
      ? new Date(lastEvent.end_time.getTime() + 30 * 60 * 1000)
      : new Date(new Date().setHours(9, 0, 0, 0));
    moveIdeaToTimeline(ideaId, nextTime);
  };

  return (
    <div
      className="flex-1 overflow-y-auto p-5"
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
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
        <div className="flex flex-col items-center justify-center py-20 border-2 border-dashed border-slate-200 rounded-[2rem] opacity-60">
          <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center mb-3">
            <Clock className="w-7 h-7 text-indigo-400" />
          </div>
          <p className="text-base font-black text-slate-900 mb-1">
            {filterDay ? 'No events for this day' : 'Build your day'}
          </p>
          <p className="text-sm text-slate-400 font-medium text-center px-4">
            {filterDay ? 'Switch to Plan mode to add events.' : 'Drag items from the Idea Bin to start.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3 relative before:absolute before:left-[17px] before:top-4 before:bottom-4 before:w-0.5 before:bg-indigo-100/60">
          {visibleEvents.map((event, index) => (
            <motion.div
              layout
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              key={event.id}
              className="relative pl-10 group"
            >
              <div className="absolute left-0 top-5 w-9 h-9 flex items-center justify-center">
                <div className="w-3.5 h-3.5 bg-indigo-600 rounded-full border-[3px] border-white shadow-sm group-hover:scale-110 transition-transform z-10" />
              </div>

              <div className="p-4 bg-white border border-slate-100 rounded-2xl shadow-sm hover:shadow-md hover:border-indigo-100 transition-all">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h4 className="font-black text-slate-900 leading-tight mb-0.5">{event.title}</h4>
                    <div className="flex items-center gap-1 text-slate-400 text-[10px] font-bold uppercase tracking-widest">
                      <MapPin className="w-2.5 h-2.5" />
                      <span>Activity</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0 ml-3">
                    <span className="text-xs font-black text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-lg">
                      {format(event.start_time, 'h:mm a')}
                    </span>
                    {index === 0 && (
                      <div className="flex items-center gap-1 text-[9px] font-black text-amber-600 uppercase tracking-tighter">
                        <AlertCircle className="w-2.5 h-2.5" />
                        Anchor
                      </div>
                    )}
                  </div>
                </div>

                <div className="text-xs text-slate-400 font-medium">
                  <Clock className="w-3 h-3 inline mr-1" />
                  {format(event.start_time, 'h:mm a')} – {format(event.end_time, 'h:mm a')}
                </div>

                {index < visibleEvents.length - 1 && (
                  <div className="mt-3 flex items-center gap-2 px-3 py-2 bg-slate-50 rounded-xl text-[10px] text-slate-500 font-bold">
                    <Navigation className="w-3 h-3 text-indigo-400 shrink-0" />
                    <span>~15 min transit</span>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
