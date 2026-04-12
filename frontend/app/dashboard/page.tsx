'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { Plus, Map, Calendar, Users, ChevronRight, Search, LayoutGrid, Loader2, X, LogOut } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import useAuth, { ProtectedRoute } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';

type Section = 'dashboard' | 'trips' | 'groups';

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
  const [isCreating, setIsCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    router.push('/');
  };

  useEffect(() => {
    fetchTrips();
  }, []);

  const fetchTrips = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) setTrips(await response.json());
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateTrip = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: newTripName }),
      });
      if (response.ok) {
        setNewTripName('');
        setIsModalOpen(false);
        fetchTrips();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsCreating(false);
    }
  };

  const filteredTrips = useMemo(() => {
    if (!searchQuery.trim()) return trips;
    const q = searchQuery.toLowerCase();
    return trips.filter((t) => t.name.toLowerCase().includes(q));
  }, [trips, searchQuery]);

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
              {navItem('groups', <Users className="w-5 h-5" />, 'Groups')}
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[9px] font-black uppercase tracking-widest text-slate-300 bg-slate-50 px-2 py-0.5 rounded-full border border-slate-100">
                Soon
              </span>
            </div>
          </nav>

          {/* User info at the bottom */}
          <div className="mt-auto pt-4 border-t border-slate-100 flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center text-white font-black text-xs shrink-0">
              {user?.name ? getInitials(user.name) : '?'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-black text-slate-800 truncate">{user?.name ?? '—'}</p>
              <p className="text-[10px] font-bold text-slate-400 truncate">{user?.email ?? ''}</p>
            </div>
            <button
              onClick={handleLogout}
              title="Log out"
              className="p-1.5 text-slate-300 hover:text-rose-500 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
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
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100"
            >
              <Plus className="w-4 h-4" />
              New Trip
            </button>
          </header>

          <div className="flex-1 overflow-y-auto p-8">
            {/* Dashboard overview */}
            {section === 'dashboard' && (
              <>
                <div className="mb-8">
                  <h2 className="text-3xl font-black text-slate-900 mb-1">
                    {user?.name ? `Hey, ${user.name.split(' ')[0]}.` : 'Your Adventures.'}
                  </h2>
                  <p className="text-slate-500 font-medium">
                    {trips.length === 0 ? "No trips yet — create your first one." : `You have ${trips.length} ${trips.length === 1 ? 'trip' : 'trips'} planned.`}
                  </p>
                </div>
                <TripGrid
                  trips={trips.slice(0, 6)}
                  isLoading={isLoading}
                  onNewTrip={() => setIsModalOpen(true)}
                />
              </>
            )}

            {/* My Trips full list + search results */}
            {(section === 'trips' || searchQuery) && (
              <>
                <div className="mb-8">
                  <h2 className="text-3xl font-black text-slate-900 mb-1">
                    {searchQuery ? `Results for "${searchQuery}"` : 'My Trips'}
                  </h2>
                  <p className="text-slate-500 font-medium">
                    {filteredTrips.length} {filteredTrips.length === 1 ? 'trip' : 'trips'} found.
                  </p>
                </div>
                <TripGrid
                  trips={filteredTrips}
                  isLoading={isLoading}
                  onNewTrip={() => setIsModalOpen(true)}
                  emptyLabel={searchQuery ? 'No trips match your search.' : "You haven't created any trips yet."}
                />
              </>
            )}

            {/* Groups placeholder */}
            {section === 'groups' && !searchQuery && (
              <div className="flex flex-col items-center justify-center py-32 text-center">
                <div className="w-20 h-20 bg-slate-100 rounded-[2rem] flex items-center justify-center mb-6">
                  <Users className="w-10 h-10 text-slate-300" />
                </div>
                <h3 className="text-2xl font-black text-slate-900 mb-2">Groups are coming soon.</h3>
                <p className="text-slate-500 font-medium max-w-sm">
                  Collaborative trip planning for families and friend groups is on the roadmap.
                </p>
              </div>
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
                <form onSubmit={handleCreateTrip} className="space-y-6">
                  <input
                    autoFocus
                    required
                    type="text"
                    placeholder="e.g. Summer in Santorini"
                    className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-lg font-bold focus:bg-white focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 outline-none transition-all"
                    value={newTripName}
                    onChange={(e) => setNewTripName(e.target.value)}
                  />
                  <button
                    disabled={isCreating}
                    className="w-full py-5 bg-slate-900 text-white rounded-2xl font-black text-lg hover:bg-indigo-600 transition-all shadow-xl shadow-indigo-100 disabled:opacity-50 flex items-center justify-center gap-3"
                  >
                    {isCreating ? <Loader2 className="w-6 h-6 animate-spin" /> : 'Create Trip'}
                  </button>
                </form>
              </motion.div>
            </div>
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
  emptyLabel = "No trips yet — create your first one.",
}: {
  trips: any[];
  isLoading: boolean;
  onNewTrip: () => void;
  emptyLabel?: string;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {trips.map((trip) => (
        <motion.div
          whileHover={{ y: -4 }}
          key={trip.id}
          className="bg-white rounded-[2rem] border border-slate-100 p-7 shadow-sm hover:shadow-xl hover:shadow-indigo-50/60 hover:border-indigo-100 transition-all group"
        >
          <div className="text-5xl mb-5">🌍</div>
          <h3 className="text-xl font-black text-slate-900 mb-1 leading-tight group-hover:text-indigo-600 transition-colors">
            {trip.name}
          </h3>
          <div className="flex items-center gap-2 text-slate-400 text-xs font-bold mb-7">
            <Calendar className="w-3.5 h-3.5" />
            {trip.start_date ? new Date(trip.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Dates TBD'}
          </div>
          <Link
            href={`/trips?id=${trip.id}`}
            className="w-full flex items-center justify-between px-5 py-3.5 bg-slate-50 rounded-xl text-slate-800 font-black text-sm group-hover:bg-indigo-600 group-hover:text-white transition-all"
          >
            Open Itinerary
            <ChevronRight className="w-4 h-4" />
          </Link>
        </motion.div>
      ))}

      {trips.length === 0 && (
        <div className="col-span-full flex flex-col items-center justify-center py-20 text-center">
          <p className="text-slate-400 font-bold mb-4">{emptyLabel}</p>
          <button
            onClick={onNewTrip}
            className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-700 transition-all"
          >
            Create a Trip
          </button>
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
  );
}
