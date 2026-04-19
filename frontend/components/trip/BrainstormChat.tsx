'use client';

import { useEffect, useRef, useState } from 'react';
import { Loader2, Send, Sparkles } from 'lucide-react';

type Msg = { id: number; role: 'user' | 'assistant'; content: string; created_at: string };

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function BrainstormChat({
  tripId,
  onItemsCreated,
}: {
  tripId: string;
  onItemsCreated: () => void;
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/brainstorm/messages`, {
      headers: authHeaders(),
      cache: 'no-store',
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data: Msg[]) => setMessages(data))
      .catch(() => {});
  }, [tripId]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const msg = input.trim();
    if (!msg || sending) return;
    setSending(true);
    setInput('');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/brainstorm/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ message: msg }),
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(data.history);
      }
    } finally {
      setSending(false);
    }
  };

  const extract = async () => {
    setExtracting(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/brainstorm/extract`, {
        method: 'POST',
        headers: authHeaders(),
      });
      if (res.ok) onItemsCreated();
    } finally {
      setExtracting(false);
    }
  };

  const hasAssistant = messages.some((m) => m.role === 'assistant');

  return (
    <div className="flex flex-col h-full bg-indigo-50/40">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2 shrink-0 bg-white">
        <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-base font-black text-slate-900 tracking-tight">Brainstorm Chat</h3>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Private to you
          </p>
        </div>
      </div>

      <div ref={listRef} className="flex-1 overflow-y-auto p-6 space-y-3">
        {messages.length === 0 && (
          <div className="text-center py-16 opacity-40">
            <p className="text-sm font-bold text-slate-400">
              Ask about a destination to get started.
            </p>
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm font-medium shadow-sm ${
              m.role === 'user'
                ? 'ml-auto bg-indigo-600 text-white shadow-indigo-100'
                : 'bg-white text-slate-700 border border-slate-100'
            }`}
          >
            {m.content}
          </div>
        ))}
      </div>

      <div className="border-t border-slate-100 p-4 space-y-2 shrink-0 bg-white">
        {hasAssistant && (
          <button
            onClick={extract}
            disabled={extracting}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-indigo-50 border border-indigo-100 text-indigo-700 rounded-xl text-xs font-black hover:bg-indigo-100 transition-all disabled:opacity-50"
          >
            {extracting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            Create items from chat
          </button>
        )}
        <div className="flex items-end gap-2">
          <textarea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Ask about a destination..."
            className="flex-1 px-3 py-2 text-sm font-medium border border-slate-200 bg-slate-50 rounded-xl resize-none focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
          />
          <button
            onClick={send}
            disabled={sending || !input.trim()}
            className="p-2.5 bg-slate-900 text-white rounded-xl hover:bg-indigo-600 disabled:opacity-30 transition-all"
          >
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
