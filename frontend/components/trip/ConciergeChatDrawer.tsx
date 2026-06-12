'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  X, Send, Loader2, MapPin, Clock, SkipForward,
  Plus, Navigation, Star, Check, RotateCcw, Coffee,
  ArrowRight, ChevronRight, AlertTriangle,
} from 'lucide-react';
import { useTripStore } from '@/lib/store';
import { api } from '@/lib/api';
import { formatTimeOfDay, timeOfDayFromDate } from '@/lib/time';
import clsx from 'clsx';
import EnrichmentBadge from '@/components/ui/EnrichmentBadge';
import VoiceInputButton from '@/components/common/VoiceInputButton';

// ── Types ───────────────────────────────────────────────────────────────────

interface PlaceCard {
  place_id: string;
  title: string;
  description?: string;
  category?: string;
  address?: string;
  lat: number;
  lng: number;
  photo_url?: string;
  rating?: number;
  price_level?: number;
  types?: string[];
  time_category?: string;
  added_by?: string;
  travel_time_s?: number;
  distance_m?: number;
}

type MessageType = 'text' | 'action_card' | 'place_card' | 'error' | 'summary' | 'whats_next';

// Dry-run preview (3.5/3.6/3.7) — mirrors backend ConciergePreview.
interface PreviewChange {
  event_id: number;
  title: string;
  day_date?: string | null;
  old_start?: string | null;
  new_start?: string | null;
  old_end?: string | null;
  new_end?: string | null;
}
interface PreviewWarning {
  kind: string; // overlap | travel | cross_midnight | opening_hours | cross_day | ineligible
  message: string;
  event_id?: number | null;
}
interface ConciergePreview {
  summary: string;
  changes: PreviewChange[];
  warnings: PreviewWarning[];
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type: MessageType;
  intent?: string;
  params?: Record<string, any>;
  requires_confirmation?: boolean;
  places?: PlaceCard[];
  summaryData?: any;
  status?: 'pending' | 'confirmed' | 'cancelled';
  preview?: ConciergePreview | null;
  authorName?: string | null;
  canUndo?: boolean;
}

// ── Formatted Text Renderer ─────────────────────────────────────────────────

function FormattedText({ text }: { text: string }) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];

  lines.forEach((line, li) => {
    if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(
        <li key={li} className="ml-4 list-disc text-sm text-slate-700 leading-relaxed">
          <InlineFormat text={line.slice(2)} />
        </li>
      );
    } else if (line.trim() === '') {
      elements.push(<div key={li} className="h-2" />);
    } else {
      elements.push(
        <p key={li} className="text-sm text-slate-700 leading-relaxed">
          <InlineFormat text={line} />
        </p>
      );
    }
  });

  return <div className="space-y-0.5">{elements}</div>;
}

