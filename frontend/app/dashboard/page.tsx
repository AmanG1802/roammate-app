'use client';

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import Link from 'next/link';
import { Plus, Map, Calendar, Users, ChevronRight, Search, LayoutGrid, Loader2, X, MailOpen, Plane, Check, XCircle, Trash2, Pencil, AlertTriangle, History, Rocket } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import useAuth, { ProtectedRoute } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';
import NotificationBell, { type NotificationBellHandle } from '@/components/layout/NotificationBell';
import GroupsPanel from '@/components/groups/GroupsPanel';
import TodayWidget, { type TodayWidgetHandle } from '@/components/dashboard/TodayWidget';
import DashboardTripPlanner from '@/components/dashboard/DashboardTripPlanner';
import UserMenu from '@/components/UserMenu';
import PersonaSoftPrompt from '@/components/PersonaSoftPrompt';
import OnboardingPersonaModal from '@/components/OnboardingPersonaModal';

type Section = 'dashboard' | 'trips' | 'invitations' | 'groups';

function getInitials(name: string): string {
  return name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2);
}

export default function DashboardPage() {
  const { user } = useAuth(true);
  const router = useRouter();
  const [section, setSection] = useState<Section>('dashboard');
  const [trips, setTrips] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTripName, setNewTripName] = useState('');
  const [newTripStartDate, setNewTripStartDate] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const [invitations, setInvitations] = useState<any[]>([]);
  const [invitationsLoading, setInvitationsLoading] = useState(false);
  const [respondingTo, setRespondingTo] = useState<number | null>(null);
  const [groupInvitesCount, setGroupInvitesCount] = useState(0);
  const [showPersonaModal, setShowPersonaModal] = useState(false);
  const [showSkipToast, setShowSkipToast] = useState(false);

  const widgetRef = useRef<TodayWidgetHandle>(null);
  const bellRef = useRef<NotificationBellHandle>(null);

  const refreshDashboard = useCallback(() => {
    widgetRef.current?.refresh();
    bellRef.current?.refresh();
  }, []);

  // Show persona onboarding modal once per login session when no persona is set
  useEffect(() => {
    if (!user) return;
    const shownKey = `persona_modal_shown_${(user as any).id}`;
    if (sessionStorage.getItem(shownKey)) return;
    const p = (user as any).personas;
    if (p === null || (Array.isArray(p) && p.length === 0)) {
      sessionStorage.setItem(shownKey, '1');
      setShowPersonaModal(true);
    }
  }, [user]);

  const handlePersonaComplete = async (personas: string[]) => {
    const token = localStorage.getItem('token');
    const API = process.env.NEXT_PUBLIC_API_URL ?? '';
    try {
      await fetch(`${API}/users/me/personas`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ personas }),
      });
      const saved = localStorage.getItem('user');
      if (saved) {
        const u = JSON.parse(saved);
        localStorage.setItem('user', JSON.stringify({ ...u, personas }));
      }
    } catch {}
    setShowPersonaModal(false);
  };

  const handlePersonaSkip = async () => {
    const token = localStorage.getItem('token');
    const API = process.env.NEXT_PUBLIC_API_URL ?? '';
    try {
      await fetch(`${API}/users/me/personas`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ personas: [] }),
      });
      const saved = localStorage.getItem('user');
      if (saved) {
        const u = JSON.parse(saved);
        localStorage.setItem('user', JSON.stringify({ ...u, personas: [] }));
      }
    } catch {}
    setShowPersonaModal(false);
    setShowSkipToast(true);
    setTimeout(() => setShowSkipToast(false), 4000);
  };

  const openCreateModal = () => {
    setNewTripName('');
    setNewTripStartDate('');
    setCreateError('');
    setIsModalOpen(true);
  };


  const onTripMutated = useCallback(() => {
    fetchTrips();
    refreshDashboard();
  }, [refreshDashboard]);

  useEffect(() => {
    fetchTrips();
    fetchInvitations();
  }, []);

  const fetchTrips = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        router.push('/login');
        return;
      }
      if (response.ok) setTrips(await response.json());
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchInvitations = async () => {
    setInvitationsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/invitations/pending`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setInvitations(await res.json());
    } catch { /* keep current */ }
    finally { setInvitationsLoading(false); }
  };

  const handleAcceptInvite = async (memberId: number) => {
    setRespondingTo(memberId);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/invitations/${memberId}/accept`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setInvitations((prev) => prev.filter((inv) => inv.id !== memberId));
        onTripMutated();
      }
    } catch { /* ignore */ }
    finally { setRespondingTo(null); }
  };

  const handleDeclineInvite = async (memberId: number) => {
    setRespondingTo(memberId);
    try {
      const token = localStorage.getItem('token');
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/invitations/${memberId}/decline`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      setInvitations((prev) => prev.filter((inv) => inv.id !== memberId));
    } catch { /* ignore */ }
    finally { setRespondingTo(null); }
  };

  const handleCreateTrip = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTripName.trim() || !newTripStartDate) return;
    setIsCreating(true);
    setCreateError('');
    try {
      const token = localStorage.getItem('token');
      const body: Record<string, unknown> = { name: newTripName };
      body.start_date = `${newTripStartDate}T00:00:00`;
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        router.push('/login');
        return;
      }
      if (response.ok) {
        setNewTripName('');
        setNewTripStartDate('');
        setCreateError('');
        setIsModalOpen(false);
        onTripMutated();
      } else {
        const err = await response.json().catch(() => null);
        setCreateError(err?.detail ?? `Failed to create trip (${response.status})`);
      }
    } catch (err) {
      setCreateError('Network error — please try again');
    } finally {
      setIsCreating(false);
    }
  };

  const [tripsTab, setTripsTab] = useState<'current' | 'past'>('current');

  const sortedTrips = useMemo(() => {
    return [...trips].sort((a, b) => {
      const da = a.start_date ? new Date(a.start_date).getTime() : Infinity;
      const db = b.start_date ? new Date(b.start_date).getTime() : Infinity;
      return da - db;
    });
  }, [trips]);

  const { currentAndUpcoming, pastTrips } = useMemo(() => {
    const now = new Date();
    const todayStr = now.toISOString().split('T')[0];
    const cur: any[] = [];
    const past: any[] = [];
    for (const t of sortedTrips) {
      const ed = t.end_date ?? t.start_date;
      if (ed && ed.split('T')[0] < todayStr) {
        past.push(t);
      } else {
        cur.push(t);
      }
    }
    return { currentAndUpcoming: cur, pastTrips: past };
  }, [sortedTrips]);

  const filteredTrips = useMemo(() => {
    if (!searchQuery.trim()) return tripsTab === 'current' ? currentAndUpcoming : pastTrips;
    const q = searchQuery.toLowerCase();
    const base = tripsTab === 'current' ? currentAndUpcoming : pastTrips;
    return base.filter((t: any) => t.name.toLowerCase().includes(q));
  }, [searchQuery, tripsTab, currentAndUpcoming, pastTrips]);

  const navItem = (id: Section, icon: React.ReactNode, label: string) => (
    <button
      onClick={() => setSection(id)}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-black text-sm transition-colors ${
        section === id
          ? 'bg-indigo-50 text-indigo-600'
          : 'text-slate-400 hover:text-slate-700 hover:bg-slate-50'
      }`}
    >
      {icon}
      {label}
    </button>
  );

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-slate-50 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-60 bg-white border-r border-slate-100 flex flex-col p-5 z-20 shrink-0">
          <Link href="/" className="flex items-center gap-2 mb-10">
            <div className="w-8 h-8 bg-indigo-600 rounded-xl flex items-center justify-center font-bold text-white">R</div>
            <span className="text-xl font-black text-slate-900 tracking-tight">Roammate</span>
          </Link>

          <nav className="flex-1 space-y-1">
            {navItem('dashboard', <LayoutGrid className="w-5 h-5" />, 'Dashboard')}
            {navItem('trips', <Map className="w-5 h-5" />, 'My Trips')}
            <div className="relative">
              {navItem('invitations', <MailOpen className="w-5 h-5" />, 'Trip Invitations')}
              {invitations.length > 0 && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 min-w-[20px] h-5 flex items-center justify-center text-[10px] font-black text-white bg-indigo-600 rounded-full px-1.5">
                  {invitations.length}
                </span>
              )}
            </div>
            <div className="relative">
              {navItem('groups', <Users className="w-5 h-5" />, 'Groups')}
              {groupInvitesCount > 0 && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 min-w-[20px] h-5 flex items-center justify-center text-[10px] font-black text-white bg-indigo-600 rounded-full px-1.5">
                  {groupInvitesCount}
                </span>
              )}
            </div>
          </nav>

          {/* Soft persona prompt (shown when no personas set and modal is not open) */}
          {((user as any)?.personas !== null && (user as any)?.personas?.length === 0) && !showPersonaModal && (
            <PersonaSoftPrompt />
          )}

          {/* User menu at the bottom */}
          <UserMenu user={user} getInitials={getInitials} />
        </aside>

        {/* Main */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <header className="h-16 border-b border-slate-100 bg-white px-8 flex items-center justify-between shrink-0">
            <div className="relative w-80">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search trips..."
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setSection('trips'); }}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-100 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <NotificationBell ref={bellRef} />
              <button
                onClick={openCreateModal}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100"
              >
                <Plus className="w-4 h-4" />
                New Trip
              </button>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto p-8">
            {/* Dashboard overview */}
            {section === 'dashboard' && (
              <>
                <div className="mb-6">
                  <h2 className="text-3xl font-black text-slate-900 mb-1">
                    {user?.name ? `Hey, ${user.name.split(' ')[0]}.` : 'Your Adventures.'}
                  </h2>
                  <p className="text-slate-500 font-medium">
                    {currentAndUpcoming.length === 0 ? "No upcoming trips — create your first one." : `You have ${currentAndUpcoming.length} ${currentAndUpcoming.length === 1 ? 'trip' : 'trips'} on the horizon.`}
                  </p>
                </div>
                <DashboardTripPlanner onTripCreated={refreshDashboard} />
                <TodayWidget ref={widgetRef} onNewTrip={openCreateModal} />
                <TripGrid
                  trips={currentAndUpcoming.slice(0, 6)}
                  isLoading={isLoading}
                  onNewTrip={openCreateModal}
                  onTripUpdate={onTripMutated}
                />
              </>
            )}

            {/* My Trips with sub-section toggle */}
            {(section === 'trips' || searchQuery) && (
              <>
                {searchQuery ? (
                  <div className="mb-8">
                    <h2 className="text-3xl font-black text-slate-900 mb-1">
                      Results for &ldquo;{searchQuery}&rdquo;
                    </h2>
                  </div>
                ) : (
                  <div className="flex items-center justify-center gap-1 mb-8 bg-slate-100 rounded-xl p-1 max-w-sm mx-auto">
                    <button
                      onClick={() => setTripsTab('current')}
                      className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-black transition-all ${
                        tripsTab === 'current'
                          ? 'bg-white text-indigo-600 shadow-sm'
                          : 'text-slate-400 hover:text-slate-600'
                      }`}
                    >
                      <Rocket className="w-4 h-4" />
                      Ongoing & Upcoming
                    </button>
                    <button
                      onClick={() => setTripsTab('past')}
                      className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-black transition-all ${
                        tripsTab === 'past'
                          ? 'bg-white text-indigo-600 shadow-sm'
                          : 'text-slate-400 hover:text-slate-600'
                      }`}
                    >
                      <History className="w-4 h-4" />
                      Past Trips
                    </button>
                  </div>
                )}
                <TripGrid
                  trips={filteredTrips}
                  isLoading={isLoading}
                  onNewTrip={openCreateModal}
                  onTripUpdate={onTripMutated}
                  emptyLabel={
                    searchQuery
                      ? 'No trips match your search.'
                      : undefined
                  }
                  emptyMode={searchQuery ? 'search' : tripsTab}
                />
              </>
            )}

            {/* Trip Invitations */}
            {section === 'invitations' && !searchQuery && (
              <>
                <div className="mb-8">
                  <h2 className="text-3xl font-black text-slate-900 mb-1">Trip Invitations</h2>
                  <p className="text-slate-500 font-medium">
                    {invitations.length > 0
                      ? `You have ${invitations.length} pending ${invitations.length === 1 ? 'invitation' : 'invitations'}.`
                      : ''}
                  </p>
                </div>

                {invitationsLoading ? (
                  <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
                  </div>
                ) : invitations.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-24 text-center">
                    <div className="w-24 h-24 bg-indigo-50 rounded-[2rem] flex items-center justify-center mb-6 relative">
                      <Plane className="w-12 h-12 text-indigo-300 -rotate-45" />
                      <span className="absolute -bottom-1 -right-1 text-2xl">💤</span>
                    </div>
                    <h3 className="text-2xl font-black text-slate-900 mb-2">All quiet on the travel front!</h3>
                    <p className="text-slate-500 font-medium max-w-sm mb-1">
                      No one&apos;s dragged you into an adventure yet.
                    </p>
                    <p className="text-slate-400 text-sm font-medium max-w-sm">
                      When a fellow traveler invites you, it&apos;ll show up right here.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {invitations.map((inv: any) => (
                      <motion.div
                        key={inv.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="bg-white rounded-[2rem] border border-slate-100 p-7 shadow-sm hover:shadow-lg hover:border-indigo-100 transition-all"
                      >
                        <div className="text-4xl mb-4">✉️</div>
                        <h3 className="text-xl font-black text-slate-900 mb-1 leading-tight">
                          {inv.trip?.name ?? 'Unknown Trip'}
                        </h3>
                        <div className="flex items-center gap-2 text-slate-400 text-xs font-bold mb-2">
                          <Calendar className="w-3.5 h-3.5" />
                          {inv.trip?.start_date
                            ? new Date(inv.trip.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                            : 'Dates TBD'}
                        </div>
                        {inv.inviter && (
                          <p className="text-sm text-slate-500 font-medium mb-5">
                            Invited by <span className="font-bold text-slate-700">{inv.inviter.name}</span>
                          </p>
                        )}
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleAcceptInvite(inv.id)}
                            disabled={respondingTo === inv.id}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-500 transition-all disabled:opacity-50"
                          >
                            {respondingTo === inv.id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <><Check className="w-4 h-4" /> Accept</>
                            )}
                          </button>
                          <button
                            onClick={() => handleDeclineInvite(inv.id)}
                            disabled={respondingTo === inv.id}
                            className="flex items-center justify-center gap-2 px-4 py-3 bg-slate-100 text-slate-500 rounded-xl font-black text-sm hover:bg-rose-50 hover:text-rose-500 transition-all disabled:opacity-50"
                          >
                            <XCircle className="w-4 h-4" /> Decline
                          </button>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </>
            )}

            {section === 'groups' && !searchQuery && (
              <GroupsPanel onInvitationsChange={setGroupInvitesCount} />
            )}
          </div>
        </main>

        {/* Create Trip Modal */}
        <AnimatePresence>
          {isModalOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-900/40 backdrop-blur-sm">
              <motion.div
                initial={{ opacity: 0, scale: 0.9, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: 20 }}
                className="bg-white rounded-[2.5rem] w-full max-w-lg p-10 shadow-2xl relative"
              >
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="absolute top-6 right-6 p-2 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-6 h-6" />
                </button>
                <h3 className="text-3xl font-black text-slate-900 mb-2">New Adventure.</h3>
                <p className="text-slate-500 font-medium mb-8">Where are we heading next?</p>
                <form onSubmit={handleCreateTrip} className="space-y-5">
                  <input
                    autoFocus
                    required
                    type="text"
                    placeholder="e.g. Summer in Santorini"
                    className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-lg font-bold focus:bg-white focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 outline-none transition-all"
                    value={newTripName}
                    onChange={(e) => setNewTripName(e.target.value)}
                  />
                  <div>
                    <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-2">
                      Start Date
                    </label>
                    <input
                      required
                      type="date"
                      className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-base font-bold text-slate-800 focus:bg-white focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 outline-none transition-all"
                      value={newTripStartDate}
                      onChange={(e) => setNewTripStartDate(e.target.value)}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isCreating || !newTripName.trim() || !newTripStartDate}
                    className="w-full py-5 bg-slate-900 text-white rounded-2xl font-black text-lg hover:bg-indigo-600 transition-all shadow-xl shadow-indigo-100 disabled:opacity-50 flex items-center justify-center gap-3"
                  >
                    {isCreating ? <Loader2 className="w-6 h-6 animate-spin" /> : 'Create Trip'}
                  </button>
                  {createError && (
                    <p className="text-rose-500 text-sm font-bold text-center">{createError}</p>
                  )}
                </form>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        {/* Persona onboarding modal — shown on first login when personas === null */}
        <AnimatePresence>
          {showPersonaModal && (
            <OnboardingPersonaModal
              onComplete={handlePersonaComplete}
              onSkip={handlePersonaSkip}
            />
          )}
        </AnimatePresence>

        {/* Skip toast */}
        <AnimatePresence>
          {showSkipToast && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 16 }}
              className="fixed bottom-6 right-6 z-50 bg-slate-800 text-white text-sm font-bold px-5 py-3 rounded-2xl shadow-xl flex items-center gap-2.5"
            >
              <Rocket className="w-4 h-4 text-indigo-400 shrink-0" />
              You can set your persona anytime — just tap Profile in the menu.
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </ProtectedRoute>
  );
}

function TripGrid({
  trips,
  isLoading,
  onNewTrip,
  onTripUpdate,
  emptyLabel,
  emptyMode = 'current',
}: {
  trips: any[];
  isLoading: boolean;
  onNewTrip: () => void;
  onTripUpdate?: () => void;
  emptyLabel?: string;
  emptyMode?: 'current' | 'past' | 'search';
}) {
  const router = useRouter();
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; name: string } | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [editingNameId, setEditingNameId] = useState<number | null>(null);
  const [editingNameVal, setEditingNameVal] = useState('');
  const [editingDateId, setEditingDateId] = useState<number | null>(null);
  const [editingDateVal, setEditingDateVal] = useState('');

  const handleOpenTrip = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>, tripId: number) => {
      if (typeof document !== 'undefined' && 'startViewTransition' in document) {
        e.preventDefault();
        (document as any).startViewTransition(() => router.push(`/trips/${tripId}`));
      }
    },
    [router]
  );

  const handleDeleteTrip = useCallback(async (tripId: number) => {
    setDeleteLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok || res.status === 204) {
        onTripUpdate?.();
      }
    } catch { /* ignore */ }
    finally {
      setDeleteLoading(false);
      setDeleteConfirm(null);
    }
  }, [onTripUpdate]);

  const handleSaveName = useCallback(async (tripId: number) => {
    if (!editingNameVal.trim()) { setEditingNameId(null); return; }
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: editingNameVal.trim() }),
      });
      if (res.ok) onTripUpdate?.();
    } catch { /* ignore */ }
    finally { setEditingNameId(null); }
  }, [editingNameVal, onTripUpdate]);

  const handleSaveDate = useCallback(async (tripId: number) => {
    if (!editingDateVal) { setEditingDateId(null); return; }
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ start_date: `${editingDateVal}T00:00:00` }),
      });
      if (res.ok) onTripUpdate?.();
    } catch { /* ignore */ }
    finally { setEditingDateId(null); }
  }, [editingDateVal, onTripUpdate]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {trips.map((trip: any) => {
          const isAdmin = trip.my_role === 'admin';

          return (
            <motion.div
              whileHover={{ y: -4 }}
              key={trip.id}
              className="relative bg-white rounded-[2rem] border border-slate-100 p-7 shadow-sm hover:shadow-xl hover:shadow-indigo-50/60 hover:border-indigo-100 transition-all group"
            >
              {/* Delete button — admin only */}
              {isAdmin && (
                <button
                  onClick={(e) => { e.stopPropagation(); setDeleteConfirm({ id: trip.id, name: trip.name }); }}
                  className="absolute top-4 right-4 p-2 text-slate-200 hover:text-rose-500 hover:bg-rose-50 rounded-xl transition-all opacity-0 group-hover:opacity-100 z-10"
                  title="Delete trip"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}

              <div className="text-5xl mb-5">🌍</div>

              {/* Name — editable by admin */}
              {editingNameId === trip.id ? (
                <div className="flex items-center gap-1.5 mb-1">
                  <input
                    autoFocus
                    type="text"
                    value={editingNameVal}
                    onChange={(e) => setEditingNameVal(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleSaveName(trip.id); if (e.key === 'Escape') setEditingNameId(null); }}
                    className="flex-1 text-lg font-black text-slate-900 bg-indigo-50 border border-indigo-200 rounded-lg px-2 py-0.5 outline-none focus:ring-2 focus:ring-indigo-400 min-w-0"
                  />
                  <button onClick={() => handleSaveName(trip.id)} className="p-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-colors">
                    <Check className="w-3 h-3" />
                  </button>
                  <button onClick={() => setEditingNameId(null)} className="p-1 text-slate-400 hover:text-slate-600 transition-colors">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 mb-1">
                  <h3 className="text-xl font-black text-slate-900 leading-tight group-hover:text-indigo-600 transition-colors truncate">
                    {trip.name}
                  </h3>
                  {isAdmin && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setEditingNameVal(trip.name); setEditingNameId(trip.id); }}
                      className="p-1 text-slate-200 hover:text-indigo-500 transition-colors opacity-0 group-hover:opacity-100 shrink-0"
                      title="Edit name"
                    >
                      <Pencil className="w-3 h-3" />
                    </button>
                  )}
                </div>
              )}

              {/* Date — editable by admin */}
              {editingDateId === trip.id ? (
                <div className="flex items-center gap-1.5 mb-7">
                  <Calendar className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                  <input
                    autoFocus
                    type="date"
                    value={editingDateVal}
                    onChange={(e) => setEditingDateVal(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleSaveDate(trip.id); if (e.key === 'Escape') setEditingDateId(null); }}
                    className="text-xs font-bold text-slate-700 bg-indigo-50 border border-indigo-200 rounded-lg px-2 py-0.5 outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                  <button onClick={() => handleSaveDate(trip.id)} className="p-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-colors">
                    <Check className="w-3 h-3" />
                  </button>
                  <button onClick={() => setEditingDateId(null)} className="p-1 text-slate-400 hover:text-slate-600 transition-colors">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-slate-400 text-xs font-bold mb-7">
                  <Calendar className="w-3.5 h-3.5" />
                  {trip.start_date ? new Date(trip.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Dates TBD'}
                  {isAdmin && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        const sd = trip.start_date ? new Date(trip.start_date).toISOString().split('T')[0] : '';
                        setEditingDateVal(sd);
                        setEditingDateId(trip.id);
                      }}
                      className="p-0.5 text-slate-200 hover:text-indigo-500 transition-colors opacity-0 group-hover:opacity-100"
                      title="Edit date"
                    >
                      <Pencil className="w-3 h-3" />
                    </button>
                  )}
                </div>
              )}

              <Link
                href={`/trips/${trip.id}`}
                onClick={(e) => handleOpenTrip(e, trip.id)}
                className="w-full flex items-center justify-between px-5 py-3.5 bg-slate-50 rounded-xl text-slate-800 font-black text-sm group-hover:bg-indigo-600 group-hover:text-white transition-all"
              >
                Open Trip
                <ChevronRight className="w-4 h-4" />
              </Link>
            </motion.div>
          );
        })}

        {trips.length === 0 && (
          <div className="col-span-full flex flex-col items-center justify-center py-24 text-center">
            {emptyLabel ? (
              <>
                <p className="text-slate-400 font-bold mb-4">{emptyLabel}</p>
                <button
                  onClick={onNewTrip}
                  className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-700 transition-all"
                >
                  Create a Trip
                </button>
              </>
            ) : emptyMode === 'past' ? (
              <>
                <div className="w-24 h-24 bg-rose-50 rounded-[2rem] flex items-center justify-center mb-6 relative">
                  <History className="w-12 h-12 text-rose-300" />
                  <span className="absolute -bottom-1 -right-1 text-2xl">🧳</span>
                </div>
                <h3 className="text-2xl font-black text-slate-900 mb-2">No stamps in the passport yet!</h3>
                <p className="text-slate-500 font-medium max-w-sm mb-1">
                  You haven&apos;t wrapped up any trips so far.
                </p>
                <p className="text-slate-400 text-sm font-medium max-w-sm">
                  Once a trip ends, it&apos;ll show up here as a memory.
                </p>
              </>
            ) : (
              <>
                <div className="w-24 h-24 bg-indigo-50 rounded-[2rem] flex items-center justify-center mb-6 relative">
                  <Rocket className="w-12 h-12 text-indigo-300" />
                  <span className="absolute -bottom-1 -right-1 text-2xl">✨</span>
                </div>
                <h3 className="text-2xl font-black text-slate-900 mb-2">The world is waiting!</h3>
                <p className="text-slate-500 font-medium max-w-sm mb-4">
                  No upcoming trips — your suitcase is collecting dust.
                </p>
                <button
                  onClick={onNewTrip}
                  className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100"
                >
                  Plan an Adventure
                </button>
              </>
            )}
          </div>
        )}

        {trips.length > 0 && (
          <button
            onClick={onNewTrip}
            className="border-2 border-dashed border-slate-200 rounded-[2rem] p-7 flex flex-col items-center justify-center gap-3 hover:bg-white hover:border-indigo-200 hover:shadow-lg transition-all group"
          >
            <div className="w-12 h-12 bg-slate-50 rounded-xl flex items-center justify-center group-hover:bg-indigo-50 transition-colors">
              <Plus className="w-6 h-6 text-slate-300 group-hover:text-indigo-500" />
            </div>
            <p className="text-sm font-black text-slate-400 group-hover:text-slate-700 transition-colors">Add New Trip</p>
          </button>
        )}
      </div>

      {/* Delete Trip Confirmation Dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-[400px] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 pt-6 pb-4 flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-rose-50 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5 text-rose-500" />
              </div>
              <div>
                <h3 className="text-base font-black text-slate-900">Delete &ldquo;{deleteConfirm.name}&rdquo;?</h3>
                <p className="text-sm text-slate-500 mt-1">
                  This will permanently delete the trip, all its itinerary, ideas, and remove all members. This cannot be undone.
                </p>
              </div>
            </div>
            <div className="px-6 pb-6 flex gap-2">
              <button
                onClick={() => handleDeleteTrip(deleteConfirm.id)}
                disabled={deleteLoading}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-rose-600 text-white rounded-xl text-sm font-black hover:bg-rose-500 transition-all disabled:opacity-50"
              >
                {deleteLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Delete Trip
              </button>
              <button
                onClick={() => setDeleteConfirm(null)}
                className="flex-1 px-4 py-3 bg-slate-100 text-slate-600 rounded-xl text-sm font-black hover:bg-slate-200 transition-all"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
