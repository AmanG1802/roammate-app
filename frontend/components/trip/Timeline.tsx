'use client';

import { useTripStore } from '@/lib/store';
import { format } from 'date-fns';
import { Clock, Navigation, MapPin, MoreVertical, GripVertical, AlertCircle } from 'lucide-react';
import { motion, Reorder } from 'framer-motion';

export default function Timeline({ tripId }: { tripId: string | null }) {
  const { events, moveIdeaToTimeline, setEvents } = useTripStore();

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const ideaId = e.dataTransfer.getData('ideaId');
    if (ideaId) {
      const lastEvent = events[events.length - 1];
      const nextTime = lastEvent 
        ? new Date(lastEvent.end_time.getTime() + 30 * 60 * 1000) 
        : new Date(new Date().setHours(9, 0, 0, 0));

      moveIdeaToTimeline(ideaId, nextTime);
    }
  };

  return (
    <div 
      className="flex-1 overflow-y-auto bg-slate-50/50 p-6 relative"
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
    >
      <div className="max-w-xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-black text-slate-900 tracking-tight">Your Itinerary</h2>
            <p className="text-slate-500 font-medium">Day 1: Arrival & Exploring Rome</p>
          </div>
          <button className="p-2 bg-white rounded-xl border border-slate-200 shadow-sm text-slate-400 hover:text-slate-600 transition-colors">
            <MoreVertical className="w-5 h-5" />
          </button>
        </div>
        
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 border-2 border-dashed border-slate-200 rounded-[2.5rem] bg-white shadow-sm opacity-60">
            <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4">
              <Clock className="w-8 h-8 text-indigo-400" />
            </div>
            <p className="text-xl font-black text-slate-900 mb-2">Build your day</p>
            <p className="text-slate-500 font-medium">Drag items from the Idea Bin to start planning</p>
          </div>
        ) : (
          <div className="space-y-4 relative before:absolute before:left-[19px] before:top-4 before:bottom-4 before:w-0.5 before:bg-indigo-100/50">
            {events.map((event, index) => (
              <motion.div 
                layout
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                key={event.id} 
                className="relative pl-12 group"
              >
                {/* Connector Dot */}
                <div className="absolute left-0 top-6 w-10 h-10 flex items-center justify-center">
                  <div className="w-4 h-4 bg-indigo-600 rounded-full border-4 border-white shadow-md group-hover:scale-125 transition-transform z-10" />
                </div>

                <div className="p-5 bg-white border border-slate-100 rounded-2xl shadow-sm hover:shadow-xl hover:shadow-indigo-50/50 hover:border-indigo-100 transition-all cursor-default">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-start gap-3">
                      <div className="mt-1 opacity-0 group-hover:opacity-40 cursor-grab active:cursor-grabbing">
                        <GripVertical className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="font-black text-slate-900 text-lg leading-tight mb-1">{event.title}</h4>
                        <div className="flex items-center gap-1.5 text-slate-400 font-bold text-xs uppercase tracking-widest">
                          <MapPin className="w-3 h-3" />
                          <span>Historical Landmark</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className="text-sm font-black text-indigo-600 bg-indigo-50 px-3 py-1.5 rounded-xl">
                        {format(event.start_time, 'h:mm a')}
                      </span>
                      {index === 0 && (
                        <div className="flex items-center gap-1 text-[10px] font-black text-amber-600 uppercase tracking-tighter">
                          <AlertCircle className="w-3 h-3" />
                          Anchor Constraint
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-6 text-sm text-slate-500 font-medium mb-2">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-slate-300" />
                      <span>{format(event.start_time, 'h:mm a')} - {format(event.end_time, 'h:mm a')}</span>
                    </div>
                  </div>

                  {index < events.length - 1 && (
                    <div className="mt-4 flex items-center gap-3 px-4 py-3 bg-slate-50 rounded-xl text-xs text-slate-600 font-bold tracking-tight">
                      <div className="p-1.5 bg-white rounded-lg shadow-sm">
                        <Navigation className="w-3.5 h-3.5 text-indigo-500" />
                      </div>
                      <span>15 min transit via Walking</span>
                      <div className="flex-1 h-px bg-slate-200 mx-2" />
                      <span className="text-slate-400 font-medium">800m away</span>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