function InlineFormat({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i} className="font-semibold text-slate-900">{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith('*') && part.endsWith('*')) {
          return <em key={i} className="italic">{part.slice(1, -1)}</em>;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

// ── Place Card Component ────────────────────────────────────────────────────

function PlaceCardItem({
  place,
  onSelect,
  selected,
}: {
  place: PlaceCard;
  onSelect: (p: PlaceCard) => void;
  selected: boolean;
}) {
  const travelMin = place.travel_time_s ? Math.ceil(place.travel_time_s / 60) : null;

  return (
    <button
      onClick={() => onSelect(place)}
      className={clsx(
        'flex-shrink-0 w-56 rounded-xl border overflow-hidden text-left transition-all',
        'hover:shadow-md active:scale-[0.98]',
        selected
          ? 'border-indigo-400 ring-2 ring-indigo-200 bg-indigo-50/50'
          : 'border-slate-200 bg-white hover:border-slate-300',
      )}
    >
      {place.photo_url && (
        <div className="h-28 w-full bg-slate-100 overflow-hidden">
          <img
            src={place.photo_url}
            alt={place.title}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        </div>
      )}
      <div className="p-3 space-y-1.5">
        <div className="flex items-center gap-1.5">
          <h4 className="font-semibold text-sm text-slate-900 line-clamp-1 flex-1">{place.title}</h4>
          {!place.place_id && <EnrichmentBadge size={3.5} />}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {place.rating != null && (
            <span className="flex items-center gap-0.5 text-xs text-amber-600">
              <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
              {place.rating.toFixed(1)}
            </span>
          )}
          {place.price_level != null && (
            <span className="text-xs text-slate-400">
              {'$'.repeat(place.price_level + 1)}
            </span>
          )}
        </div>
        {place.address && (
          <p className="text-xs text-slate-500 line-clamp-1">{place.address}</p>
        )}
        {travelMin != null && (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 bg-indigo-50 rounded-full px-2 py-0.5">
            <Navigation className="w-3 h-3" />
            {travelMin} min
          </span>
        )}
      </div>
    </button>
  );
}

// ── Intent Icon ─────────────────────────────────────────────────────────────

function IntentIcon({ intent }: { intent?: string }) {
  const cls = 'w-4 h-4';
  switch (intent) {
    case 'shift_timeline': return <Clock className={cls} />;
    case 'skip_event': return <SkipForward className={cls} />;
    case 'add_event': return <Plus className={cls} />;
    case 'move_event': return <MapPin className={cls} />;
    case 'find_nearby': return <Coffee className={cls} />;
    default: return <ArrowRight className={cls} />;
  }
}

// ── Main Drawer ─────────────────────────────────────────────────────────────

export default function ConciergeChatDrawer({
  isOpen,
  onClose,
  preAction,
}: {
  isOpen: boolean;
  onClose: () => void;
  preAction?: { type: string; payload?: any } | null;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [selectedPlace, setSelectedPlace] = useState<PlaceCard | null>(null);
  // 3.1: the thread is shared by the whole trip; canWrite gates the composer
  // (Plus + trip editor). Non-writers see a read-only/upsell state.
  const [canWrite, setCanWrite] = useState(true);
  const [threadLoaded, setThreadLoaded] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { activeTripId, activeTripTimezone, loadEvents } = useTripStore();
  const processedPreActionRef = useRef<string | null>(null);
  const mountedRef = useRef(true);
  const nearbyAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      nearbyAbortRef.current?.abort();
    };
  }, []);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending, scrollToBottom]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen]);

  // 3.1: hydrate the shared, trip-wide thread when the drawer opens so every
  // member sees the same conversation (with author labels) and we know whether
  // this member may post.
  useEffect(() => {
    if (!isOpen || !activeTripId || threadLoaded) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await api<{ messages: any[]; can_write: boolean }>(
          `/api/concierge/${activeTripId}/messages`,
        );
        if (cancelled) return;
        setCanWrite(data.can_write);
        const hydrated: ChatMessage[] = (data.messages || []).map((m, i) => {
          const meta = m.metadata || {};
          const isCard = m.message_type === 'action_card';
          return {
            id: `hist-${m.id ?? i}`,
            role: m.role,
            content: m.content,
            type: (m.message_type || 'text') as MessageType,
            intent: meta.intent,
            params: meta.params,
            // History action cards are already resolved — show them confirmed,
            // not as live pending prompts (avoids re-confirming old actions).
            requires_confirmation: false,
            status: isCard ? 'confirmed' : undefined,
            authorName: m.author_name,
          };
        });
        setMessages(hydrated);
      } catch {
        // A fresh trip or transient error — fall back to the empty state.
      } finally {
        if (!cancelled) setThreadLoaded(true);
      }
    })();
    return () => { cancelled = true; };
  }, [isOpen, activeTripId, threadLoaded]);

  // Reset the load latch when the drawer closes so it refetches next open.
  useEffect(() => {
    if (!isOpen) setThreadLoaded(false);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  // Tutorial: send a canned sample message so the user sees a real exchange
  // animate in. The override path skips the input box entirely.
  useEffect(() => {
    if (!isOpen) return;
    const onSample = (e: Event) => {
      const text = (e as CustomEvent).detail?.message as string | undefined;
      if (text) void handleSend(text);
    };
    window.addEventListener('tutorial:concierge-send', onSample as EventListener);
    return () => window.removeEventListener('tutorial:concierge-send', onSample as EventListener);
    // handleSend closes over activeTripId/sending; re-bind when those change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, activeTripId, sending]);

  // Handle pre-composed actions from action bar buttons.
  // Use a stable id field if present, falling back to a content hash, to avoid
  // re-processing the same action when the parent re-renders.
  useEffect(() => {
    if (!isOpen || !preAction || !activeTripId) return;
    const actionKey =
      (preAction as { id?: string }).id ??
      `${preAction.type}:${preAction.payload?.eventId ?? ''}`;
    if (processedPreActionRef.current === actionKey) return;
    processedPreActionRef.current = actionKey;

    if (preAction.type === 'skip_next') {
      handleSkipNext(preAction.payload?.eventId, preAction.payload?.eventTitle);
    } else if (preAction.type === 'find_coffee') {
      handleFindCoffee();
    }
  }, [isOpen, preAction, activeTripId]); // eslint-disable-line react-hooks/exhaustive-deps

  const addMessage = (msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  };

  const updateMessage = (id: string, updates: Partial<ChatMessage>) => {
    if (!mountedRef.current) return;
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...updates } : m)));
  };

  const refreshEvents = async () => {
    if (activeTripId) {
      await loadEvents(activeTripId, '');
    }
  };

  // ── Chat Send ──────────────────────────────────────────────────────────

  const handleSend = async (override?: string) => {
    const msg = (override ?? input).trim();
    if (!msg || sending || !activeTripId) return;
    setSending(true);
    if (override === undefined) setInput('');

    const userMsgId = `user-${Date.now()}`;
    addMessage({ id: userMsgId, role: 'user', content: msg, type: 'text' });

    try {
      const data = await api<Record<string, any>>(`/api/concierge/${activeTripId}/chat`, {
        method: 'POST',
        json: { message: msg },
      });

      if (data.intent === 'find_nearby') {
        addMessage({
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: data.user_message,
          type: 'text',
        });
        await handleFindNearbyFromLLM(data.params?.query || 'coffee', data.params?.category);
      } else {
        const asstMsgId = `asst-${Date.now()}`;
        addMessage({
          id: asstMsgId,
          role: 'assistant',
          content: data.user_message,
          type: data.message_type || 'text',
          intent: data.intent,
          params: data.params,
          requires_confirmation: data.requires_confirmation,
          status: data.requires_confirmation ? 'pending' : undefined,
          preview: data.preview ?? null,
        });
      }
    } catch {
      addMessage({
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: 'Something went wrong. Please try again.',
        type: 'error',
      });
    } finally {
      setSending(false);
    }
  };

  // ── Confirm / Cancel ──────────────────────────────────────────────────

  const handleConfirm = async (msgId: string, intent: string, params: Record<string, any>) => {
    if (!activeTripId) return;
    updateMessage(msgId, { status: 'confirmed' });

    try {
      await api(`/api/concierge/${activeTripId}/execute`, {
        method: 'POST',
        json: { intent, params },
      });
      await refreshEvents();
      // 3.8: an executed mutation can be reverted — surface an Undo affordance
      // on the just-confirmed card (only the most recent action is undoable).
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? { ...m, canUndo: true }
            : m.canUndo
            ? { ...m, canUndo: false }
            : m,
        ),
      );
    } catch {
      updateMessage(msgId, { status: 'pending' });
    }
  };

  const handleUndo = async (msgId: string) => {
    if (!activeTripId) return;
    try {
      await api(`/api/concierge/${activeTripId}/undo`, { method: 'POST' });
      await refreshEvents();
      updateMessage(msgId, { canUndo: false, status: 'cancelled' });
      addMessage({
        id: `undo-${Date.now()}`,
        role: 'system',
        content: '↩️ Reverted the last action.',
        type: 'text',
      });
    } catch {
      // Leave the card as-is on failure.
    }
  };

  const handleCancel = (msgId: string) => {
    updateMessage(msgId, { status: 'cancelled' });
  };

  // ── Skip Next ─────────────────────────────────────────────────────────

  const handleSkipNext = async (eventId?: number, eventTitle?: string) => {
    if (!activeTripId || !eventId) return;

    const cardId = `skip-${Date.now()}`;
    addMessage({
      id: cardId,
      role: 'assistant',
      content: `Skip **${eventTitle || 'next event'}**?`,
      type: 'action_card',
      intent: 'skip_event',
      params: { event_id: eventId },
      requires_confirmation: true,
      status: 'pending',
    });
  };

  // ── Find Coffee (geolocation + nearby API) ────────────────────────────

  const handleFindCoffee = () => {
    const loadingId = `loading-${Date.now()}`;
    addMessage({
      id: loadingId,
      role: 'assistant',
      content: 'Finding coffee near you...',
      type: 'text',
    });

    if (!navigator.geolocation) {
      updateMessage(loadingId, {
        content: 'Geolocation is not supported by your browser. Please try a different device.',
        type: 'error',
      });
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        await doNearbySearch('coffee', latitude, longitude, loadingId, 'Food & Dining');
      },
      () => {
        updateMessage(loadingId, {
          content: 'I need your location to find coffee nearby. Please enable location access and try again.',
          type: 'error',
        });
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  // ── Find Nearby from LLM intent ───────────────────────────────────────

  const handleFindNearbyFromLLM = async (query: string, category?: string) => {
    const loadingId = `loading-${Date.now()}`;
    addMessage({
      id: loadingId,
      role: 'assistant',
      content: `Looking for ${query} near you...`,
      type: 'text',
    });

    if (!navigator.geolocation) {
      updateMessage(loadingId, {
        content: 'Geolocation is not supported by your browser.',
        type: 'error',
      });
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        await doNearbySearch(query, position.coords.latitude, position.coords.longitude, loadingId, category);
      },
      () => {
        updateMessage(loadingId, {
          content: 'I need your location to find places nearby. Please enable location access.',
          type: 'error',
        });
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const doNearbySearch = async (query: string, lat: number, lng: number, replaceId: string, category?: string) => {
    if (!activeTripId) return;
    // Cancel any in-flight nearby search so a rapid second click doesn't get
    // overwritten by a stale first response.
    nearbyAbortRef.current?.abort();
    const controller = new AbortController();
    nearbyAbortRef.current = controller;
    try {
      const payload: Record<string, unknown> = { query, lat, lng, limit: 3 };
      if (category) payload.category = category;
      const data = await api<{ places: PlaceCard[] }>(`/api/concierge/${activeTripId}/find-nearby`, {
        method: 'POST',
        json: payload,
        signal: controller.signal,
      });

      updateMessage(replaceId, {
        content: `Found ${data.places.length} option${data.places.length !== 1 ? 's' : ''} nearby:`,
        type: 'place_card',
        places: data.places,
      });
    } catch (err) {
      // Ignore abort errors — they happen when a newer search supersedes this one.
      if ((err as { name?: string } | null)?.name === 'AbortError') return;
      updateMessage(replaceId, {
        content: 'Failed to search nearby places. Please try again.',
        type: 'error',
      });
    }
  };

  // ── Place Selection → Confirm ─────────────────────────────────────────

  const handlePlaceSelect = (place: PlaceCard) => {
    setSelectedPlace(place);
    const travelMin = place.travel_time_s ? Math.ceil(place.travel_time_s / 60) : 15;
    const tripTz = activeTripTimezone || Intl.DateTimeFormat().resolvedOptions().timeZone;
    const futureInstant = new Date(Date.now() + travelMin * 60_000);
    const startTod = timeOfDayFromDate(futureInstant, tripTz);
    const timeStr = formatTimeOfDay(startTod);

    const cardId = `place-confirm-${Date.now()}`;
    addMessage({
      id: cardId,
      role: 'assistant',
      content: `Add **${place.title}** at ${timeStr}?`,
      type: 'action_card',
      intent: 'add_event',
      params: {
        title: place.title,
        place_id: place.place_id,
        lat: place.lat,
        lng: place.lng,
        address: place.address,
        photo_url: place.photo_url,
        rating: place.rating,
        price_level: place.price_level,
        types: place.types,
        category: place.category,
        start_time: startTod,
      },
      requires_confirmation: true,
      status: 'pending',
    });
  };

  // ── Intent Chips ──────────────────────────────────────────────────────

  const handleTodaySummary = async () => {
    if (!activeTripId) return;
    const loadingId = `loading-${Date.now()}`;
    addMessage({ id: loadingId, role: 'assistant', content: 'Loading your day...', type: 'text' });

    try {
      const data = await api<Record<string, any>>(`/api/concierge/${activeTripId}/today-summary`);
      updateMessage(loadingId, {
        content: '',
        type: 'summary',
        summaryData: data,
      });
    } catch {
      updateMessage(loadingId, { content: 'Could not load today\'s summary.', type: 'error' });
    }
  };

  const handleWhatsNext = async () => {
    if (!activeTripId) return;
    const loadingId = `loading-${Date.now()}`;
    addMessage({ id: loadingId, role: 'assistant', content: 'Checking...', type: 'text' });

    try {
      const data = await api<Record<string, any>>(`/api/concierge/${activeTripId}/whats-next`);
      updateMessage(loadingId, {
        content: '',
        type: 'whats_next',
        summaryData: data,
      });
    } catch {
      updateMessage(loadingId, { content: 'Could not check what\'s next.', type: 'error' });
    }
  };

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40"
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Concierge chat"
            data-tutorial="concierge-panel"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md bg-white shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
                  <Navigation className="w-4 h-4 text-indigo-600" />
                </div>
                <h2 className="text-base font-bold text-slate-900">Concierge</h2>
              </div>
              <button
                onClick={onClose}
                className="p-2 -mr-2 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
                aria-label="Close concierge"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Messages */}
            <div ref={listRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center px-6 py-12">
                  <div className="w-14 h-14 rounded-2xl bg-indigo-50 flex items-center justify-center mb-4">
                    <Navigation className="w-7 h-7 text-indigo-500" />
                  </div>
                  <h3 className="font-semibold text-slate-800 mb-1">Hi there!</h3>
                  <p className="text-sm text-slate-500 leading-relaxed max-w-[260px]">
                    I can help you adjust your itinerary, find nearby places, or answer questions about your trip.
                  </p>
                </div>
              )}

              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  msg={msg}
                  onConfirm={handleConfirm}
                  onCancel={handleCancel}
                  onUndo={handleUndo}
                  onPlaceSelect={handlePlaceSelect}
                  onRetry={() => inputRef.current?.focus()}
                  selectedPlace={selectedPlace}
                />
              ))}

              {sending && (
                <div className="flex justify-start">
                  <div className="bg-slate-100 rounded-2xl rounded-bl-md px-4 py-3">
                    <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                  </div>
                </div>
              )}
            </div>

            {/* Intent Chips */}
            <div className="px-4 py-2 border-t border-slate-50 overflow-x-auto flex gap-2 scrollbar-hide">
              <ChipButton label="My day" icon={<Clock className="w-3.5 h-3.5" />} onClick={handleTodaySummary} />
              <ChipButton label="What's next?" icon={<ChevronRight className="w-3.5 h-3.5" />} onClick={handleWhatsNext} />
              <ChipButton label="Find Coffee" icon={<Coffee className="w-3.5 h-3.5" />} onClick={handleFindCoffee} />
            </div>

            {/* Input — read-only for non-writers (3.1) */}
            {!canWrite ? (
              <div className="px-4 pb-4 pt-2">
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-center">
                  <p className="text-sm text-slate-500">
                    You can follow the trip&rsquo;s Concierge here. Posting and confirming
                    actions is available to trip admins on Roammate Plus.
                  </p>
                </div>
              </div>
            ) : (
            <div className="px-4 pb-4 pt-2">
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus-within:border-indigo-300 focus-within:ring-2 focus-within:ring-indigo-100 transition-all">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleSend(); }}
                  placeholder="Ask anything about your trip..."
                  disabled={sending}
                  className="flex-1 bg-transparent text-sm text-slate-800 placeholder:text-slate-400 outline-none disabled:opacity-50"
                />
                <VoiceInputButton
                  value={input}
                  onChange={setInput}
                  disabled={sending}
                  className="p-1.5 rounded-lg"
                />
                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim() || sending}
                  className="p-1.5 rounded-lg bg-indigo-600 text-white disabled:opacity-30 hover:bg-indigo-700 transition-colors"
                  aria-label="Send message"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ── Chip Button ─────────────────────────────────────────────────────────────

function ChipButton({
  label,
  icon,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-full hover:bg-slate-50 hover:border-slate-300 transition-colors active:scale-95"
    >
      {icon}
      {label}
    </button>
  );
}

// ── Preview Block (dry-run impact: before→after diff + warnings) ─────────────

function warningIcon(kind: string) {
  switch (kind) {
    case 'opening_hours': return '🕗';
    case 'cross_midnight': return '🌙';
    case 'travel': return '🚗';
    case 'overlap': return '⏱️';
    default: return '⚠️';
  }
}

function PreviewBlock({ preview }: { preview: ConciergePreview }) {
  const { changes, warnings, summary } = preview;
  if (!changes.length && !warnings.length) return null;

  return (
    <div className="px-4 pb-3 pt-1 border-t border-slate-100 space-y-2">
      {summary && (
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{summary}</p>
      )}
      {changes.length > 0 && (
        <div className="space-y-1">
          {changes.map((c) => {
            const added = !c.old_start && c.new_start;
            return (
              <div key={c.event_id} className="flex items-center gap-2 text-sm">
                <span className="flex-1 truncate text-slate-700">{c.title}</span>
                <span className="flex items-center gap-1.5 font-medium tabular-nums">
                  {c.old_start && (
                    <span className="text-slate-400 line-through">{c.old_start}</span>
                  )}
                  {c.old_start && c.new_start && (
                    <ArrowRight className="w-3 h-3 text-slate-300" />
                  )}
                  {c.new_start && (
                    <span className={added ? 'text-emerald-600' : 'text-indigo-600'}>{c.new_start}</span>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      )}
      {warnings.length > 0 && (
        <div className="space-y-1 pt-0.5">
          {warnings.map((w, i) => (
            <div
              key={i}
              className="flex items-start gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-2.5 py-1.5"
            >
              <span aria-hidden>{warningIcon(w.kind)}</span>
              <span className="flex-1 leading-snug">{w.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Message Bubble ──────────────────────────────────────────────────────────

function MessageBubble({
  msg,
  onConfirm,
  onCancel,
  onUndo,
  onPlaceSelect,
  onRetry,
  selectedPlace,
}: {
  msg: ChatMessage;
  onConfirm: (id: string, intent: string, params: Record<string, any>) => void;
  onCancel: (id: string) => void;
  onUndo: (id: string) => void;
  onPlaceSelect: (p: PlaceCard) => void;
  onRetry: () => void;
  selectedPlace: PlaceCard | null;
}) {
  // User message (shared thread shows the author's name above the bubble, 3.1)
  if (msg.role === 'user') {
    return (
      <div className="flex flex-col items-end">
        {msg.authorName && (
          <span className="text-[11px] font-medium text-slate-400 mb-0.5 mr-1">{msg.authorName}</span>
        )}
        <div className="max-w-[80%] bg-indigo-600 text-white rounded-2xl rounded-br-md px-4 py-2.5">
          <p className="text-sm leading-relaxed">{msg.content}</p>
        </div>
      </div>
    );
  }

  // System message (e.g. confirmation receipts, undo notices)
  if (msg.role === 'system') {
    return (
      <div className="flex justify-center">
        <span className="text-xs text-slate-400 bg-slate-50 rounded-full px-3 py-1">{msg.content}</span>
      </div>
    );
  }

  // Action Confirmation Card
  if (msg.type === 'action_card') {
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm">
          <div className="px-4 py-3 flex items-start gap-3">
            <div className={clsx(
              'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5',
              msg.status === 'confirmed' ? 'bg-emerald-100 text-emerald-600' :
              msg.status === 'cancelled' ? 'bg-slate-100 text-slate-400' :
              'bg-indigo-100 text-indigo-600'
            )}>
              {msg.status === 'confirmed' ? <Check className="w-4 h-4" /> :
               msg.status === 'cancelled' ? <X className="w-4 h-4" /> :
               <IntentIcon intent={msg.intent} />}
            </div>
            <div className="flex-1 min-w-0">
              <FormattedText text={msg.content} />
            </div>
          </div>
          {/* 3.5/3.6/3.7: real projected impact — before→after diff + warnings */}
          {msg.preview && <PreviewBlock preview={msg.preview} />}
          {msg.status === 'pending' && (
            <div className="px-4 py-2.5 border-t border-slate-100 flex items-center gap-2">
              <button
                onClick={() => onConfirm(msg.id, msg.intent || '', msg.params || {})}
                className="flex-1 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors active:scale-[0.98]"
              >
                Confirm
              </button>
              <button
                onClick={() => onCancel(msg.id)}
                className="px-4 py-2 text-sm font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-50 rounded-lg transition-colors"
              >
                Nevermind
              </button>
            </div>
          )}
          {msg.status === 'confirmed' && (
            <div className="px-4 py-2 border-t border-emerald-100 bg-emerald-50/50 flex items-center justify-between">
              <p className="text-xs font-medium text-emerald-600 flex items-center gap-1">
                <Check className="w-3 h-3" /> Done
              </p>
              {msg.canUndo && (
                <button
                  onClick={() => onUndo(msg.id)}
                  className="flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-slate-700 transition-colors"
                >
                  <RotateCcw className="w-3 h-3" /> Undo
                </button>
              )}
            </div>
          )}
          {msg.status === 'cancelled' && (
            <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/50">
              <p className="text-xs font-medium text-slate-400">Cancelled</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Place Selection Cards
  if (msg.type === 'place_card' && msg.places?.length) {
    return (
      <div className="flex flex-col gap-2">
        <div className="flex justify-start">
          <div className="max-w-[80%] bg-slate-100 rounded-2xl rounded-bl-md px-4 py-2.5">
            <p className="text-sm text-slate-700">{msg.content}</p>
          </div>
        </div>
        <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide pl-1">
          {msg.places.map((p) => (
            <PlaceCardItem
              key={p.place_id}
              place={p}
              onSelect={onPlaceSelect}
              selected={selectedPlace?.place_id === p.place_id}
            />
          ))}
        </div>
      </div>
    );
  }

  // Error / Retry Card
  if (msg.type === 'error') {
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] border border-amber-200 bg-amber-50 rounded-xl px-4 py-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-amber-800 leading-relaxed">{msg.content}</p>
              <button
                onClick={onRetry}
                className="mt-2 flex items-center gap-1.5 text-xs font-semibold text-amber-700 hover:text-amber-900 transition-colors"
              >
                <RotateCcw className="w-3 h-3" />
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Summary Card
  if (msg.type === 'summary' && msg.summaryData) {
    const d = msg.summaryData;
    return (
      <div className="flex justify-start">
        <div className="max-w-[90%] border border-slate-200 bg-white rounded-xl overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
            <h4 className="text-sm font-bold text-slate-800">
              Today &middot; {d.total_events} event{d.total_events !== 1 ? 's' : ''}
            </h4>
            <div className="flex gap-3 mt-1 text-xs text-slate-500">
              {d.completed > 0 && <span>{d.completed} done</span>}
              {d.upcoming > 0 && <span>{d.upcoming} upcoming</span>}
              {d.skipped > 0 && <span>{d.skipped} skipped</span>}
            </div>
          </div>
          <div className="divide-y divide-slate-50">
            {d.events?.map((se: any, i: number) => (
              <div key={i} className={clsx(
                'px-4 py-2.5 flex items-center gap-3',
                se.status === 'skipped' && 'opacity-40',
              )}>
                <StatusDot status={se.status} />
                <div className="flex-1 min-w-0">
                  <p className={clsx(
                    'text-sm font-medium truncate',
                    se.status === 'skipped' ? 'line-through text-slate-400' : 'text-slate-800',
                  )}>
                    {se.event.title}
                  </p>
                  {se.event.start_time && (
                    <p className="text-xs text-slate-400">
                      {formatTimeOfDay(se.event.start_time)}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // What's Next Card
  if (msg.type === 'whats_next' && msg.summaryData) {
    const d = msg.summaryData;
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] border border-slate-200 bg-white rounded-xl overflow-hidden shadow-sm">
          {d.current_event && (
            <div className="px-4 py-3 bg-indigo-50 border-b border-indigo-100">
              <p className="text-xs font-medium text-indigo-500 uppercase tracking-wide">Now</p>
              <p className="text-sm font-semibold text-slate-800 mt-0.5">{d.current_event.title}</p>
            </div>
          )}
          {d.next_event ? (
            <div className="px-4 py-3">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Next up</p>
              <p className="text-sm font-semibold text-slate-800 mt-0.5">{d.next_event.title}</p>
              <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
                {d.time_until_next && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    in {d.time_until_next}
                  </span>
                )}
                {d.travel_time_to_next != null && (
                  <span className="flex items-center gap-1">
                    <Navigation className="w-3 h-3" />
                    {Math.ceil(d.travel_time_to_next / 60)} min drive
                  </span>
                )}
              </div>
            </div>
          ) : (
            <div className="px-4 py-3">
              <p className="text-sm text-slate-500">Nothing else scheduled today. Enjoy your free time!</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Default text message
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] bg-slate-100 rounded-2xl rounded-bl-md px-4 py-2.5">
        <FormattedText text={msg.content} />
      </div>
    </div>
  );
}

// ── Status Dot ──────────────────────────────────────────────────────────────

function StatusDot({ status }: { status: string }) {
  const cls = 'w-2 h-2 rounded-full flex-shrink-0';
  switch (status) {
    case 'completed': return <div className={`${cls} bg-emerald-400`} />;
    case 'ongoing': return <div className={`${cls} bg-indigo-500 animate-pulse`} />;
    case 'skipped': return <div className={`${cls} bg-slate-300`} />;
    default: return <div className={`${cls} bg-slate-300`} />;
  }
}
