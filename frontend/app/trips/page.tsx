'use client';

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  LayoutGrid, Map as MapIcon, Sparkles, ChevronLeft,
  ChevronDown, Plus, ChevronRight, Calendar, Trash2, AlertTriangle,
  Users, Mail, Loader2, Check, X, UserPlus, ShieldCheck, Eye, Vote,
  Lightbulb,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import useAuth, { ProtectedRoute } from '@/hooks/useAuth';
import Timeline from '@/components/trip/Timeline';
import IdeaBin from '@/components/trip/IdeaBin';
import BrainstormSection from '@/components/trip/BrainstormSection';
import GoogleMap from '@/components/map/GoogleMap';
// Collaborators header removed — invite flow lives in People tab now
import ConciergeActionBar from '@/components/trip/ConciergeActionBar';
import { useTripStore, TripDay } from '@/lib/store';
import { addDays, format, isToday, parseISO } from 'date-fns';

type Mode = 'brainstorm' | 'plan' | 'concierge' | 'people';

const ROLE_OPTIONS = [
  { value: 'admin', label: 'Admin', icon: ShieldCheck, color: 'text-amber-600 bg-amber-50 border-amber-200' },
  { value: 'view_only', label: 'View Only', icon: Eye, color: 'text-sky-600 bg-sky-50 border-sky-200' },
  { value: 'view_with_vote', label: 'View with Vote', icon: Vote, color: 'text-violet-600 bg-violet-50 border-violet-200' },
] as const;

function roleMeta(role: string) {
  return ROLE_OPTIONS.find((r) => r.value === role) ?? ROLE_OPTIONS[1];
}

