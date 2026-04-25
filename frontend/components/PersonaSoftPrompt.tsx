'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { X, Sparkles } from 'lucide-react';

const DISMISSED_KEY = 'persona_soft_prompt_dismissed';

export default function PersonaSoftPrompt() {
  const [visible, setVisible] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const dismissed = localStorage.getItem(DISMISSED_KEY);
    if (!dismissed) setVisible(true);
  }, []);

  const dismiss = () => {
    localStorage.setItem(DISMISSED_KEY, '1');
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="mx-3 mb-3 bg-indigo-50 border border-indigo-100 rounded-xl p-3 flex items-start gap-2">
      <Sparkles className="w-4 h-4 text-indigo-500 mt-0.5 shrink-0" />
      <button
        onClick={() => router.push('/profile/persona')}
        className="flex-1 text-left text-xs font-bold text-indigo-700 hover:text-indigo-800 cursor-pointer leading-snug"
      >
        Set your travel persona for smarter suggestions →
      </button>
      <button
        onClick={dismiss}
        className="text-indigo-300 hover:text-indigo-500 transition-colors shrink-0 cursor-pointer"
        aria-label="Dismiss"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
