'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, Sparkles, Calendar, MapPin, Plane, Compass, Globe,
  Plus, X, Loader2, ChevronRight, Users, Clock, Pencil, Check,
  ShieldCheck, Eye, Vote, ChevronDown,
} from 'lucide-react';
import { gsap } from 'gsap';
import { format, differenceInDays, parseISO } from 'date-fns';
import useAuth, { ProtectedRoute } from '@/hooks/useAuth';

const ROLE_ICON_MAP: Record<string, { icon: typeof ShieldCheck; bg: string; fg: string }> = {
  admin: { icon: ShieldCheck, bg: 'bg-amber-400', fg: 'text-amber-900' },
  view_only: { icon: Eye, bg: 'bg-sky-400', fg: 'text-sky-900' },
  view_with_vote: { icon: Vote, bg: 'bg-violet-400', fg: 'text-violet-900' },
};

function getInitials(name: string) {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

const AVATAR_PALETTE = [
  '#6366f1', '#8b5cf6', '#ec4899', '#14b8a6', '#f59e0b', '#10b981',
];

// ── Trip Hub ──────────────────────────────────────────────────────────────────

function TripHubContent() {
  const params = useParams();
  const router = useRouter();
  const tripId = params.id as string;
  const { user: currentUser } = useAuth(true);

  const containerRef = useRef<HTMLDivElement>(null);
  const [trip, setTrip] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('');
  const [inviteStatus, setInviteStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [inviteError, setInviteError] = useState('');
  

  const ROLE_OPTIONS = [
    { value: 'admin', label: 'Admin' },
    { value: 'view_only', label: 'View Only' },
    { value: 'view_with_vote', label: 'View with Vote' },
  ];

  const [editingDate, setEditingDate] = useState(false);
  const [dateValue, setDateValue] = useState('');

  const isAdmin = currentUser
    ? members.some((m) => m.user_id === currentUser.id && m.role === 'admin')
    : false;

  // ── Fetch trip + members ────────────────────────────────────────────────────
  useEffect(() => {
    if (!tripId) return;
    const token = localStorage.getItem('token');
    if (!token) { router.push('/login'); return; }

    const fetchData = async () => {
      try {
        const [tripRes, membersRes] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/members`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        if (tripRes.status === 403 || tripRes.status === 404) {
          setNotFound(true);
          return;
        }
        if (tripRes.ok) setTrip(await tripRes.json());
        if (membersRes.ok) setMembers(await membersRes.json());
      } catch {
        // silently fail — data stays null
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [tripId, router]);

  // ── GSAP cinematic entry ────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || isLoading) return;

    const ctx = gsap.context(() => {
      // Initial hidden states
      gsap.set(['.hub-badge', '.hub-word', '.hub-date-pill', '.hub-divider',
                 '.hub-avatar', '.hub-invite-btn', '.hub-cta', '.hub-float-icon'], {
        opacity: 0,
      });
      gsap.set('.hub-word',       { y: 70, rotateX: 18 });
      gsap.set('.hub-badge',      { y: -16 });
      gsap.set('.hub-date-pill',  { y: 16 });
      gsap.set('.hub-divider',    { scaleX: 0, transformOrigin: 'left center' });
      gsap.set('.hub-avatar',     { scale: 0, y: 8 });
      gsap.set('.hub-invite-btn', { scale: 0.7 });
      gsap.set('.hub-cta',        { y: 24 });

      const tl = gsap.timeline({ delay: 0.05 });

      // Floating icons drift in
      tl.to('.hub-float-icon', {
        opacity: 0.15, duration: 1.2, stagger: 0.12, ease: 'power2.out',
      }, 0);

      // Badge
      tl.to('.hub-badge', {
        opacity: 1, y: 0, duration: 0.5, ease: 'power3.out',
      }, 0.1);

      // Trip name — each word flips up with perspective
      tl.to('.hub-word', {
        opacity: 1, y: 0, rotateX: 0,
        duration: 0.85, stagger: 0.11, ease: 'expo.out',
      }, 0.25);

      // Date pills
      tl.to('.hub-date-pill', {
        opacity: 1, y: 0, duration: 0.5, stagger: 0.08, ease: 'power3.out',
      }, 0.6);

      // Divider lines expand left → right
      tl.to('.hub-divider', {
        opacity: 1, scaleX: 1, duration: 0.5, stagger: 0.1, ease: 'power2.inOut',
      }, 0.75);

      // Avatars pop in with elastic overshoot
      tl.to('.hub-avatar', {
        opacity: 1, scale: 1, y: 0,
        duration: 0.55, stagger: 0.09, ease: 'back.out(2.2)',
      }, 0.85);

      // Invite + add button
      tl.to('.hub-invite-btn', {
        opacity: 1, scale: 1, duration: 0.4, ease: 'back.out(2)',
      }, 1.1);

      // CTA buttons rise from below
      tl.to('.hub-cta', {
        opacity: 1, y: 0, duration: 0.55, stagger: 0.1, ease: 'expo.out',
      }, 1.1);

      // Persistent float loops (start after entry)
      gsap.to('.hub-float-1', {
        y: -20, x: 10, rotation: 14, duration: 5.5,
        repeat: -1, yoyo: true, ease: 'sine.inOut', delay: 1.5,
      });
      gsap.to('.hub-float-2', {
        y: 16, x: -12, rotation: -10, duration: 7,
        repeat: -1, yoyo: true, ease: 'sine.inOut', delay: 1.5,
      });
      gsap.to('.hub-float-3', {
        y: -14, x: 8, rotation: 8, duration: 6.2,
        repeat: -1, yoyo: true, ease: 'sine.inOut', delay: 1.5,
      });
      gsap.to('.hub-float-4', {
        y: 12, x: -8, rotation: -12, duration: 4.8,
        repeat: -1, yoyo: true, ease: 'sine.inOut', delay: 1.5,
      });
    }, containerRef);

    return () => ctx.revert();
  }, [isLoading]);

  // ── Invite handler ──────────────────────────────────────────────────────────
  const handleInvite = async () => {
    if (!inviteEmail.trim() || !inviteRole) return;
    setInviteStatus('loading');
    setInviteError('');
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/invite`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
        }
      );
      if (res.ok) {
        const newMember = await res.json();
        setMembers((prev) => [...prev, newMember]);
        setInviteEmail('');
        setInviteRole('');
        setInviteStatus('success');
        setTimeout(() => { setInviteStatus('idle'); setShowInvite(false); }, 2000);
      } else {
        const err = await res.json();
        setInviteError(err.detail ?? 'Could not invite user');
        setInviteStatus('error');
      }
    } catch {
      setInviteError('Network error — please try again');
      setInviteStatus('error');
    }
  };

  // ── Save start date ────────────────────────────────────────────────────────
  const handleSaveDate = async () => {
    if (!dateValue) return;
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ start_date: `${dateValue}T00:00:00` }),
        }
      );
      if (res.ok) {
        const updated = await res.json();
        setTrip(updated);
      }
    } catch {
      // silently fail
    }
    setEditingDate(false);
  };

  // ── View-Transition navigation ──────────────────────────────────────────────
  const navigate = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (typeof document !== 'undefined' && 'startViewTransition' in document) {
      e.preventDefault();
      (document as any).startViewTransition(() => router.push(href));
    }
  };

  // ── Loading skeleton ────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="h-screen bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-5">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
              <Compass className="w-8 h-8 text-indigo-400 animate-spin" style={{ animationDuration: '2s' }} />
            </div>
            <div className="absolute inset-0 rounded-2xl bg-indigo-500/10 blur-xl animate-pulse" />
          </div>
          <p className="text-slate-500 text-xs font-black uppercase tracking-[0.3em]">Loading Trip</p>
        </div>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="h-screen bg-slate-950 flex flex-col items-center justify-center gap-6">
        <p className="text-slate-400 text-lg font-black">Trip not found.</p>
        <Link href="/dashboard" className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-500 transition-colors">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const nameWords: string[] = (trip?.name ?? 'Your Trip').split(' ');

  const parsedStart = trip?.start_date ? parseISO(trip.start_date) : null;
  const parsedEnd = trip?.end_date ? parseISO(trip.end_date) : null;

  const dateRange =
    parsedStart && parsedEnd
      ? `${format(parsedStart, 'MMM d')} → ${format(parsedEnd, 'MMM d, yyyy')}`
      : parsedStart
      ? `From ${format(parsedStart, 'MMM d, yyyy')}`
      : 'Dates TBD';

  const duration =
    parsedStart && parsedEnd
      ? `${differenceInDays(parsedEnd, parsedStart) + 1} days`
      : null;

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div ref={containerRef} className="relative h-screen bg-slate-950 overflow-hidden flex flex-col">

      {/* depth-0: atmospheric glow blobs */}
      <div className="absolute inset-0 pointer-events-none z-0" aria-hidden="true">
        <div className="absolute -top-[20%] -left-[10%] w-[70vw] h-[70vw] bg-indigo-600/10 rounded-full blur-[200px]" />
        <div className="absolute -bottom-[20%] -right-[10%] w-[60vw] h-[60vw] bg-violet-600/10 rounded-full blur-[180px]" />
        <div className="absolute top-[35%] right-[25%] w-[25vw] h-[25vw] bg-indigo-400/5 rounded-full blur-[100px]" />
      </div>

      {/* depth-2: floating travel icons */}
      <div className="absolute inset-0 pointer-events-none z-10" aria-hidden="true">
        <Plane
          className="hub-float-icon hub-float-1 absolute text-indigo-400/30 w-20 h-20"
          style={{ top: '14%', left: '7%', transform: 'rotate(38deg)' }}
        />
        <Compass
          className="hub-float-icon hub-float-2 absolute text-violet-400/20 w-28 h-28"
          style={{ bottom: '18%', left: '4%' }}
        />
        <Globe
          className="hub-float-icon hub-float-3 absolute text-indigo-300/15 w-36 h-36"
          style={{ top: '8%', right: '5%' }}
        />
        <MapPin
          className="hub-float-icon hub-float-4 absolute text-rose-400/20 w-14 h-14"
          style={{ bottom: '28%', right: '8%' }}
        />
      </div>

      {/* Nav */}
      <nav className="relative z-30 flex items-center justify-between px-8 pt-7 pb-3 shrink-0">
        <Link
          href="/dashboard"
          className="flex items-center gap-2.5 text-slate-500 hover:text-white transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
          <span className="text-xs font-black uppercase tracking-[0.25em]">All Trips</span>
        </Link>
        <Link href="/" className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center font-black text-white text-lg shadow-lg shadow-indigo-900/60 hover:scale-105 transition-transform">
          R
        </Link>
      </nav>

      {/* Main two-column layout */}
      <main className="relative z-20 flex-1 flex flex-col lg:flex-row items-center justify-center px-8 lg:px-16 xl:px-24 gap-12 lg:gap-20 overflow-hidden pb-6">

        {/* ── LEFT: Trip Identity ────────────────────────────────────────── */}
        <div className="flex-1 max-w-2xl flex flex-col justify-center min-w-0" style={{ perspective: '1200px' }}>

          <div className="hub-badge inline-flex items-center gap-2 px-4 py-2 bg-indigo-500/10 border border-indigo-500/25 text-indigo-400 rounded-full text-[9px] font-black uppercase tracking-[0.35em] mb-7 w-fit">
            <Sparkles className="w-3 h-3" />
            Trip Overview
          </div>

          <h1
            className="font-black text-white tracking-tighter leading-[0.88] mb-8 break-words"
            style={{ fontSize: 'clamp(3rem, 7vw, 7.5rem)' }}
          >
            {nameWords.map((word, i) => (
              <span key={i} className="hub-word inline-block mr-[0.12em] last:mr-0">
                {i === nameWords.length - 1 ? (
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-violet-400">
                    {word}
                  </span>
                ) : (
                  word
                )}
              </span>
            ))}
          </h1>

          <div className="flex items-center gap-3 flex-wrap">
            {isAdmin && editingDate ? (
              <div className="hub-date-pill flex items-center gap-2 px-3 py-1.5 bg-white/10 border border-indigo-500/40 rounded-2xl backdrop-blur-sm">
                <Calendar className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                <input
                  autoFocus
                  type="date"
                  value={dateValue}
                  onChange={(e) => setDateValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSaveDate()}
                  className="bg-transparent text-white font-bold text-sm outline-none border-none w-40"
                />
                <button
                  onClick={handleSaveDate}
                  className="p-1 bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors"
                >
                  <Check className="w-3 h-3 text-white" />
                </button>
                <button
                  onClick={() => setEditingDate(false)}
                  className="p-1 text-slate-400 hover:text-white transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ) : (
              <div className="hub-date-pill flex items-center gap-2 px-4 py-2.5 bg-white/5 border border-white/8 rounded-2xl backdrop-blur-sm group">
                <Calendar className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                <span className="text-white/90 font-bold text-sm">{dateRange}</span>
                {isAdmin && (
                  <button
                    onClick={() => {
                      const sd = trip?.start_date ? trip.start_date.split('T')[0] : '';
                      setDateValue(sd);
                      setEditingDate(true);
                    }}
                    className="p-1 text-white/30 hover:text-indigo-400 transition-colors"
                    title="Edit start date"
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                )}
              </div>
            )}
            {duration && !editingDate && (
              <div className="hub-date-pill flex items-center gap-2 px-4 py-2.5 bg-white/5 border border-white/8 rounded-2xl backdrop-blur-sm">
                <Clock className="w-3.5 h-3.5 text-violet-400 shrink-0" />
                <span className="text-slate-300 font-bold text-sm">{duration}</span>
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT: Social + Actions ────────────────────────────────────── */}
        <div className="w-full lg:w-[360px] xl:w-[400px] flex flex-col gap-5 shrink-0">

          {/* Divider */}
          <div className="hub-divider h-px bg-gradient-to-r from-white/15 via-white/5 to-transparent" />

          {/* Travelers */}
          <div>
            <div className="flex items-center gap-2 text-slate-500 mb-4">
              <Users className="w-3.5 h-3.5" />
              <span className="text-[10px] font-black uppercase tracking-widest">
                {members.length} {members.length === 1 ? 'Traveler' : 'Travelers'}
              </span>
            </div>

            <div className="flex items-center gap-3 flex-wrap">
              {members.map((member, i) => {
                const roleCfg = ROLE_ICON_MAP[member.role] ?? ROLE_ICON_MAP.view_only;
                const RIcon = roleCfg.icon;
                const isSelf = currentUser && member.user_id === currentUser.id;
                return (
                  <div key={member.id} className="hub-avatar group relative">
                    <div
                      className="w-11 h-11 rounded-full border-2 border-slate-800 flex items-center justify-center font-black text-sm text-white shadow-lg cursor-default transition-all hover:scale-110 hover:border-indigo-400 hover:shadow-indigo-900/40"
                      style={{ backgroundColor: AVATAR_PALETTE[i % AVATAR_PALETTE.length] }}
                    >
                      {getInitials(member.user?.name ?? '?')}
                    </div>
                    <div className={`absolute -top-1 -right-1 w-4 h-4 ${roleCfg.bg} rounded-full flex items-center justify-center shadow-sm`}>
                      <RIcon className={`w-2.5 h-2.5 ${roleCfg.fg}`} />
                    </div>
                    <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 hidden group-hover:flex flex-col items-center bg-slate-800/95 text-white text-[10px] py-1.5 px-2.5 rounded-xl font-bold whitespace-nowrap z-50 border border-white/10 shadow-xl">
                      <span>
                        {member.user?.name}
                        <span className="text-slate-400 ml-1.5 font-normal">({member.role?.replace('_', ' ')})</span>
                      </span>
                    </div>
                  </div>
                );
              })}

              {isAdmin && (
                <button
                  onClick={() => { setShowInvite(!showInvite); setInviteError(''); setInviteEmail(''); }}
                  className="hub-invite-btn w-11 h-11 rounded-full border-2 border-dashed border-indigo-500/35 flex items-center justify-center text-indigo-500 hover:border-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 transition-all"
                  title="Add traveler"
                >
                  {showInvite ? <X className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />}
                </button>
              )}
            </div>

            {/* Invite form — admin only */}
            {isAdmin && showInvite && (
              <div className="mt-4 space-y-2">
                <div className="flex gap-2">
                  <input
                    autoFocus
                    type="email"
                    placeholder="traveler@email.com"
                    value={inviteEmail}
                    onChange={(e) => {
                      setInviteEmail(e.target.value);
                      setInviteStatus('idle');
                      setInviteError('');
                    }}
                    onKeyDown={(e) => e.key === 'Enter' && handleInvite()}
                    className="flex-1 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white text-sm font-medium placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 transition-all"
                  />
                  <div className="relative w-[150px] shrink-0">
                    <select
                      value={inviteRole}
                      onChange={(e) => setInviteRole(e.target.value)}
                      className={`w-full appearance-none pl-3 pr-8 py-2.5 border border-white/10 rounded-xl text-sm font-bold focus:outline-none focus:border-indigo-500/60 cursor-pointer transition-all ${
                        inviteRole ? 'bg-white/10 text-white' : 'bg-white/5 text-slate-500'
                      }`}
                    >
                      <option value="" disabled>Add role</option>
                      {ROLE_OPTIONS.map((r) => (
                        <option key={r.value} value={r.value}>{r.label}</option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
                  </div>
                  <button
                    onClick={handleInvite}
                    disabled={inviteStatus === 'loading' || !inviteEmail.trim() || !inviteRole}
                    className="px-4 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-black hover:bg-indigo-500 transition-all disabled:opacity-50 min-w-[80px] flex items-center justify-center gap-2"
                  >
                    {inviteStatus === 'loading' ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : inviteStatus === 'success' ? (
                      '✓ Added!'
                    ) : (
                      'Invite'
                    )}
                  </button>
                </div>
                {inviteError && (
                  <p className="text-rose-400 text-xs font-bold px-1">{inviteError}</p>
                )}
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="hub-divider h-px bg-gradient-to-r from-white/15 via-white/5 to-transparent" />

          {/* CTA buttons */}
          <div className="flex flex-col gap-3">
            <Link
              href={`/trips?id=${tripId}`}
              onClick={(e) => navigate(e, `/trips?id=${tripId}`)}
              className="hub-cta group flex items-center justify-between px-6 py-4 bg-white text-slate-900 rounded-2xl font-black text-[15px] hover:bg-indigo-50 transition-all shadow-2xl shadow-black/30"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-indigo-100 rounded-xl flex items-center justify-center group-hover:bg-indigo-200 transition-colors">
                  <MapPin className="w-4 h-4 text-indigo-600" />
                </div>
                Open Planner
              </div>
              <ChevronRight className="w-5 h-5 text-slate-400 group-hover:translate-x-0.5 group-hover:text-indigo-600 transition-all" />
            </Link>

            <Link
              href={`/trips?id=${tripId}&mode=concierge`}
              onClick={(e) => navigate(e, `/trips?id=${tripId}&mode=concierge`)}
              className="hub-cta group flex items-center justify-between px-6 py-4 bg-indigo-600/15 border border-indigo-500/25 text-indigo-300 rounded-2xl font-black text-[15px] hover:bg-indigo-600/25 hover:border-indigo-400/40 transition-all"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-indigo-500/20 rounded-xl flex items-center justify-center group-hover:bg-indigo-500/30 transition-colors">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                </div>
                Live Concierge
              </div>
              <ChevronRight className="w-5 h-5 text-indigo-600/50 group-hover:translate-x-0.5 group-hover:text-indigo-400 transition-all" />
            </Link>

            <Link
              href={`/trips?id=${tripId}&mode=people`}
              onClick={(e) => navigate(e, `/trips?id=${tripId}&mode=people`)}
              className="hub-cta group flex items-center justify-between px-6 py-4 bg-white/5 border border-white/10 text-slate-400 rounded-2xl font-black text-[15px] hover:bg-white/10 hover:border-white/20 hover:text-slate-300 transition-all"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-white/10 rounded-xl flex items-center justify-center group-hover:bg-white/15 transition-colors">
                  <Users className="w-4 h-4 text-slate-400 group-hover:text-slate-300" />
                </div>
                People
              </div>
              <ChevronRight className="w-5 h-5 text-white/20 group-hover:translate-x-0.5 group-hover:text-slate-400 transition-all" />
            </Link>
          </div>
        </div>
      </main>

      {/* Bottom strip */}
      <div className="relative z-30 px-9 py-3 shrink-0 flex items-center justify-between">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-slate-800">
          Trip #{tripId}
          {trip?.created_at ? ` · Created ${format(new Date(trip.created_at), 'MMM d, yyyy')}` : ''}
        </p>
      </div>

      {/* View Transition + Accessibility CSS */}
      <style jsx global>{`
        @keyframes vt-exit-scale {
          to {
            opacity: 0;
            transform: scale(1.05) translateY(-6px);
            filter: blur(6px);
          }
        }
        @keyframes vt-enter-scale {
          from {
            opacity: 0;
            transform: scale(0.96) translateY(18px);
          }
        }
        @media (prefers-reduced-motion: no-preference) {
          ::view-transition-old(root) {
            animation: 280ms ease-in both vt-exit-scale;
          }
          ::view-transition-new(root) {
            animation: 480ms cubic-bezier(0, 0, 0.2, 1) both vt-enter-scale;
          }
        }
        @media (prefers-reduced-motion: reduce) {
          ::view-transition-old(root),
          ::view-transition-new(root) {
            animation: none !important;
          }
        }
      `}</style>
    </div>
  );
}

export default function TripHubPage() {
  return (
    <ProtectedRoute>
      <TripHubContent />
    </ProtectedRoute>
  );
}
