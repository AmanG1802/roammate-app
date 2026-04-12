'use client';

import { useState } from 'react';
import { useTripStore } from '@/lib/store';
import { Clock, SkipForward, Coffee, MessageSquare, Loader2 } from 'lucide-react';

export default function ConciergeActionBar() {
  const [isProcessing, setIsProcessing] = useState(false);
  const { activeTripId, events, setEvents } = useTripStore();

  const handleRunningLate = async (minutes: number) => {
    if (!activeTripId) return;
    setIsProcessing(true);
    
    try {
      // Logic for actual backend call:
      // const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/events/ripple/${activeTripId}`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ delta_minutes: minutes }),
      // });
      // const updatedEvents = await response.json();
      // setEvents(updatedEvents);

      // Mocking for now to show UI feedback
      const updatedEvents = events.map(event => ({
        ...event,
        start_time: new Date(event.start_time.getTime() + minutes * 60 * 1000),
        end_time: new Date(event.end_time.getTime() + minutes * 60 * 1000),
      }));
      
      // Update store
      useTripStore.setState({ events: updatedEvents });
      
    } catch (error) {
      console.error('Error triggering ripple:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 p-2 bg-white/80 backdrop-blur-md border border-slate-200 rounded-2xl shadow-2xl">
      <button 
        onClick={() => handleRunningLate(30)}
        disabled={isProcessing || events.length === 0}
        className="flex items-center gap-2 px-4 py-2.5 bg-rose-50 text-rose-600 rounded-xl font-bold hover:bg-rose-100 transition-colors disabled:opacity-50"
      >
        {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4" />}
        <span>Running 30m Late</span>
      </button>

      <div className="w-px h-6 bg-slate-200 mx-1" />

      <button className="p-2.5 text-slate-600 hover:bg-slate-100 rounded-xl transition-colors" title="Skip Next">
        <SkipForward className="w-5 h-5" />
      </button>

      <button className="p-2.5 text-slate-600 hover:bg-slate-100 rounded-xl transition-colors" title="Find Coffee">
        <Coffee className="w-5 h-5" />
      </button>

      <button className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-200 ml-2">
        <MessageSquare className="w-4 h-4" />
        <span>Chat Now</span>
      </button>
    </div>
  );
}
