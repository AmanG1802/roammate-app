'use client';

import Link from 'next/link';
import Timeline from '@/components/trip/Timeline';
import IdeaBin from '@/components/trip/IdeaBin';
import GoogleMap from '@/components/map/GoogleMap';
import ConciergeActionBar from '@/components/trip/ConciergeActionBar';
import VibeCheck from '@/components/trip/VibeCheck';
import Collaborators from '@/components/layout/Collaborators';
import { Share2, Settings, LayoutGrid, Map as MapIcon, Calendar, User, ChevronLeft } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { ProtectedRoute } from '@/hooks/useAuth';

export default function TripPlannerPage() {
  const searchParams = useSearchParams();
  const tripId = searchParams.get('id');
  const [tripName, setTripName] = useState('New Adventure');

  useEffect(() => {
    if (tripId) {
      const fetchTrip = async () => {
        const token = localStorage.getItem('token');
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/trips/${tripId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setTripName(data.name);
        }
      };
      fetchTrip();
    }
  }, [tripId]);

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-white overflow-hidden relative">
        {/* Morning Concierge Overlay */}
        <VibeCheck />

        {/* Sidebar/Navigation (Fixed Mini) */}
        <aside className="w-20 bg-slate-900 flex flex-col items-center py-8 gap-10 shrink-0 z-30">
          <Link href="/dashboard" className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center font-black text-white text-2xl shadow-lg shadow-indigo-900/50 hover:scale-110 transition-transform">
            R
          </Link>
          
          <nav className="flex flex-col gap-6">
            <Link href="/dashboard" className="p-3 text-slate-500 hover:text-white transition-colors" title="Dashboard">
              <LayoutGrid className="w-6 h-6" />
            </Link>
            <button className="p-3 text-white bg-white/10 rounded-2xl" title="Active Trip">
              <MapIcon className="w-6 h-6" />
            </button>
            <button className="p-3 text-slate-500 hover:text-white transition-colors" title="Calendar">
              <Calendar className="w-6 h-6" />
            </button>
          </nav>

          <div className="mt-auto flex flex-col gap-6">
            <button className="p-3 text-slate-500 hover:text-white transition-colors">
              <Settings className="w-6 h-6" />
            </button>
            <div className="w-10 h-10 rounded-full bg-indigo-500 border-2 border-slate-800 flex items-center justify-center text-white font-bold text-xs">
              AG
            </div>
          </div>
        </aside>

        {/* Main Container */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <header className="h-20 border-b border-slate-100 flex items-center justify-between px-10 bg-white shrink-0">
            <div className="flex items-center gap-6">
              <Link href="/dashboard" className="p-2 hover:bg-slate-50 rounded-xl transition-colors">
                <ChevronLeft className="w-5 h-5 text-slate-400" />
              </Link>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-black text-slate-900 tracking-tight">{tripName}</h1>
                  <span className="px-3 py-1 bg-green-50 text-green-600 text-[10px] font-black uppercase tracking-[0.2em] rounded-full border border-green-100">Live Sync</span>
                </div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Travel Planning Active</p>
              </div>
            </div>
            
            <div className="flex items-center gap-8">
              <Collaborators />
              <div className="w-px h-8 bg-slate-100" />
              <div className="flex items-center gap-3">
                <button className="flex items-center gap-2 px-5 py-3 bg-slate-900 text-white rounded-2xl font-black text-sm hover:bg-indigo-600 transition-all shadow-xl shadow-slate-200">
                  <Share2 className="w-4 h-4" />
                  Invite
                </button>
              </div>
            </div>
          </header>

          {/* Main Content: 3-Pane View */}
          <div className="flex-1 flex overflow-hidden bg-slate-50">
            {/* Left: Timeline */}
            <div className="w-[480px] shrink-0 border-r border-slate-100 flex flex-col shadow-sm z-10 bg-white">
              <Timeline tripId={tripId} />
            </div>

            {/* Center: Map */}
            <div className="flex-1 relative">
              <GoogleMap />
              <ConciergeActionBar />
            </div>

            {/* Right: Idea Bin */}
            <div className="w-80 shrink-0 bg-white z-10">
              <IdeaBin tripId={tripId} />
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
