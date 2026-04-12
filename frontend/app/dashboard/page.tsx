'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Plus, Map, Calendar, Users, ChevronRight, Search, LayoutGrid, List, Loader2, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Navbar from '@/components/layout/Navbar';
import { ProtectedRoute } from '@/hooks/useAuth';

export default function DashboardPage() {
  const [trips, setTrips] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTripName, setNewTripName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetchTrips();
  }, []);

  const fetchTrips = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/trips/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setTrips(data);
      }
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
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/trips/`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
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

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-slate-50 overflow-hidden">
        {/* Sidebar Navigation */}
        <aside className="w-64 bg-white border-r border-slate-200 flex flex-col p-6 z-20">
          <div className="flex items-center gap-2 mb-12">
            <div className="w-8 h-8 bg-indigo-600 rounded-xl flex items-center justify-center font-bold text-white text-lg">R</div>
            <span className="text-xl font-black text-slate-900 tracking-tight">Roammate</span>
          </div>

          <nav className="flex-1 space-y-1">
            <Link href="/dashboard" className="flex items-center gap-3 px-4 py-3 bg-indigo-50 text-indigo-600 rounded-xl font-black text-sm">
              <LayoutGrid className="w-5 h-5" />
              Dashboard
            </Link>
            <button className="w-full flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-slate-600 rounded-xl font-black text-sm transition-colors">
              <Map className="w-5 h-5" />
              My Trips
            </button>
            <button className="w-full flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-slate-600 rounded-xl font-black text-sm transition-colors">
              <Users className="w-5 h-5" />
              Groups
            </button>
          </nav>

          <div className="mt-auto p-4 bg-slate-900 rounded-2xl text-white">
            <p className="text-xs font-black uppercase tracking-widest text-indigo-400 mb-2">Pro Plan</p>
            <p className="text-sm font-bold mb-4 italic">"The world is your oyster."</p>
            <button className="w-full py-2 bg-indigo-600 rounded-lg text-xs font-black hover:bg-indigo-700 transition-colors">Upgrade</button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col overflow-hidden relative">
          <header className="h-20 border-b border-slate-200 bg-white px-10 flex items-center justify-between shrink-0">
            <div className="relative w-96">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search trips, locations..." 
                className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-100 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
              />
            </div>
            
            <div className="flex items-center gap-4">
              <button 
                onClick={() => setIsModalOpen(true)}
                className="w-10 h-10 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 hover:bg-slate-200 transition-colors"
              >
                <Plus className="w-5 h-5" />
              </button>
              <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-black">AG</div>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto p-10">
            <div className="flex items-center justify-between mb-10">
              <div>
                <h2 className="text-4xl font-black text-slate-900 mb-1">Your Adventures.</h2>
                <p className="text-slate-500 font-medium">You have {trips.length} active trips.</p>
              </div>
              <button 
                onClick={() => setIsModalOpen(true)}
                className="px-6 py-4 bg-indigo-600 text-white rounded-2xl font-black flex items-center gap-3 hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-100"
              >
                <Plus className="w-5 h-5" />
                Plan New Trip
              </button>
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {trips.map((trip) => (
                  <motion.div 
                    whileHover={{ y: -5 }}
                    key={trip.id} 
                    className="bg-white rounded-[2.5rem] border border-slate-100 p-8 shadow-sm hover:shadow-2xl hover:shadow-indigo-50 hover:border-indigo-100 transition-all group"
                  >
                    <div className="text-6xl mb-6">🌍</div>
                    <h3 className="text-2xl font-black text-slate-900 mb-2 leading-tight group-hover:text-indigo-600 transition-colors">{trip.name}</h3>
                    
                    <div className="flex flex-col gap-3 mb-8">
                      <div className="flex items-center gap-2 text-slate-400 text-sm font-bold">
                        <Calendar className="w-4 h-4" />
                        {trip.start_date ? new Date(trip.start_date).toLocaleDateString() : 'TBD'}
                      </div>
                    </div>

                    <Link 
                      href={`/trips?id=${trip.id}`}
                      className="w-full flex items-center justify-between px-6 py-4 bg-slate-50 rounded-2xl text-slate-900 font-black text-sm group-hover:bg-indigo-600 group-hover:text-white transition-all"
                    >
                      Open Itinerary
                      <ChevronRight className="w-5 h-5" />
                    </Link>
                  </motion.div>
                ))}

                <button 
                  onClick={() => setIsModalOpen(true)}
                  className="border-2 border-dashed border-slate-200 rounded-[2.5rem] p-8 flex flex-col items-center justify-center gap-4 hover:bg-white hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-50 transition-all group"
                >
                  <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center group-hover:bg-indigo-50 transition-colors">
                    <Plus className="w-8 h-8 text-slate-300 group-hover:text-indigo-500" />
                  </div>
                  <p className="text-lg font-black text-slate-400 group-hover:text-slate-900 transition-colors">Add New Trip</p>
                </button>
              </div>
            )}
          </div>

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
                    className="absolute top-6 right-6 p-2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>

                  <h3 className="text-3xl font-black text-slate-900 mb-2">New Adventure.</h3>
                  <p className="text-slate-500 font-medium mb-8">Where are we heading next?</p>

                  <form onSubmit={handleCreateTrip} className="space-y-6">
                    <div>
                      <label className="block text-xs font-black uppercase tracking-widest text-slate-400 mb-2 ml-1">Trip Name</label>
                      <input 
                        autoFocus
                        required
                        type="text" 
                        placeholder="e.g. Summer in Santorini"
                        className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-lg font-bold focus:bg-white focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 outline-none transition-all"
                        value={newTripName}
                        onChange={(e) => setNewTripName(e.target.value)}
                      />
                    </div>

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
        </main>
      </div>
    </ProtectedRoute>
  );
}
