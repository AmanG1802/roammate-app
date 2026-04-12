'use client';

import { useState, useEffect } from 'react';
import { useTripStore } from '@/lib/store';
import { Sun, Coffee, Zap, Moon, X, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function VibeCheck() {
  const [isVisible, setIsVisible] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const { events } = useTripStore();

  // Show vibe check if there are events and it hasn't been shown this "session"
  useEffect(() => {
    if (events.length > 0) {
      const timer = setTimeout(() => setIsVisible(true), 2000);
      return () => clearTimeout(timer);
    }
  }, [events.length]);

  const handleVibeSelect = async (vibe: 'low' | 'medium' | 'high') => {
    setIsProcessing(true);
    
    // Logic for actual backend call to LLM:
    // "User is feeling 'Low Energy'. Suggest changes to the itinerary to be more relaxed."
    // For now, we simulate a 1-second "Concierge is thinking" state
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Mock response: If Low Energy, suggest pushing everything back or adding more coffee breaks
    console.log(`Adapting itinerary for ${vibe} energy...`);
    
    setIsProcessing(false);
    setIsVisible(false);
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div 
          initial={{ opacity: 0, y: 50, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          className="absolute top-6 left-1/2 -translate-x-1/2 z-50 w-[400px]"
        >
          <div className="bg-white rounded-3xl shadow-2xl border border-indigo-100 p-6 overflow-hidden relative">
            {/* Background Decoration */}
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-indigo-50 rounded-full blur-3xl opacity-60" />
            
            <button 
              onClick={() => setIsVisible(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="relative">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-amber-50 text-amber-500 rounded-xl">
                  <Sun className="w-5 h-5" />
                </div>
                <h3 className="text-xl font-bold text-slate-800">Morning Vibe Check</h3>
              </div>

              <p className="text-slate-600 mb-6">
                Good morning! How energetic are we feeling for today's Rome adventure?
              </p>

              {isProcessing ? (
                <div className="flex flex-col items-center py-4 gap-3">
                  <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
                  <p className="text-sm font-medium text-indigo-600">Concierge is optimizing your day...</p>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-3">
                  <button 
                    onClick={() => handleVibeSelect('low')}
                    className="flex flex-col items-center gap-2 p-4 rounded-2xl border border-slate-100 hover:border-indigo-200 hover:bg-indigo-50 transition-all group"
                  >
                    <Moon className="w-6 h-6 text-slate-400 group-hover:text-indigo-500" />
                    <span className="text-xs font-bold text-slate-500 group-hover:text-indigo-700 uppercase tracking-wider">Chill</span>
                  </button>

                  <button 
                    onClick={() => handleVibeSelect('medium')}
                    className="flex flex-col items-center gap-2 p-4 rounded-2xl border border-slate-100 hover:border-indigo-200 hover:bg-indigo-50 transition-all group"
                  >
                    <Coffee className="w-6 h-6 text-slate-400 group-hover:text-indigo-500" />
                    <span className="text-xs font-bold text-slate-500 group-hover:text-indigo-700 uppercase tracking-wider">Steady</span>
                  </button>

                  <button 
                    onClick={() => handleVibeSelect('high')}
                    className="flex flex-col items-center gap-2 p-4 rounded-2xl border border-slate-100 hover:border-indigo-200 hover:bg-indigo-50 transition-all group"
                  >
                    <Zap className="w-6 h-6 text-slate-400 group-hover:text-indigo-500" />
                    <span className="text-xs font-bold text-slate-500 group-hover:text-indigo-700 uppercase tracking-wider">Active</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
