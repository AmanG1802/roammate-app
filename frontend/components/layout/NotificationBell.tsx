'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Bell, Check, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type NotificationItem = {
  id: number;
  type: string;
  payload: Record<string, any>;
  trip_id: number | null;
  group_id: number | null;
  actor: { id: number; name: string | null; email: string | null } | null;
  read_at: string | null;
  created_at: string;
};

const API = process.env.NEXT_PUBLIC_API_URL ?? '';
const POLL_MS = 30_000;

function auth(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const s = Math.max(1, Math.floor(ms / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function dayLabel(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) return 'Today';
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function renderMessage(n: NotificationItem): { icon: string; text: JSX.Element } {
  const p = n.payload || {};
  const trip = <strong className="text-slate-900">{p.trip_name || 'a trip'}</strong>;
  const actor = <strong className="text-slate-900">{p.actor_name || n.actor?.name || 'Someone'}</strong>;
  switch (n.type) {
    case 'trip_created':
      return { icon: '🌍', text: <>You created {trip}.</> };
    case 'trip_renamed':
      return { icon: '✏️', text: <>{actor} renamed <strong className="text-slate-900">{p.from}</strong> to <strong className="text-slate-900">{p.to}</strong>.</> };
    case 'trip_date_changed':
      return { icon: '📅', text: <>{actor} changed dates for {trip}.</> };
    case 'trip_deleted':
      return { icon: '🗑️', text: <>{actor} deleted {trip}.</> };
    case 'invite_received':
      return { icon: '✉️', text: <><strong className="text-slate-900">{p.inviter_name || 'Someone'}</strong> invited you to {trip}.</> };
    case 'invite_accepted':
      if (p.self) return { icon: '✅', text: <>You accepted {trip}.</> };
      return { icon: '👋', text: <><strong className="text-slate-900">{p.joined_user_name || 'Someone'}</strong> joined {trip}.</> };
    case 'invite_declined':
      return { icon: '❌', text: <><strong className="text-slate-900">{p.declined_user_name || 'Someone'}</strong> declined the invite to {trip}.</> };
    case 'member_removed':
      if (p.self) return { icon: '🚪', text: <>{actor} removed you from {trip}.</> };
      return { icon: '🚪', text: <>{actor} removed <strong className="text-slate-900">{p.removed_user_name || 'a member'}</strong> from {trip}.</> };
    case 'member_role_changed':
      return { icon: '🎭', text: <>{actor} changed your role on {trip} to <strong className="text-slate-900">{p.new_role}</strong>.</> };
    case 'group_created':
      return { icon: '👥', text: <>You created group <strong className="text-slate-900">{p.group_name || ''}</strong>.</> };
    case 'group_invite_received':
      return { icon: '👥', text: <><strong className="text-slate-900">{p.inviter_name || 'Someone'}</strong> invited you to group <strong className="text-slate-900">{p.group_name || ''}</strong>.</> };
    case 'group_invite_accepted':
      if (p.self) return { icon: '✅', text: <>You joined group <strong className="text-slate-900">{p.group_name || ''}</strong>.</> };
      return { icon: '👋', text: <><strong className="text-slate-900">{p.joined_user_name || 'Someone'}</strong> joined group <strong className="text-slate-900">{p.group_name || ''}</strong>.</> };
    case 'group_member_removed':
      if (p.self) return { icon: '🚪', text: <>{actor} removed you from group <strong className="text-slate-900">{p.group_name || ''}</strong>.</> };
      return { icon: '🚪', text: <>{actor} removed <strong className="text-slate-900">{p.removed_user_name || 'a member'}</strong> from group <strong className="text-slate-900">{p.group_name || ''}</strong>.</> };
    case 'group_trip_attached':
      return { icon: '🔗', text: <>{actor} attached {trip} to group <strong className="text-slate-900">{p.group_name || ''}</strong>.</> };
    case 'idea_added_to_group':
      return { icon: '💡', text: <>{actor} added <strong className="text-slate-900">{p.idea_title || 'an idea'}</strong> to <strong className="text-slate-900">{p.group_name || 'your group'}</strong>.</> };
    case 'event_added':
      return { icon: '➕', text: <>{actor} added <strong className="text-slate-900">{p.title || 'an event'}</strong>{p.via === 'quick_add' ? ' (quick add)' : ''}.</> };
    case 'event_moved':
      return { icon: '🕒', text: <>{actor} rescheduled <strong className="text-slate-900">{p.title || 'an event'}</strong>.</> };
    case 'event_removed':
      return { icon: '🗑️', text: <>{actor} {p.moved_to_bin ? 'moved' : 'removed'} <strong className="text-slate-900">{p.title || 'an event'}</strong>{p.moved_to_bin ? ' to the idea bin' : ''}.</> };
    case 'ripple_fired': {
      const dm = Number(p.delta_minutes || 0);
      const dir = dm >= 0 ? 'pushed back' : 'pulled forward';
      const mins = Math.abs(dm);
      return { icon: '🌊', text: <>{actor} {dir} {p.shifted_count || 0} events by <strong className="text-slate-900">{mins}m</strong>.</> };
    }
    default:
      return { icon: '🔔', text: <>{n.type.replaceAll('_', ' ')}</> };
  }
}

export default function NotificationBell() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  const fetchUnread = useCallback(async () => {
    try {
      const res = await fetch(`${API}/notifications/unread-count`, { headers: auth() });
      if (res.ok) {
        const data = await res.json();
        setUnread(data.unread ?? 0);
      }
    } catch { /* ignore */ }
  }, []);

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/notifications/?limit=30`, { headers: auth() });
      if (res.ok) setItems(await res.json());
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, POLL_MS);
    const onFocus = () => fetchUnread();
    window.addEventListener('focus', onFocus);
    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', onFocus);
    };
  }, [fetchUnread]);

  useEffect(() => {
    if (open) fetchList();
  }, [open, fetchList]);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  const markRead = useCallback(async (id: number) => {
    setItems((prev) => prev.map((n) => (n.id === id && !n.read_at ? { ...n, read_at: new Date().toISOString() } : n)));
    setUnread((u) => Math.max(0, u - 1));
    try {
      await fetch(`${API}/notifications/${id}/read`, { method: 'POST', headers: auth() });
    } catch { /* optimistic — already updated */ }
  }, []);

  const markAllRead = useCallback(async () => {
    setItems((prev) => prev.map((n) => (n.read_at ? n : { ...n, read_at: new Date().toISOString() })));
    setUnread(0);
    try {
      await fetch(`${API}/notifications/mark-all-read`, { method: 'POST', headers: auth() });
    } catch { /* optimistic */ }
  }, []);

  const handleClick = useCallback(async (n: NotificationItem) => {
    if (!n.read_at) await markRead(n.id);
    if (n.trip_id) {
      setOpen(false);
      router.push(`/trips/${n.trip_id}`);
    }
  }, [markRead, router]);

  const grouped = groupByDay(items);

  return (
    <div className="relative" ref={wrapRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative p-2.5 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-50 transition-colors"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center text-[10px] font-black text-white bg-rose-500 rounded-full ring-2 ring-white">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 mt-3 w-[380px] bg-white rounded-2xl shadow-2xl border border-slate-100 z-50 overflow-hidden"
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
              <h3 className="text-sm font-black text-slate-900">Notifications</h3>
              {unread > 0 && (
                <button
                  onClick={markAllRead}
                  className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                >
                  <Check className="w-3 h-3" /> Mark all read
                </button>
              )}
            </div>

            <div className="max-h-[460px] overflow-y-auto">
              {loading && items.length === 0 ? (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
                </div>
              ) : items.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
                  <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center mb-3">
                    <Bell className="w-5 h-5 text-slate-300" />
                  </div>
                  <p className="text-sm font-black text-slate-700">You&apos;re all caught up</p>
                  <p className="text-xs text-slate-400 font-medium mt-1">
                    New activity on your trips will show up here.
                  </p>
                </div>
              ) : (
                grouped.map(([label, bucket]) => (
                  <div key={label}>
                    <div className="px-5 pt-3 pb-1 text-[10px] font-black uppercase tracking-widest text-slate-400">
                      {label}
                    </div>
                    {bucket.map((n) => {
                      const m = renderMessage(n);
                      const unread = !n.read_at;
                      return (
                        <button
                          key={n.id}
                          onClick={() => handleClick(n)}
                          className={`w-full flex items-start gap-3 px-5 py-3 border-b border-slate-50 text-left hover:bg-slate-50 transition-colors ${
                            unread ? 'bg-indigo-50/40' : ''
                          }`}
                        >
                          <div className="w-8 h-8 shrink-0 rounded-xl bg-slate-50 flex items-center justify-center text-base">
                            {m.icon}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-slate-600 font-medium leading-snug">{m.text}</p>
                            <p className="text-[11px] text-slate-400 font-bold mt-1">{timeAgo(n.created_at)}</p>
                          </div>
                          {unread && <span className="w-2 h-2 rounded-full bg-indigo-500 mt-2 shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function groupByDay(items: NotificationItem[]): [string, NotificationItem[]][] {
  const map = new Map<string, NotificationItem[]>();
  for (const n of items) {
    const label = dayLabel(n.created_at);
    const bucket = map.get(label) ?? [];
    bucket.push(n);
    map.set(label, bucket);
  }
  return Array.from(map.entries());
}
