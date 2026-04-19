'use client';

import { useEffect, useRef, useState } from 'react';
import { Loader2, Send, Sparkles, MessageSquare } from 'lucide-react';

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
  }, [messages, sending]);

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
    <div className="flex flex-col h-full bg-gradient-to-b from-slate-50 to-indigo-50/20">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-3 shrink-0 bg-white">
        <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-violet-600 text-white rounded-xl shadow-sm shadow-indigo-200/60 shrink-0">
          <Sparkles className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-black text-slate-900 tracking-tight">Brainstorm Chat</h3>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            AI-powered · Private to you
          </p>
        </div>
        {messages.length > 0 && (
          <span className="shrink-0 px-2.5 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-black border border-indigo-100 tabular-nums">
            {messages.length}
          </span>
        )}
      </div>

      {/* Messages */}
      <div ref={listRef} className="flex-1 overflow-y-auto px-5 py-6 space-y-4">
        {messages.length === 0 && !sending && (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            <div className="w-14 h-14 bg-white border border-indigo-100 rounded-2xl flex items-center justify-center shadow-sm shadow-indigo-50">
              <MessageSquare className="w-7 h-7 text-indigo-300" />
            </div>
            <div className="text-center max-w-[200px]">
              <p className="text-sm font-black text-slate-500 uppercase tracking-widest">Start brainstorming</p>
              <p className="text-xs font-medium text-slate-400 mt-1.5 leading-relaxed">
                Ask about destinations, activities, food, and hidden gems.
              </p>
            </div>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={`flex items-end gap-2 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {m.role === 'assistant' && (
              <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0 shadow-sm shadow-indigo-200/60 mb-0.5">
                <Sparkles className="w-3 h-3 text-white" />
              </div>
            )}
            <div
              className={`max-w-[82%] rounded-2xl px-4 py-2.5 text-sm font-medium leading-relaxed ${
                m.role === 'user'
                  ? 'bg-gradient-to-br from-indigo-500 to-indigo-600 text-white shadow-md shadow-indigo-200/50 rounded-br-sm'
                  : 'bg-white text-slate-700 border border-slate-100 shadow-sm rounded-bl-sm'
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}

        {/* Typing indicator while waiting for AI response */}
        {sending && (
          <div className="flex items-end gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0 shadow-sm shadow-indigo-200/60">
              <Sparkles className="w-3 h-3 text-white" />
            </div>
            <div className="bg-white border border-slate-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-slate-100 p-4 space-y-2.5 shrink-0 bg-white">
        {hasAssistant && (
          <button
            onClick={extract}
            disabled={extracting}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-500 to-violet-500 text-white rounded-xl text-xs font-black hover:from-indigo-600 hover:to-violet-600 transition-all shadow-sm shadow-indigo-200/40 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
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
            placeholder="Ask about a destination…"
            className="flex-1 px-3.5 py-2.5 text-sm font-medium border border-slate-200 bg-slate-50 rounded-2xl resize-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 outline-none transition-all leading-relaxed"
          />
          <button
            onClick={send}
            disabled={sending || !input.trim()}
            className="p-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-sm cursor-pointer"
          >
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
