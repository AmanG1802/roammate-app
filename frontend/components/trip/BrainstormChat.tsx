'use client';

import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Loader2, Lock, RotateCcw, Send, Sparkles, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { AnimatePresence, motion } from 'framer-motion';
import { getToken } from '@/lib/auth';
import { isNeedsPlus, useEntitlement } from '@/hooks/useEntitlement';
import { BrainstormQuotaPill } from '@/components/billing/QuotaPill';
import VoiceInputButton from '@/components/common/VoiceInputButton';

type Msg = { id: number; role: 'user' | 'assistant'; content: string; created_at: string };

function authHeaders(): HeadersInit {
  const token = getToken();
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
  const [failedMessage, setFailedMessage] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [loadTick, setLoadTick] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);
  const { entitlement, requirePlus, refresh: refreshEntitlement } = useEntitlement();
  // Plus users have `brainstorm_remaining === null` (unlimited) → not exhausted.
  const isQuotaExhausted = entitlement.brainstorm_remaining === 0;

  useEffect(() => {
    const controller = new AbortController();
    setLoadError(false);
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/brainstorm/messages`, {
      headers: authHeaders(),
      cache: 'no-store',
      signal: controller.signal,
    })
      .then(async (r) => {
        if (!r.ok) throw new Error(`status ${r.status}`);
        return r.json();
      })
      .then((data: Msg[]) => setMessages(data))
      .catch((err) => {
        if (err?.name === 'AbortError') return;
        setLoadError(true);
      });
    return () => controller.abort();
  }, [tripId, loadTick]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, sending, failedMessage]);

  // Tutorial: send a canned sample message so the exchange animates in.
  useEffect(() => {
    const onSample = (e: Event) => {
      const text = (e as CustomEvent).detail?.message as string | undefined;
      if (text) void send(text, true);
    };
    window.addEventListener('tutorial:brainstorm-send', onSample as EventListener);
    return () => window.removeEventListener('tutorial:brainstorm-send', onSample as EventListener);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tripId, sending]);

  const send = async (presetMsg?: string, addOptimistic = false) => {
    const msg = presetMsg ?? input.trim();
    if (!msg || sending) return;
    setSending(true);
    setFailedMessage(null);

    // Show the user's bubble immediately for fresh sends (typed or tutorial),
    // but not for retries where it's already on screen.
    const optimistic = presetMsg ? addOptimistic : true;
    if (optimistic) {
      setMessages((prev) => [
        ...prev,
        { id: Date.now(), role: 'user', content: msg, created_at: new Date().toISOString() },
      ]);
      if (!presetMsg) setInput('');
    }

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/brainstorm/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ message: msg }),
      });
      if (res.status === 402) {
        // Roll back the optimistic message and open the paywall. If the user
        // subscribes, automatically retry the send.
        if (optimistic) setMessages((prev) => prev.slice(0, -1));
        const body = await res.json().catch(() => null);
        const needs = isNeedsPlus(body);
        const subscribed = await requirePlus(needs?.feature ?? 'brainstorm_quota');
        setSending(false);
        if (subscribed) {
          await refreshEntitlement();
          send(msg);
        } else if (!presetMsg) {
          setInput(msg);
        }
        return;
      }
      if (res.ok) {
        const data = await res.json();
        const history: Msg[] = data.history;
        if (!optimistic) {
          // No optimistic bubble was shown; use full history to restore state
          setMessages(history);
        } else {
          // Normal send: optimistic user message already in state.
          // Swap it for the server's real user message + append the assistant reply.
          const assistantMsg = history[history.length - 1];
          const realUserMsg = history[history.length - 2];
          if (assistantMsg?.role === 'assistant') {
            setMessages((prev) => [
              ...prev.slice(0, -1),
              ...(realUserMsg?.role === 'user' ? [realUserMsg] : []),
              assistantMsg,
            ]);
          } else {
            setMessages(history);
          }
        }
        // Counter ticked up on the server — refresh the entitlement so the
        // QuotaPill reflects the new remaining count immediately.
        void refreshEntitlement();
      } else {
        setFailedMessage(msg);
      }
    } catch {
      setFailedMessage(msg);
    } finally {
      setSending(false);
    }
  };

  const retry = () => {
    if (failedMessage) send(failedMessage);
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
        <BrainstormQuotaPill className="shrink-0" />
      </div>

      {/* Messages */}
      <div ref={listRef} className="flex-1 overflow-y-auto px-5 py-6 space-y-4">
        {loadError && (
          <div className="flex items-start gap-2 px-3 py-2.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-700">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1 text-xs font-bold leading-relaxed">
              Couldn&apos;t load chat history.
              <button
                onClick={() => setLoadTick((t) => t + 1)}
                className="ml-2 underline underline-offset-2 hover:no-underline"
              >
                Retry
              </button>
            </div>
          </div>
        )}
        {messages.length === 0 && !sending && !loadError && (
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
              {m.role === 'assistant' ? (
                <div
                  className="prose prose-sm prose-slate max-w-none
                    [&>p]:my-1 [&>ul]:my-1.5 [&>ol]:my-1.5 [&>li]:my-0.5
                    [&>p:first-child]:mt-0 [&>p:last-child]:mb-0
                    [&_strong]:font-bold [&_strong]:text-slate-800
                    [&_ul]:pl-4 [&_ol]:pl-4
                    [&_li]:marker:text-indigo-400"
                >
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>
              ) : (
                m.content
              )}
            </div>
          </div>
        ))}

        {/* Typing indicator while waiting for AI response */}
        {sending && (
          <div className="flex items-end gap-2" aria-live="polite" aria-label="Assistant is responding">
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

        {/* Error bubble when AI response fails */}
        {failedMessage && !sending && (
          <div className="flex items-end gap-2">
            <div className="w-6 h-6 rounded-lg bg-rose-100 flex items-center justify-center shrink-0 mb-0.5">
              <AlertTriangle className="w-3 h-3 text-rose-500" />
            </div>
            <div className="max-w-[82%] bg-rose-50 border border-rose-200 rounded-2xl rounded-bl-sm px-4 py-2.5 shadow-sm">
              <p className="text-sm font-medium text-rose-700">Couldn&apos;t get a response.</p>
              <button
                onClick={retry}
                className="mt-1 text-xs font-bold text-rose-600 hover:text-rose-800 flex items-center gap-1 transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3 h-3" /> Retry
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-slate-100 p-4 space-y-2.5 shrink-0 bg-white">
        <AnimatePresence>
          {hasAssistant && !isQuotaExhausted && (
            <motion.button
              key="extract"
              initial={{ opacity: 0, y: 8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.98 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              onClick={extract}
              disabled={extracting}
              whileTap={{ scale: 0.98 }}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-500 to-violet-500 text-white rounded-xl text-xs font-black hover:from-indigo-600 hover:to-violet-600 transition-colors shadow-sm shadow-indigo-200/40 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {extracting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              Create items from chat
            </motion.button>
          )}
        </AnimatePresence>
        <div className="flex items-end gap-2">
          <textarea
            data-tutorial="brainstorm-chat-input"
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder={isQuotaExhausted ? 'Out of free brainstorms' : 'Ask about a destination…'}
            disabled={isQuotaExhausted}
            className="flex-1 px-3.5 py-2.5 text-sm font-medium border border-slate-200 bg-slate-50 rounded-2xl resize-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 outline-none transition-all leading-relaxed disabled:opacity-60 disabled:cursor-not-allowed"
          />
          {isQuotaExhausted ? (
            <button
              onClick={() => requirePlus('brainstorm_quota')}
              aria-label="Get Plus to keep chatting"
              className="p-2.5 bg-rose-500 text-white rounded-xl hover:bg-rose-600 transition-all shadow-sm cursor-pointer active:scale-95"
            >
              <Lock className="w-4 h-4" />
            </button>
          ) : (
            <>
            <VoiceInputButton value={input} onChange={setInput} disabled={sending} />
            <button
              onClick={() => send()}
              disabled={sending || !input.trim()}
              aria-label="Send message"
              className="p-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-sm cursor-pointer active:scale-95"
            >
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
