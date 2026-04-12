'use client';

import { useTripStore } from '@/lib/store';
import { motion, AnimatePresence } from 'framer-motion';

export default function Collaborators() {
  const { collaborators } = useTripStore();

  return (
    <div className="flex -space-x-2">
      {collaborators.map((collaborator) => (
        <div 
          key={collaborator.id}
          className="relative group"
          title={collaborator.name}
        >
          <div 
            className="w-10 h-10 rounded-full border-2 border-white flex items-center justify-center text-xs font-bold text-white shadow-sm transition-transform hover:scale-110 active:scale-95 cursor-pointer"
            style={{ backgroundColor: collaborator.color }}
          >
            {collaborator.name.charAt(0)}
          </div>
          
          {/* Tooltip */}
          <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 hidden group-hover:block bg-slate-800 text-white text-[10px] py-1 px-2 rounded font-bold whitespace-nowrap z-50">
            {collaborator.name}
          </div>
        </div>
      ))}
      
      <button className="w-10 h-10 rounded-full border-2 border-dashed border-slate-300 flex items-center justify-center text-slate-400 hover:border-indigo-400 hover:text-indigo-500 transition-colors">
        <span className="text-sm font-bold">+</span>
      </button>
    </div>
  );
}
