'use client';

import { useState } from 'react';
import { useTripStore } from '@/lib/store';
import { Send, MapPin, Loader2, Sparkles, X, Plus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function IdeaBin({ tripId }: { tripId: string | null }) {
  const [inputText, setInputText] = useState('');
  const [isIngesting, setIsIngesting] = useState(false);
  const { ideas, addIdea } = useTripStore();

  const handleIngest = async () => {
    if (!inputText.trim()) return;
    setIsIngesting(true);
    
    try {
      const token = localStorage.getItem('token');

      if (tripId && token) {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/trips/${tripId}/ingest`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ text: inputText }),
        });
        
        if (response.ok) {
          const newItems = await response.json();
          newItems.forEach((item: any) => addIdea({
            id: item.id.toString(),
            title: item.title,
            lat: item.lat,
            lng: item.lng
          }));
          setInputText('');
          return;
        }
      }

      // Fallback/Mock
      const mockIdeas = inputText.split(/[,\n]/).map(item => ({
        id: Math.random().toString(36).substr(2, 9),
        title: item.trim(),
        lat: 41.8902,
        lng: 12.4922,
      })).filter(item => item.title.length > 0);

      mockIdeas.forEach(idea => addIdea(idea));
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
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">Smart location ingestion</p>
        
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
            {isIngesting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <AnimatePresence initial={false}>
          {ideas.length === 0 ? (
            <motion.div 
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
                draggable
                onDragStart={(e) => e.dataTransfer.setData('ideaId', idea.id)}
                className="p-4 bg-white border border-slate-100 rounded-2xl shadow-sm cursor-grab active:cursor-grabbing hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-50/50 transition-all group relative overflow-hidden"
              >
                <div className="absolute top-0 left-0 w-1 h-full bg-indigo-100 group-hover:bg-indigo-500 transition-colors" />
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-50 text-slate-400 group-hover:bg-indigo-50 group-hover:text-indigo-600 rounded-xl transition-colors">
                    <MapPin className="w-4 h-4" />
                  </div>
                  <span className="text-sm font-black text-slate-800 truncate">{idea.title}</span>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