export default function TripPlannerPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const tripId = searchParams.get('id');
  const rawMode = searchParams.get('mode') as Mode | null;
  const initialMode: Mode =
    rawMode === 'concierge' ? 'concierge'
    : rawMode === 'people' ? 'people'
    : rawMode === 'brainstorm' ? 'brainstorm'
    : 'plan';
  const { user: currentUser } = useAuth(true);
  const [trip, setTrip] = useState<any>(null);
  const [mode, setMode] = useState<Mode>(initialMode);
  const [planDayIdx, setPlanDayIdx] = useState(0);
  const [liveDayIdx, setLiveDayIdx] = useState(0);

  const { setActiveTrip, loadEvents, events, tripDays, loadTripDays, addTripDay, deleteTripDay } = useTripStore();
  const [deleteConfirm, setDeleteConfirm] = useState<{ dayId: string; dayNumber: number; date: string } | null>(null);
  const mutatingRef = useRef(false);

  // People page state
  const [members, setMembers] = useState<any[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('');
  const [inviteStatus, setInviteStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [inviteError, setInviteError] = useState('');
  const [editingRoleFor, setEditingRoleFor] = useState<number | null>(null);
  const [pendingRole, setPendingRole] = useState('');
  const [roleUpdateLoading, setRoleUpdateLoading] = useState(false);
  const [removeConfirm, setRemoveConfirm] = useState<{ id: number; name: string } | null>(null);
  const [removeLoading, setRemoveLoading] = useState(false);
  const roleDropdownRef = useRef<HTMLDivElement>(null);

  const fetchMembers = useCallback(async () => {
    if (!tripId) return;
    const token = localStorage.getItem('token');
    if (!token) return;
    setMembersLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/members`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setMembers(await res.json());
    } catch { /* keep current */ }
    finally { setMembersLoading(false); }
  }, [tripId]);

  useEffect(() => {
    if (mode === 'people') fetchMembers();
  }, [mode, fetchMembers]);

  useEffect(() => {
    if (editingRoleFor === null) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (roleDropdownRef.current && !roleDropdownRef.current.contains(e.target as Node)) {
        setEditingRoleFor(null);
        setPendingRole('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [editingRoleFor]);

  const handleInvite = useCallback(async () => {
    if (!inviteEmail.trim() || !inviteRole || !tripId) return;
    setInviteStatus('loading');
    setInviteError('');
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/invite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      if (res.ok) {
        setInviteEmail('');
        setInviteRole('');
        setInviteStatus('success');
        fetchMembers();
        setTimeout(() => setInviteStatus('idle'), 2000);
      } else {
        const err = await res.json().catch(() => null);
        setInviteError(err?.detail ?? 'Could not invite user');
        setInviteStatus('error');
      }
    } catch {
      setInviteError('Network error — please try again');
      setInviteStatus('error');
    }
  }, [inviteEmail, inviteRole, tripId, fetchMembers]);

  const handleRoleChange = useCallback(async (memberId: number, newRole: string) => {
    if (!tripId) return;
    setRoleUpdateLoading(true);
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/members/${memberId}/role`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ role: newRole }),
      });
      if (res.ok) {
        fetchMembers();
      }
    } catch { /* ignore */ }
    finally {
      setRoleUpdateLoading(false);
      setEditingRoleFor(null);
      setPendingRole('');
    }
  }, [tripId, fetchMembers]);

  const handleRemoveMember = useCallback(async (memberId: number) => {
    if (!tripId) return;
    setRemoveLoading(true);
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/members/${memberId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok || res.status === 204) {
        fetchMembers();
      }
    } catch { /* ignore */ }
    finally {
      setRemoveLoading(false);
      setRemoveConfirm(null);
    }
  }, [tripId, fetchMembers]);

  const refreshTripData = useCallback(() => {
    if (!tripId) return;
    const token = localStorage.getItem('token');
    if (!token) return;

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => { if (data) setTrip(data); })
      .catch(() => {});

    loadTripDays(tripId, token);
    loadEvents(tripId, token);
    fetchMembers();
  }, [tripId, loadTripDays, loadEvents, fetchMembers]);

  useEffect(() => {
    if (!tripId) return;
    setActiveTrip(tripId);
    refreshTripData();
  }, [tripId, setActiveTrip, refreshTripData]);

  // Re-fetch when user navigates back to this tab/page (tab switch, bfcache restore).
  // Skip if a mutation (delete day, etc.) is in progress to avoid stale data races.
  useEffect(() => {
    const onFocus = () => { if (!mutatingRef.current) refreshTripData(); };
    const onPageShow = (e: PageTransitionEvent) => { if (e.persisted && !mutatingRef.current) refreshTripData(); };
    window.addEventListener('focus', onFocus);
    window.addEventListener('pageshow', onPageShow);
    return () => {
      window.removeEventListener('focus', onFocus);
      window.removeEventListener('pageshow', onPageShow);
    };
  }, [refreshTripData]);

  // Derive plan-mode selected day from tripDays
  const planDay: Date | null = useMemo(() => {
    if (tripDays.length === 0) return null;
    const idx = Math.min(planDayIdx, tripDays.length - 1);
    return parseISO(tripDays[idx].date);
  }, [tripDays, planDayIdx]);

  // Derive live-mode selected day from tripDays
  const liveDay: Date | null = useMemo(() => {
    if (tripDays.length === 0) return null;
    const idx = Math.min(liveDayIdx, tripDays.length - 1);
    return parseISO(tripDays[idx].date);
  }, [tripDays, liveDayIdx]);

  const isCurrentDay = liveDay ? isToday(liveDay) : false;

  const handleAddDay = useCallback(async () => {
    if (!tripId) return;
    const token = localStorage.getItem('token');
    if (!token) return;

    let nextDate: Date;
    if (tripDays.length > 0) {
      const lastDate = parseISO(tripDays[tripDays.length - 1].date);
      nextDate = addDays(lastDate, 1);
    } else if (trip?.start_date) {
      nextDate = new Date(trip.start_date);
    } else {
      nextDate = new Date();
    }

    const dateStr = format(nextDate, 'yyyy-MM-dd');
    const newDay = await addTripDay(tripId, dateStr, token);
    if (newDay) {
      const newDays = [...tripDays, newDay].sort(
        (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
      );
      const newIdx = newDays.findIndex((d) => d.id === newDay.id);
      setPlanDayIdx(newIdx >= 0 ? newIdx : newDays.length - 1);
    }
  }, [tripId, tripDays, trip, addTripDay]);

  const handleDeleteDayClick = useCallback(async () => {
    if (!tripId || tripDays.length === 0) return;
    const idx = Math.min(planDayIdx, tripDays.length - 1);
    const dayToDelete = tripDays[idx];
    if (!dayToDelete) return;

    const dayHasEvents = events.some((e) => e.day_date === dayToDelete.date);
    if (!dayHasEvents) {
      const token = localStorage.getItem('token');
      if (!token) return;
      mutatingRef.current = true;
      try {
        await deleteTripDay(tripId, dayToDelete.id, token, 'delete');
        await loadEvents(tripId, token);
        setPlanDayIdx((prev) => {
          const newLen = tripDays.length - 1;
          if (newLen <= 0) return 0;
          return Math.min(prev, newLen - 1);
        });
      } finally {
        mutatingRef.current = false;
      }
      return;
    }

    setDeleteConfirm({ dayId: dayToDelete.id, dayNumber: dayToDelete.day_number, date: dayToDelete.date });
  }, [tripId, tripDays, planDayIdx, events, deleteTripDay, loadEvents]);

  const executeDeleteDay = useCallback(async (itemsAction: 'bin' | 'delete') => {
    if (!tripId || !deleteConfirm) return;
    const token = localStorage.getItem('token');
    if (!token) return;

    mutatingRef.current = true;
    try {
      await deleteTripDay(tripId, deleteConfirm.dayId, token, itemsAction);

      // If items were sent to bin, reload ideas so they appear immediately
      if (itemsAction === 'bin') {
        try {
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/ideas`, {
            headers: { Authorization: `Bearer ${token}` },
            cache: 'no-store',
          });
          if (res.ok) {
            const raw = await res.json();
            const { setIdeas } = useTripStore.getState();
            setIdeas(raw.map((r: any) => ({
              id: String(r.id),
              title: r.title,
              lat: r.lat ?? 0,
              lng: r.lng ?? 0,
              time_hint: r.time_hint ?? null,
              added_by: r.added_by ?? null,
              up: r.up ?? 0,
              down: r.down ?? 0,
              my_vote: r.my_vote ?? 0,
            })));
          }
        } catch { /* ignore */ }
      }

      await loadEvents(tripId, token);
    } finally {
      mutatingRef.current = false;
    }

    setPlanDayIdx((prev) => {
      const newLen = tripDays.length - 1;
      if (newLen <= 0) return 0;
      return Math.min(prev, newLen - 1);
    });
    setDeleteConfirm(null);
  }, [tripId, deleteConfirm, tripDays, deleteTripDay, loadEvents]);

  const switchMode = useCallback((m: Mode) => {
    setMode(m);
    const params = new URLSearchParams();
    if (tripId) params.set('id', tripId);
    if (m !== 'plan') params.set('mode', m);
    router.replace(`/trips?${params.toString()}`, { scroll: false });
  }, [tripId, router]);

  const sidebarBtn = (m: Mode, icon: React.ReactNode, label: string) => (
    <motion.button
      onClick={() => switchMode(m)}
      title={label}
      whileTap={{ scale: 0.94 }}
      transition={{ type: 'spring', stiffness: 380, damping: 32 }}
      className={`flex flex-col items-center gap-1.5 p-3 rounded-2xl transition-colors ${
        mode === m
          ? 'bg-white/15 text-white'
          : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
      }`}
    >
      {icon}
      <span className="text-[9px] font-black uppercase tracking-widest">{label}</span>
    </motion.button>
  );

  const safePlanIdx = Math.min(planDayIdx, Math.max(tripDays.length - 1, 0));
  const safeLiveIdx = Math.min(liveDayIdx, Math.max(tripDays.length - 1, 0));

  const currentUserIsAdmin = useMemo(() => {
    if (!currentUser) return false;
    return members.some((m: any) => m.user_id === currentUser.id && m.role === 'admin');
  }, [members, currentUser]);

  const currentUserCanVote = useMemo(() => {
    if (!currentUser) return false;
    return members.some(
      (m: any) => m.user_id === currentUser.id && (m.role === 'admin' || m.role === 'view_with_vote'),
    );
  }, [members, currentUser]);

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-white overflow-hidden">
        {/* ── Icon sidebar ───────────────────────────────────────────────── */}
        <aside className="w-[72px] bg-slate-900 flex flex-col items-center py-6 gap-3 shrink-0 z-30">
          <Link
            href="/dashboard"
            className="w-11 h-11 bg-indigo-600 rounded-2xl flex items-center justify-center font-black text-white text-xl shadow-lg shadow-indigo-900/50 hover:scale-105 transition-transform mb-4"
          >
            R
          </Link>

          <nav className="flex flex-col gap-2 w-full px-2">
            {sidebarBtn('brainstorm', <Lightbulb className="w-5 h-5" />, 'Ideas')}
            {sidebarBtn('plan', <MapIcon className="w-5 h-5" />, 'Plan')}
            {sidebarBtn('concierge', <Sparkles className="w-5 h-5" />, 'Live')}
            {sidebarBtn('people', <Users className="w-5 h-5" />, 'People')}
          </nav>

          <div className="mt-auto flex flex-col items-center gap-4 pb-2">
            <Link
              href="/dashboard"
              title="Dashboard"
              className="p-3 text-slate-500 hover:text-white transition-colors"
            >
              <LayoutGrid className="w-5 h-5" />
            </Link>
          </div>
        </aside>

        {/* ── Main area ──────────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <header className="h-16 border-b border-slate-100 flex items-center justify-between px-8 bg-white shrink-0">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="p-2 hover:bg-slate-50 rounded-xl transition-colors">
                <ChevronLeft className="w-5 h-5 text-slate-400" />
              </Link>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-lg font-black text-slate-900 tracking-tight">
                    {trip?.name ?? 'Loading…'}
                  </h1>
                  <span className={`px-2.5 py-0.5 text-[9px] font-black uppercase tracking-[0.2em] rounded-full border ${
                    mode === 'concierge'
                      ? 'bg-green-50 text-green-600 border-green-100'
                      : mode === 'people'
                      ? 'bg-violet-50 text-violet-600 border-violet-100'
                      : mode === 'brainstorm'
                      ? 'bg-amber-50 text-amber-600 border-amber-100'
                      : 'bg-indigo-50 text-indigo-600 border-indigo-100'
                  }`}>
                    {mode === 'plan' ? 'Planning' : mode === 'concierge' ? 'Live Concierge' : mode === 'brainstorm' ? 'Brainstorm' : 'People'}
                  </span>
                </div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  {mode === 'plan' ? 'Full Itinerary View' : mode === 'concierge' ? 'Day-by-Day View' : mode === 'brainstorm' ? 'Chat + Bin' : 'Trip Members'}
                </p>
              </div>
            </div>

            {/* intentionally empty — invite moved to People tab */}
            <div />
          </header>

          {/* ── Mode region (animated) ─────────────────────────────────────── */}
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={mode}
              className="flex-1 flex flex-col min-h-0"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            >
          {/* ── Brainstorm Mode ───────────────────────────────────────────── */}
          {mode === 'brainstorm' && (
            <BrainstormSection tripId={tripId} />
          )}

          {/* ── Plan Mode ─────────────────────────────────────────────────── */}
          {mode === 'plan' && (
            <div className="flex-1 flex overflow-hidden bg-slate-50">
              {/* Timeline with day navigation */}
              <div className="w-[420px] shrink-0 border-r border-slate-100 bg-white overflow-hidden flex flex-col">
                {/* Day navigation header */}
                <div className="px-5 pt-4 pb-3 border-b border-slate-100 shrink-0">
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="text-sm font-black text-slate-900 uppercase tracking-widest">
                      Full Itinerary
                    </h2>
                    {currentUserIsAdmin && (
                      <button
                        onClick={handleAddDay}
                        title="Add Day"
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-xl text-xs font-black hover:bg-indigo-500 transition-all shadow-sm"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        Add Day
                      </button>
                    )}
                  </div>

                  {tripDays.length > 0 && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setPlanDayIdx(Math.max(0, safePlanIdx - 1))}
                        disabled={safePlanIdx === 0}
                        className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 hover:text-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                        title="Previous Day"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>

                      <div className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-indigo-50 rounded-xl">
                        <Calendar className="w-3.5 h-3.5 text-indigo-500" />
                        <span className="text-sm font-black text-indigo-700">
                          Day {tripDays[safePlanIdx]?.day_number ?? safePlanIdx + 1}
                        </span>
                        <span className="text-xs font-bold text-indigo-500">
                          — {planDay ? format(planDay, 'EEE, MMM d') : ''}
                        </span>
                      </div>

                      {currentUserIsAdmin && (
                        <button
                          onClick={handleDeleteDayClick}
                          className="p-1.5 rounded-lg border border-slate-200 text-slate-400 hover:bg-rose-50 hover:text-rose-500 hover:border-rose-200 transition-all"
                          title="Delete Day"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}

                      <button
                        onClick={() => setPlanDayIdx(Math.min(tripDays.length - 1, safePlanIdx + 1))}
                        disabled={safePlanIdx >= tripDays.length - 1}
                        className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 hover:text-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                        title="Next Day"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  )}

                  {tripDays.length === 0 && (
                    <p className="text-xs text-slate-400 font-medium">
                      No days added yet. Click "Add Day" to start planning.
                    </p>
                  )}
                </div>
                <Timeline tripId={tripId} filterDay={planDay ?? undefined} readOnly={!currentUserIsAdmin} canVote={currentUserCanVote} />
              </div>
              {/* Map */}
              <div className="flex-1 relative">
                <GoogleMap filterDay={planDay ?? undefined} tripId={tripId} />
              </div>
              {/* Idea Bin */}
              <div className="w-80 shrink-0 border-l border-slate-100 bg-white overflow-hidden flex flex-col">
                <IdeaBin tripId={tripId} readOnly={!currentUserIsAdmin} canVote={currentUserCanVote} />
              </div>
            </div>
          )}

          {/* ── Concierge / Live Mode ──────────────────────────────────────── */}
          {mode === 'concierge' && (
            <div className="flex-1 flex overflow-hidden">
              {/* Day Timeline */}
              <div className="w-[380px] shrink-0 border-r border-slate-100 bg-white overflow-hidden flex flex-col">
                {/* Day selector header — only shows days added in Plan mode */}
                <div className="px-6 pt-5 pb-4 border-b border-slate-50 shrink-0">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Select Day</p>
                  {tripDays.length > 0 ? (
                    <div className="relative">
                      <select
                        value={safeLiveIdx}
                        onChange={(e) => setLiveDayIdx(Number(e.target.value))}
                        className="w-full appearance-none pl-4 pr-10 py-2.5 bg-slate-50 border border-slate-100 rounded-xl text-sm font-black text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
                      >
                        {tripDays.map((day, idx) => {
                          const d = parseISO(day.date);
                          return (
                            <option key={day.id} value={idx}>
                              Day {day.day_number} — {format(d, 'EEE, MMM d')}{isToday(d) ? ' (Today)' : ''}
                            </option>
                          );
                        })}
                      </select>
                      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400 font-medium">
                      No days planned yet. Switch to Plan mode to add days.
                    </p>
                  )}
                </div>
                <Timeline tripId={tripId} filterDay={liveDay ?? undefined} readOnly canVote={currentUserCanVote} />
              </div>

              {/* Map + optional concierge overlay */}
              <div className="flex-1 relative">
                <GoogleMap filterDay={liveDay ?? undefined} tripId={tripId} />
                {isCurrentDay && currentUserIsAdmin && (
                  <ConciergeActionBar />
                )}
                {!isCurrentDay && liveDay && (
                  <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 px-5 py-3 bg-white/80 backdrop-blur border border-slate-200 rounded-2xl shadow-lg">
                    <p className="text-xs font-black text-slate-500 uppercase tracking-widest">
                      Concierge activates on {format(liveDay, 'EEE, MMM d')}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── People Mode ────────────────────────────────────────────────── */}
          {mode === 'people' && (
            <div className="flex-1 overflow-y-auto bg-slate-50">
              <div className="max-w-2xl mx-auto py-10 px-8">
                {/* Invite card — admin only */}
                {currentUserIsAdmin && (
                  <div className="bg-white rounded-2xl border border-slate-100 p-7 shadow-sm mb-8">
                    <div className="flex items-center gap-3 mb-5">
                      <div className="w-10 h-10 bg-indigo-50 rounded-xl flex items-center justify-center">
                        <UserPlus className="w-5 h-5 text-indigo-600" />
                      </div>
                      <div>
                        <h3 className="text-base font-black text-slate-900">Invite a Traveler</h3>
                        <p className="text-xs text-slate-400 font-medium">They&apos;ll receive a trip invitation on their dashboard</p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {/* Email */}
                      <div className="relative flex-1">
                        <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                          type="email"
                          placeholder="traveler@email.com"
                          value={inviteEmail}
                          onChange={(e) => { setInviteEmail(e.target.value); setInviteStatus('idle'); setInviteError(''); }}
                          onKeyDown={(e) => e.key === 'Enter' && handleInvite()}
                          className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium placeholder-slate-400 focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all"
                        />
                      </div>
                      {/* Role dropdown */}
                      <div className="relative w-[180px] shrink-0">
                        <select
                          value={inviteRole}
                          onChange={(e) => setInviteRole(e.target.value)}
                          className={`w-full appearance-none pl-4 pr-9 py-3 border border-slate-200 rounded-xl text-sm font-bold focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer transition-all ${
                            inviteRole ? 'bg-white text-slate-800' : 'bg-slate-50 text-slate-400'
                          }`}
                        >
                          <option value="" disabled>Add role</option>
                          {ROLE_OPTIONS.map((r) => (
                            <option key={r.value} value={r.value}>{r.label}</option>
                          ))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                      </div>
                      {/* Invite button */}
                      <button
                        onClick={handleInvite}
                        disabled={inviteStatus === 'loading' || !inviteEmail.trim() || !inviteRole}
                        className="px-5 py-3 bg-indigo-600 text-white rounded-xl text-sm font-black hover:bg-indigo-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed min-w-[100px] flex items-center justify-center gap-2"
                      >
                        {inviteStatus === 'loading' ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : inviteStatus === 'success' ? (
                          <><Check className="w-4 h-4" /> Sent!</>
                        ) : (
                          'Invite'
                        )}
                      </button>
                    </div>
                    {inviteError && (
                      <p className="text-rose-500 text-xs font-bold mt-2 px-1">{inviteError}</p>
                    )}
                  </div>
                )}

                {/* Members list */}
                <div className="flex items-center gap-2 mb-4">
                  <Users className="w-4 h-4 text-slate-400" />
                  <h2 className="text-sm font-black text-slate-600 uppercase tracking-widest">
                    {members.length} {members.length === 1 ? 'Member' : 'Members'}
                  </h2>
                </div>

                {membersLoading ? (
                  <div className="flex items-center justify-center py-16">
                    <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                  </div>
                ) : (
                  <div className="space-y-3">
                    {members.map((member: any) => {
                      const name = member.user?.name ?? 'Unknown';
                      const email = member.user?.email ?? '';
                      const initials = name
                        .split(' ')
                        .map((n: string) => n[0])
                        .join('')
                        .toUpperCase()
                        .slice(0, 2);
                      const isInvited = member.status === 'invited';
                      const meta = roleMeta(member.role);
                      const RoleIcon = meta.icon;
                      const isEditing = editingRoleFor === member.id;
                      const isSelf = currentUser && member.user_id === currentUser.id;

                      return (
                        <div
                          key={member.id}
                          className="bg-white rounded-2xl border border-slate-100 p-5 flex items-center gap-4 shadow-sm hover:shadow-md hover:border-slate-200 transition-all"
                        >
                          {/* Avatar */}
                          <div
                            className={`w-12 h-12 rounded-full flex items-center justify-center font-black text-sm text-white shrink-0 overflow-hidden ${
                              isInvited ? 'bg-slate-300' : 'bg-indigo-600'
                            }`}
                          >
                            {member.user?.avatar_url
                              ? <img src={member.user.avatar_url} alt={name} className="w-full h-full object-cover" />
                              : initials || '?'
                            }
                          </div>

                          {/* Name + email */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-black text-slate-900 truncate">
                                {name}
                                {isSelf && <span className="text-slate-400 font-bold ml-1">(you)</span>}
                              </p>
                            </div>
                            <p className="text-xs text-slate-400 font-medium truncate">{email}</p>
                          </div>

                          {/* Invited badge */}
                          {isInvited && (
                            <span className="px-3 py-1.5 bg-amber-50 border border-amber-200 text-amber-600 rounded-full text-[11px] font-black uppercase tracking-wide shrink-0">
                              Invited
                            </span>
                          )}

                          {/* Role badge (always visible) */}
                          <span className={`flex items-center gap-1.5 px-3 py-1.5 border rounded-full text-[11px] font-black shrink-0 ${meta.color}`}>
                            <RoleIcon className="w-3.5 h-3.5" />
                            {meta.label}
                          </span>

                          {/* Role change + Remove — admin only, not for self */}
                          {currentUserIsAdmin && !isSelf && (
                            <div className="flex items-center gap-1 shrink-0">
                            <div className="relative">
                              {!isEditing ? (
                                <button
                                  onClick={() => { setEditingRoleFor(member.id); setPendingRole(member.role); }}
                                  className="p-2 text-slate-300 hover:text-indigo-500 hover:bg-indigo-50 rounded-lg transition-all"
                                  title="Change role"
                                >
                                  <ChevronDown className="w-4 h-4" />
                                </button>
                              ) : (
                                <div ref={roleDropdownRef} className="absolute right-0 top-full mt-1 z-20 bg-white border border-slate-200 rounded-xl shadow-xl p-2 w-52">
                                  {ROLE_OPTIONS.map((r) => {
                                    const OptIcon = r.icon;
                                    const isSelected = pendingRole === r.value;
                                    return (
                                      <button
                                        key={r.value}
                                        onClick={() => setPendingRole(r.value)}
                                        className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-bold transition-all ${
                                          isSelected
                                            ? 'bg-indigo-50 text-indigo-700'
                                            : 'text-slate-600 hover:bg-slate-50'
                                        }`}
                                      >
                                        <OptIcon className="w-4 h-4 shrink-0" />
                                        {r.label}
                                        {isSelected && <Check className="w-3.5 h-3.5 ml-auto text-indigo-500" />}
                                      </button>
                                    );
                                  })}
                                  {/* Confirm / Cancel — only show when role actually changed */}
                                  {pendingRole !== member.role && (
                                    <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-slate-100">
                                      <button
                                        onClick={() => handleRoleChange(member.id, pendingRole)}
                                        disabled={roleUpdateLoading}
                                        className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-black hover:bg-indigo-500 transition-all disabled:opacity-50"
                                      >
                                        {roleUpdateLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                                        Confirm
                                      </button>
                                      <button
                                        onClick={() => { setEditingRoleFor(null); setPendingRole(''); }}
                                        className="flex items-center justify-center gap-1 px-3 py-1.5 bg-slate-100 text-slate-500 rounded-lg text-xs font-black hover:bg-slate-200 transition-all"
                                      >
                                        <X className="w-3 h-3" />
                                        Cancel
                                      </button>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                            <button
                              onClick={() => setRemoveConfirm({ id: member.id, name })}
                              className="p-2 text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all"
                              title="Remove member"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                    {members.length === 0 && !membersLoading && (
                      <div className="text-center py-16">
                        <Users className="w-12 h-12 text-slate-200 mx-auto mb-4" />
                        <p className="text-slate-400 font-bold">No members yet. Invite someone above!</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* Remove Member Confirmation Dialog */}
      {removeConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-[400px] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 pt-6 pb-4 flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-rose-50 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5 text-rose-500" />
              </div>
              <div>
                <h3 className="text-base font-black text-slate-900">Remove {removeConfirm.name}?</h3>
                <p className="text-sm text-slate-500 mt-1">
                  They will lose access to this trip and it will no longer appear on their dashboard.
                </p>
              </div>
            </div>
            <div className="px-6 pb-6 flex gap-2">
              <button
                onClick={() => handleRemoveMember(removeConfirm.id)}
                disabled={removeLoading}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-rose-600 text-white rounded-xl text-sm font-black hover:bg-rose-500 transition-all disabled:opacity-50"
              >
                {removeLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Remove
              </button>
              <button
                onClick={() => setRemoveConfirm(null)}
                className="flex-1 px-4 py-3 bg-slate-100 text-slate-600 rounded-xl text-sm font-black hover:bg-slate-200 transition-all"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Day Confirmation Dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-[420px] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 pt-6 pb-4 flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <h3 className="text-base font-black text-slate-900">
                  Delete Day {deleteConfirm.dayNumber}?
                </h3>
                <p className="text-sm text-slate-500 mt-1">
                  <span className="font-bold text-slate-600">
                    {format(parseISO(deleteConfirm.date), 'EEEE, MMM d')}
                  </span>
                  {' '}will be removed. What should happen to the items on this day?
                </p>
              </div>
            </div>

            <div className="px-6 pb-6 flex flex-col gap-2">
              <button
                onClick={() => executeDeleteDay('bin')}
                className="w-full flex items-center gap-3 px-4 py-3 bg-indigo-50 border border-indigo-100 rounded-xl text-sm font-bold text-indigo-700 hover:bg-indigo-100 transition-all"
              >
                <span className="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-600 text-xs font-black">↩</span>
                Send items back to Idea Bin
              </button>
              <button
                onClick={() => executeDeleteDay('delete')}
                className="w-full flex items-center gap-3 px-4 py-3 bg-rose-50 border border-rose-100 rounded-xl text-sm font-bold text-rose-600 hover:bg-rose-100 transition-all"
              >
                <Trash2 className="w-4 h-4 ml-1.5 mr-0.5" />
                No, delete them permanently
              </button>
              <button
                onClick={() => setDeleteConfirm(null)}
                className="w-full px-4 py-2.5 text-sm font-bold text-slate-400 hover:text-slate-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </ProtectedRoute>
  );
}
