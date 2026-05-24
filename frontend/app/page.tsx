'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  Sparkles, Map as MapIcon, Clock, Wand2, MessageSquare,
  Layers, Check, ArrowRight, ChevronDown, Coffee, Bell,
  ThumbsUp, ThumbsDown, ChevronLeft, ChevronRight, MapPin, GripVertical,
  Pencil, User as UserIcon, Infinity as InfinityIcon, Compass, MapPinned,
} from 'lucide-react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { motion, useScroll, useTransform } from 'framer-motion';
import Navbar from '@/components/layout/Navbar';

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

// ── Plan Mode mockup ────────────────────────────────────────────────────────

type PlanEvent = {
  time: string;
  endTime: string;
  title: string;
  cat: string;
  catTint: string;
  accent: string;
  dot: string;
};
type PlanPin = { cx: number; cy: number; color: string; n: number };
type PlanDay = {
  id: 'd1' | 'd2' | 'd3';
  label: string;
  weekday: string;
  date: string;
  events: PlanEvent[];
  routeD: string;
  pins: PlanPin[];
};

const PLAN_DAYS: PlanDay[] = [
  {
    id: 'd1', label: 'Day 1', weekday: 'Thu', date: 'May 21',
    events: [
      { time: '09:00 AM', endTime: '10:30 AM', title: 'Pastéis de Belém', cat: 'Food', catTint: 'bg-amber-50 text-amber-700 border-amber-200', accent: 'bg-amber-400', dot: '#f59e0b' },
      { time: '11:30 AM', endTime: '01:00 PM', title: 'Jerónimos Monastery', cat: 'Landmarks & Viewpoints', catTint: 'bg-yellow-50 text-yellow-700 border-yellow-200', accent: 'bg-yellow-400', dot: '#eab308' },
      { time: '02:30 PM', endTime: '04:30 PM', title: 'LX Factory', cat: 'Culture', catTint: 'bg-violet-50 text-violet-700 border-violet-200', accent: 'bg-violet-400', dot: '#8b5cf6' },
    ],
    routeD: 'M18 82 Q 35 70, 50 55 T 84 22',
    pins: [
      { cx: 18, cy: 82, color: '#f59e0b', n: 1 },
      { cx: 50, cy: 55, color: '#eab308', n: 2 },
      { cx: 84, cy: 22, color: '#8b5cf6', n: 3 },
    ],
  },
  {
    id: 'd2', label: 'Day 2', weekday: 'Fri', date: 'May 22',
    events: [
      { time: '10:00 AM', endTime: '12:00 PM', title: 'São Jorge Castle', cat: 'Landmarks & Viewpoints', catTint: 'bg-yellow-50 text-yellow-700 border-yellow-200', accent: 'bg-yellow-400', dot: '#eab308' },
      { time: '01:00 PM', endTime: '02:30 PM', title: 'Time Out Market', cat: 'Food', catTint: 'bg-amber-50 text-amber-700 border-amber-200', accent: 'bg-amber-400', dot: '#f59e0b' },
      { time: '04:00 PM', endTime: '06:00 PM', title: 'LX Factory', cat: 'Culture', catTint: 'bg-violet-50 text-violet-700 border-violet-200', accent: 'bg-violet-400', dot: '#8b5cf6' },
    ],
    routeD: 'M22 28 Q 40 40, 55 50 Q 70 60, 78 78',
    pins: [
      { cx: 22, cy: 28, color: '#eab308', n: 1 },
      { cx: 50, cy: 48, color: '#f59e0b', n: 2 },
      { cx: 78, cy: 78, color: '#8b5cf6', n: 3 },
    ],
  },
  {
    id: 'd3', label: 'Day 3', weekday: 'Sat', date: 'May 23',
    events: [
      { time: '10:00 AM', endTime: '12:00 PM', title: 'Pena Palace', cat: 'Landmarks & Viewpoints', catTint: 'bg-yellow-50 text-yellow-700 border-yellow-200', accent: 'bg-yellow-400', dot: '#eab308' },
      { time: '01:00 PM', endTime: '02:30 PM', title: 'Café Saudade', cat: 'Food', catTint: 'bg-amber-50 text-amber-700 border-amber-200', accent: 'bg-amber-400', dot: '#f59e0b' },
      { time: '03:00 PM', endTime: '05:00 PM', title: 'Quinta da Regaleira', cat: 'Nature', catTint: 'bg-emerald-50 text-emerald-700 border-emerald-200', accent: 'bg-emerald-400', dot: '#10b981' },
    ],
    routeD: 'M82 80 Q 60 60, 45 45 T 18 18',
    pins: [
      { cx: 82, cy: 80, color: '#eab308', n: 1 },
      { cx: 45, cy: 45, color: '#f59e0b', n: 2 },
      { cx: 18, cy: 18, color: '#10b981', n: 3 },
    ],
  },
];

const IDEA_BIN_ITEMS = [
  { name: 'Time Out Market', cat: 'Food', catTint: 'bg-amber-50 text-amber-700 border-amber-200', accent: 'bg-amber-400', up: 5, down: 0 },
  { name: 'Belém Tower', cat: 'Landmarks & Viewpoints', catTint: 'bg-yellow-50 text-yellow-700 border-yellow-200', accent: 'bg-yellow-400', up: 4, down: 1 },
  { name: 'LX Factory', cat: 'Culture', catTint: 'bg-violet-50 text-violet-700 border-violet-200', accent: 'bg-violet-400', up: 3, down: 2 },
  { name: 'Quinta da Regaleira', cat: 'Nature', catTint: 'bg-emerald-50 text-emerald-700 border-emerald-200', accent: 'bg-emerald-400', up: 4, down: 0 },
  { name: 'Fado in Alfama', cat: 'Nightlife', catTint: 'bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200', accent: 'bg-fuchsia-400', up: 5, down: 0 },
];

function PlanModeMockup({ interactive = false }: { interactive?: boolean }) {
  const [dayIdx, setDayIdx] = useState(0);
  const day = PLAN_DAYS[dayIdx];

  const handleDay = (i: number) => {
    if (!interactive) return;
    setDayIdx(i);
  };

  return (
    <div className="rounded-3xl bg-white p-4 md:p-6 shadow-2xl shadow-indigo-900/10 border border-slate-100">
      <div className="flex items-center mb-4 px-1 gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          {interactive && (
            <button
              onClick={() => handleDay((dayIdx - 1 + PLAN_DAYS.length) % PLAN_DAYS.length)}
              className="p-1.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
              aria-label="Previous day"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
          )}
          <div className="flex gap-1.5">
            {PLAN_DAYS.map((d, i) => {
              const active = i === dayIdx;
              return (
                <button
                  key={d.id}
                  onClick={() => handleDay(i)}
                  disabled={!interactive}
                  className={`text-[11px] font-bold px-3 py-1.5 rounded-full transition-all ${
                    active
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-200 scale-105'
                      : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                  } ${interactive ? 'cursor-pointer' : 'cursor-default'}`}
                >
                  {d.label}
                  {active && <span className="hidden md:inline ml-1.5 opacity-80 font-medium">· {d.weekday} {d.date}</span>}
                </button>
              );
            })}
          </div>
          {interactive && (
            <button
              onClick={() => handleDay((dayIdx + 1) % PLAN_DAYS.length)}
              className="p-1.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
              aria-label="Next day"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4">
        <TimelinePanel day={day} />
        <MapPanel day={day} />
        <IdeaBinPanel />
      </div>
    </div>
  );
}

function TimelinePanel({ day }: { day: PlanDay }) {
  return (
    <div className="flex flex-col gap-2.5 p-3 bg-white rounded-2xl border border-slate-200 shadow-sm min-h-[260px]">
      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">
        <Clock className="w-3 h-3" /> Timeline
      </div>
      <motion.div
        key={day.id}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex flex-col gap-2.5 relative pl-3"
      >
        <div className="absolute left-[3px] top-1 bottom-1 w-px bg-slate-200" />
        {day.events.map((e, i) => (
          <motion.div
            key={`${day.id}-${e.time}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.05 * i }}
            className="relative"
          >
            <div
              className="absolute -left-[10px] top-3 w-2 h-2 rounded-full ring-2 ring-white"
              style={{ backgroundColor: e.dot }}
            />
            <div className="ml-2 p-2.5 rounded-xl bg-white border border-slate-200 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
              <div className="flex items-start gap-1.5 mb-1.5">
                <GripVertical className="w-2.5 h-2.5 text-slate-300 mt-0.5 shrink-0" />
                <span className="text-[11px] font-black text-slate-900 leading-tight truncate flex-1">{e.title}</span>
              </div>
              <div className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-indigo-50 border border-indigo-100 mb-1">
                <span className="text-[8px] font-bold text-indigo-700 font-mono tracking-tight">{e.time}–{e.endTime}</span>
                <Pencil className="w-2 h-2 text-indigo-400" />
              </div>
              <div>
                <span className={`inline-block text-[8px] font-bold uppercase tracking-wider rounded-md px-1.5 py-0.5 border ${e.catTint}`}>
                  {e.cat}
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}

function MapPanel({ day }: { day: PlanDay }) {
  return (
    <div className="relative p-3 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden min-h-[260px]">
      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
        <MapIcon className="w-3 h-3" /> Map · {day.weekday} {day.date}
      </div>
      <div className="relative w-full aspect-square rounded-xl bg-gradient-to-br from-indigo-50 via-violet-50 to-emerald-50 border border-indigo-100 overflow-hidden">
        <svg className="absolute inset-0 w-full h-full opacity-30" viewBox="0 0 100 100" preserveAspectRatio="none">
          {[20, 40, 60, 80].map((v) => (
            <g key={v}>
              <line x1={v} y1={0} x2={v} y2={100} stroke="#cbd5e1" strokeWidth="0.2" />
              <line x1={0} y1={v} x2={100} y2={v} stroke="#cbd5e1" strokeWidth="0.2" />
            </g>
          ))}
        </svg>
        <motion.svg
          key={day.id}
          className="absolute inset-0 w-full h-full"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          <motion.path
            d={day.routeD}
            fill="none"
            stroke="url(#routeGrad)"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeDasharray="3 2"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.1, ease: 'easeInOut' }}
          />
          <defs>
            <linearGradient id="routeGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#4f46e5" />
              <stop offset="100%" stopColor="#d946ef" />
            </linearGradient>
          </defs>
        </motion.svg>
        <motion.div key={`${day.id}-pins`} className="absolute inset-0">
          {day.pins.map((p, i) => (
            <motion.div
              key={`${day.id}-pin-${p.n}`}
              initial={{ scale: 0, y: -8 }}
              animate={{ scale: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 + 0.08 * i, type: 'spring', stiffness: 220 }}
              className="absolute -translate-x-1/2 -translate-y-full"
              style={{ left: `${p.cx}%`, top: `${p.cy}%` }}
            >
              <div className="relative flex flex-col items-center">
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black text-white ring-2 ring-white shadow-lg"
                  style={{ backgroundColor: p.color }}
                >
                  {p.n}
                </div>
                <div className="w-1.5 h-1.5 rotate-45 -mt-0.5" style={{ backgroundColor: p.color }} />
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}

function IdeaBinPanel() {
  return (
    <div className="flex flex-col gap-2 p-3 bg-white rounded-2xl border border-slate-200 shadow-sm min-h-[260px]">
      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">
        <Sparkles className="w-3 h-3 text-indigo-600" /> Idea Bin
      </div>
      {IDEA_BIN_ITEMS.slice(0, 4).map((it, idx) => (
        <motion.div
          key={it.name}
          initial={{ opacity: 0, x: 10 }}
          whileInView={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.35, delay: 0.05 * idx }}
          viewport={{ once: true }}
          className="relative pl-2 rounded-xl bg-white border border-slate-200 shadow-[0_1px_2px_rgba(0,0,0,0.04)] overflow-hidden"
        >
          <div className={`absolute left-0 top-0 bottom-0 w-1 ${it.accent}`} />
          <div className="p-2 pl-2.5">
            <div className="flex items-center gap-1.5 mb-1">
              <MapPin className="w-2.5 h-2.5 text-indigo-500 shrink-0" />
              <span className="text-[10px] font-black text-slate-900 truncate flex-1">{it.name}</span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className={`text-[8px] font-bold uppercase tracking-wider rounded-md px-1.5 py-0.5 border ${it.catTint} truncate`}>
                {it.cat}
              </span>
              <div className="flex items-center gap-1 shrink-0">
                <span className="inline-flex items-center gap-0.5 text-[9px] font-bold text-slate-600 bg-slate-50 rounded px-1 py-0.5 border border-slate-100">
                  <ThumbsUp className="w-2 h-2" />{it.up}
                </span>
                <span className="inline-flex items-center gap-0.5 text-[9px] font-bold text-slate-400 bg-slate-50 rounded px-1 py-0.5 border border-slate-100">
                  <ThumbsDown className="w-2 h-2" />{it.down}
                </span>
              </div>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// ── Page ────────────────────────────────────────────────────────────────────

export default function Home() {
  const containerRef = useRef<HTMLDivElement>(null);
  const heroRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress: heroProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  });
  const heroOpacity = useTransform(heroProgress, [0, 0.8], [1, 0]);
  const heroY = useTransform(heroProgress, [0, 1], [0, 80]);

  useEffect(() => {
    if (!containerRef.current) return;

    if (typeof window !== 'undefined' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      gsap.set(['.reveal', '.hero-fade'], { opacity: 1, y: 0, clearProps: 'transform' });
      return;
    }

    const ctx = gsap.context(() => {
      gsap.to('.hero-fade', {
        opacity: 1, y: 0, duration: 1.1, ease: 'power3.out', stagger: 0.14,
      });

      gsap.utils.toArray<HTMLElement>('.reveal').forEach((el) => {
        gsap.to(el, {
          opacity: 1, y: 0, duration: 0.9, ease: 'power3.out',
          scrollTrigger: { trigger: el, start: 'top 88%' },
        });
      });

      gsap.utils.toArray<HTMLElement>('.reveal-scale').forEach((el) => {
        gsap.fromTo(el,
          { opacity: 0, scale: 0.94, y: 30 },
          {
            opacity: 1, scale: 1, y: 0, duration: 1, ease: 'power3.out',
            scrollTrigger: { trigger: el, start: 'top 88%' },
          }
        );
      });

      gsap.utils.toArray<HTMLElement>('.parallax-slow').forEach((el) => {
        gsap.to(el, {
          y: -60,
          ease: 'none',
          scrollTrigger: { trigger: el, start: 'top bottom', end: 'bottom top', scrub: true },
        });
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={containerRef} className="flex flex-col min-h-screen bg-white text-slate-900 overflow-x-hidden selection:bg-indigo-600 selection:text-white">
      <Navbar />

      {/* ── HERO ────────────────────────────────────────────────────────── */}
      <section ref={heroRef} aria-labelledby="hero-h" className="relative pt-32 pb-24 md:pt-44 md:pb-32 px-6 md:px-10 overflow-hidden">
        <div className="absolute inset-0 -z-10 pointer-events-none">
          <div className="blob blob-1 absolute top-[-20%] left-[-10%] w-[60vw] h-[60vw] bg-indigo-300/30 rounded-full blur-[140px]" />
          <div className="blob blob-2 absolute bottom-[-15%] right-[-10%] w-[55vw] h-[55vw] bg-fuchsia-300/30 rounded-full blur-[130px]" />
          <div className="blob blob-3 absolute top-[30%] right-[25%] w-[30vw] h-[30vw] bg-amber-200/30 rounded-full blur-[120px]" />
        </div>

        <motion.div
          style={{ opacity: heroOpacity, y: heroY }}
          className="max-w-5xl mx-auto text-center flex flex-col items-center"
        >
          <h1 id="hero-h" className="hero-fade opacity-0 translate-y-6 text-5xl md:text-7xl lg:text-8xl font-black text-slate-900 tracking-tighter leading-[1.02] mb-8">
            The travel planner that{' '}
            <span className="italic text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-violet-600">
              travels with you.
            </span>
          </h1>
          <p className="hero-fade opacity-0 translate-y-6 text-lg md:text-xl text-slate-500 leading-relaxed font-medium max-w-2xl mb-10">
            Most apps stop the moment you board the plane. Roammate keeps working — re-routing your day when you're late, finding a coffee shop near your next stop, and re-balancing the group's plan in real time.
          </p>
          <div className="hero-fade opacity-0 translate-y-6">
            <Link
              href="/login?signup=true"
              className="group inline-flex items-center justify-center gap-2 px-8 py-4 bg-slate-900 text-white rounded-2xl font-bold hover:bg-indigo-600 transition-all shadow-xl shadow-slate-200 hover:shadow-2xl hover:shadow-indigo-200 hover:scale-105 active:scale-95"
            >
              Start free
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </motion.div>

        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 opacity-40">
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">Scroll</span>
          <ChevronDown className="w-4 h-4 animate-bounce text-indigo-600" />
        </div>
      </section>

      {/* ── FEATURE 1 — BRAINSTORM ───────────────────────────────────── */}
      <FeatureRow
        anchor="brainstorm"
        accentText="text-violet-600"
        chipBg="bg-violet-50"
        chipText="text-violet-700"
        chipLabel="Brainstorm"
        title="Turn loose ideas into a real plan."
        body="Tell our AI what you're craving. It comes back with real places — already enriched with locations, opening hours, and everything you need to drop them into your day."
        bullets={[
          'A dedicated chat for every trip — context never leaks',
          'Every suggestion is a real, mappable place — never a hallucination',
          'Multi-turn refinement — ask for swaps, dig deeper, narrow the vibe',
          'Auto-detects duplicates so your bin stays clean',
        ]}
        mockup={<BrainstormMockup />}
        reverse={false}
      />

      {/* ── FEATURE 2 — IDEA BIN + VOTING ─────────────────────────────── */}
      <FeatureRow
        anchor="idea-bin"
        accentText="text-rose-500"
        chipBg="bg-rose-50"
        chipText="text-rose-700"
        chipLabel="Idea Bin + Voting"
        title="Group input without group chat chaos."
        body="Everyone's ideas land in one shared bin. Vote them up — or down. The plan reflects the group, not the loudest voice on WhatsApp."
        bullets={[]}
        mockup={<IdeaBinMockup />}
        reverse
      />

      {/* ── FEATURE 3 — PLAN MODE (anchor) ────────────────────────────── */}
      <section id="plan-mode" aria-labelledby="planmode-h" className="bg-gradient-to-b from-white to-indigo-50/40 pt-8 pb-16 md:pt-10 md:pb-20 px-6 md:px-10 scroll-mt-20">
        <div className="max-w-7xl mx-auto">
          <div className="reveal opacity-0 translate-y-4 text-center mb-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-[10px] font-bold uppercase tracking-widest mb-3">
              <Layers className="w-3 h-3" /> Plan Mode
            </div>
            <h2 id="planmode-h" className="text-3xl md:text-5xl font-black text-slate-900 tracking-tighter mb-3">
              Timeline. Map. Ideas. <span className="text-indigo-600">One canvas.</span>
            </h2>
            <p className="text-base md:text-lg text-slate-500 font-medium max-w-2xl mx-auto leading-snug">
              Drag an idea onto a day. Pick a time. The route emerges on the map. That&apos;s it.
            </p>
          </div>
          <div className="reveal-scale">
            <p className="text-center text-[11px] font-bold uppercase tracking-widest text-indigo-600 mb-2">
              ✨ Try it — tap a day below
            </p>
            <PlanModeMockup interactive />
          </div>
        </div>
      </section>

      {/* ── FEATURE 4 — CONCIERGE ─────────────────────────────────────── */}
      <section id="how-it-works" aria-labelledby="concierge-h" className="bg-indigo-50 pt-10 pb-20 md:pt-14 md:pb-28 px-6 md:px-10 overflow-hidden scroll-mt-20">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-16 items-center">
          <div>
            <div className="reveal opacity-0 translate-y-4 inline-flex items-center gap-2 px-3 py-1 bg-indigo-100 text-indigo-600 rounded-full text-[10px] font-bold uppercase tracking-widest mb-5">
              <Wand2 className="w-3 h-3" /> Concierge
            </div>
            <h2 id="concierge-h" className="reveal opacity-0 translate-y-4 text-3xl md:text-5xl font-black tracking-tighter mb-4 text-slate-900">
              Plans change. So does <span className="text-indigo-600">your day.</span>
            </h2>
            <p className="reveal opacity-0 translate-y-4 text-lg text-slate-500 font-medium leading-relaxed mb-6 max-w-xl">
              Running late by 45 minutes? Tap once. Roammate reflows the day, finds a coffee near you, and pings the group. Your co-pilot during the trip — not just before it.
            </p>
            <div className="reveal opacity-0 translate-y-4 grid grid-cols-2 gap-3 max-w-lg">
              {[
                { icon: Clock, label: 'Running late' },
                { icon: ArrowRight, label: 'Skip next' },
                { icon: Coffee, label: 'Find X near me' },
                { icon: MessageSquare, label: 'Free-form chat' },
              ].map(({ icon: Icon, label }) => (
                <div key={label} className="flex items-center gap-3 px-4 py-3 bg-white border border-slate-200 rounded-xl hover:border-indigo-300 hover:bg-indigo-50 transition-colors">
                  <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-sm font-semibold text-slate-900">{label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="reveal-scale">
            <ConciergeStoryboard />
          </div>
        </div>
      </section>

      {/* ── FEATURE 5 — PERSONAS ─────────────────────────────────────── */}
      <section aria-labelledby="personas-h" className="py-20 md:py-28 px-6 md:px-10">
        <div className="max-w-7xl mx-auto">
          <div className="reveal opacity-0 translate-y-4 text-center mb-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-fuchsia-50 text-fuchsia-700 rounded-full text-[10px] font-bold uppercase tracking-widest mb-5">
              <Sparkles className="w-3 h-3" /> Personas
            </div>
            <h2 id="personas-h" className="text-3xl md:text-5xl font-black text-slate-900 tracking-tighter mb-4">
              AI that knows <span className="text-fuchsia-600">your style.</span>
            </h2>
            <p className="text-lg text-slate-500 font-medium max-w-2xl mx-auto leading-relaxed">
              Foodie, cultural deep-diver, slow traveler — pick a persona and every suggestion tilts to match. Same prompt, different answer.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <PersonaMockup persona="Foodie" accent="amber" items={['Tasca da Esquina — neighborhood bistro', 'Pastelaria 1829 — pastéis benchmark', 'Time Out Market — chef-curated stalls']} />
            <PersonaMockup persona="Cultural Deep-Diver" accent="fuchsia" items={['Jerónimos Monastery — Manueline crown jewel', 'Gulbenkian — Lalique + Ancient Egypt', 'Fado vadio in Alfama — no tourists']} />
          </div>
        </div>
      </section>

      {/* ── PRICING TEASER ───────────────────────────────────────────── */}
      <section aria-labelledby="pricing-h" className="py-20 md:py-28 px-6 md:px-10">
        <div className="max-w-5xl mx-auto">
          <div className="reveal opacity-0 translate-y-4 text-center mb-10">
            <h2 id="pricing-h" className="text-3xl md:text-5xl font-black text-slate-900 tracking-tighter mb-3">
              Free to start. <span className="text-indigo-600">Plus when you outgrow it.</span>
            </h2>
            <p className="text-slate-500 font-medium">Every core feature works for free. Plus removes the limits.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              viewport={{ once: true }}
              className="rounded-3xl bg-white border border-slate-200 p-8 hover:border-slate-300 hover:shadow-lg transition-all"
            >
              <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">Free</div>
              <div className="text-3xl font-black text-slate-900 tracking-tighter mb-5">Everything to plan a great trip.</div>
              <ul className="space-y-2.5 mb-7">
                <PriceFeature icon={Compass} text="2 active trips at a time" free />
                <PriceFeature icon={Sparkles} text="15 AI brainstorms per month" free />
                <PriceFeature icon={ThumbsUp} text="Group voting & full Plan Mode" free />
              </ul>
              <Link href="/login?signup=true" className="inline-flex items-center gap-2 text-sm font-bold text-slate-900 hover:text-indigo-600 transition-colors">
                Start free <ArrowRight className="w-4 h-4" />
              </Link>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
              viewport={{ once: true }}
              className="relative rounded-3xl bg-gradient-to-br from-indigo-600 via-fuchsia-500 to-amber-500 p-8 text-white shadow-xl shadow-indigo-200 overflow-hidden hue-loop"
            >
              <div className="blob absolute -top-20 -right-20 w-[280px] h-[280px] bg-white/20 rounded-full blur-3xl" />
              <div className="relative">
                <div className="text-xs font-bold uppercase tracking-widest text-white/80 mb-3">Plus</div>
                <div className="text-3xl font-black tracking-tighter mb-5">Everything, unlimited.</div>
                <ul className="space-y-2.5 mb-7">
                  <PriceFeature icon={InfinityIcon} text="Unlimited trips & brainstorms" />
                  <PriceFeature icon={Wand2} text="Always-on AI Concierge" />
                  <PriceFeature icon={MapPinned} text="Offline maps for the road" />
                </ul>
                <Link href="/pricing" className="inline-flex items-center gap-2 text-sm font-bold bg-white text-indigo-600 px-4 py-2 rounded-full hover:bg-slate-900 hover:text-white transition-colors">
                  See Plus <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── FINAL CTA ────────────────────────────────────────────────── */}
      <section aria-labelledby="cta-h" className="py-20 md:py-28 px-6 md:px-10">
        <motion.div
          initial={{ opacity: 0, y: 30, scale: 0.96 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          viewport={{ once: true }}
          className="max-w-6xl mx-auto bg-indigo-600 rounded-[2.5rem] px-8 py-20 md:py-28 text-center text-white relative overflow-hidden"
        >
          <div className="blob absolute -top-32 -right-20 w-[440px] h-[440px] bg-indigo-400/30 rounded-full blur-3xl" />
          <div className="blob absolute -bottom-24 -left-20 w-[360px] h-[360px] bg-indigo-300/20 rounded-full blur-3xl" />
          <h2 id="cta-h" className="relative text-7xl md:text-9xl lg:text-[10rem] font-black tracking-tighter leading-[0.95] mb-12">
            Ready to<br />
            <span className="italic font-black text-indigo-200">Roam?</span>
          </h2>
          <Link href="/login?signup=true" className="relative inline-flex items-center gap-3 px-8 py-4 bg-white text-indigo-600 rounded-full font-black text-lg hover:bg-slate-900 hover:text-white transition-all shadow-2xl hover:scale-105 active:scale-95">
            Start Your First Trip <Compass className="w-5 h-5" />
          </Link>
        </motion.div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-100 pt-16 pb-10 px-6 md:px-10 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-10 md:gap-16 mb-12">
            <div className="col-span-2 space-y-5">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 bg-indigo-600 rounded-2xl flex items-center justify-center font-black text-white text-xl shadow-lg shadow-indigo-200">R</div>
                <span className="text-2xl font-black tracking-tighter text-slate-900">Roammate</span>
              </div>
              <p className="text-slate-500 font-medium max-w-sm leading-relaxed">
                The travel planner that travels with you.
              </p>
            </div>

            <FooterColumn title="Product" links={[
              { href: '#brainstorm', label: 'Features' },
              { href: '#plan-mode', label: 'How it works' },
              { href: '/pricing', label: 'Pricing' },
            ]} />
            <FooterColumn title="Company" links={[
              { href: '#', label: 'About' },
              { href: '#', label: 'Contact' },
              { href: '#', label: 'Privacy' },
              { href: '#', label: 'Terms' },
            ]} />
          </div>

          <div className="pt-8 border-t border-slate-100 flex flex-col md:flex-row justify-between items-center gap-6">
            <p className="text-slate-400 text-xs font-bold uppercase tracking-widest">© 2026 Roammate. All rights reserved.</p>
            <div className="flex gap-6 text-[10px] font-bold uppercase tracking-widest text-slate-400">
              <a href="#" className="hover:text-indigo-600 transition-colors">X / Twitter</a>
              <a href="#" className="hover:text-indigo-600 transition-colors">Instagram</a>
              <a href="#" className="hover:text-indigo-600 transition-colors">LinkedIn</a>
            </div>
          </div>
        </div>
      </footer>

      <style jsx global>{`
        html { scroll-behavior: smooth; }
        @keyframes blobFloat {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(30px, -20px) scale(1.08); }
          66% { transform: translate(-20px, 25px) scale(0.95); }
        }
        .blob { animation: blobFloat 18s ease-in-out infinite; }
        .blob-2 { animation-duration: 22s; animation-delay: -6s; }
        .blob-3 { animation-duration: 26s; animation-delay: -12s; }
        @keyframes hueShift {
          0%, 100% { filter: hue-rotate(0deg); }
          50% { filter: hue-rotate(15deg); }
        }
        .hue-loop { animation: hueShift 8s ease-in-out infinite; }
        @media (prefers-reduced-motion: reduce) {
          html { scroll-behavior: auto; }
          .blob, .hue-loop { animation: none !important; }
        }
      `}</style>
    </div>
  );
}

// ── FeatureRow ──────────────────────────────────────────────────────────────

function FeatureRow({
  anchor, accentText, chipBg, chipText, chipLabel,
  title, body, bullets, mockup, reverse,
}: {
  anchor: string;
  accentText: string;
  chipBg: string;
  chipText: string;
  chipLabel: string;
  title: string;
  body: string;
  bullets: string[];
  mockup: React.ReactNode;
  reverse: boolean;
}) {
  const [first, ...rest] = title.split('.');
  const accentPart = rest.join('.').trim();

  return (
    <section id={anchor} aria-labelledby={`${anchor}-h`} className="pt-10 pb-20 md:pt-14 md:pb-28 px-6 md:px-10 scroll-mt-20">
      <div className={`max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-14 items-start ${reverse ? 'lg:[&>*:first-child]:order-2' : ''}`}>
        <div>
          <div className={`reveal opacity-0 translate-y-4 inline-flex items-center gap-2 px-3 py-1 ${chipBg} ${chipText} rounded-full text-[10px] font-bold uppercase tracking-widest mb-5`}>
            {chipLabel}
          </div>
          <h2 id={`${anchor}-h`} className="reveal opacity-0 translate-y-4 text-3xl md:text-5xl font-black text-slate-900 tracking-tighter mb-4 leading-[1.05]">
            {first}.{accentPart && <> <span className={accentText}>{accentPart}</span></>}
          </h2>
          <p className="reveal opacity-0 translate-y-4 text-lg text-slate-500 font-medium leading-relaxed mb-5 max-w-xl">
            {body}
          </p>
          {bullets.length > 0 && (
            <ul className="reveal opacity-0 translate-y-4 space-y-2.5">
              {bullets.map((b) => (
                <li key={b} className="flex items-start gap-3 text-base text-slate-700 font-medium">
                  <span className={`mt-1 inline-flex w-4 h-4 rounded-full ${chipBg} ${chipText} items-center justify-center shrink-0`}>
                    <Check className="w-2.5 h-2.5" />
                  </span>
                  {b}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="reveal-scale">{mockup}</div>
      </div>
    </section>
  );
}

// ── Price feature row ──────────────────────────────────────────────────────

function PriceFeature({
  icon: Icon, text, free = false,
}: { icon: React.ComponentType<{ className?: string }>; text: string; free?: boolean }) {
  return (
    <li className={`flex items-center gap-3 text-sm font-semibold ${free ? 'text-slate-700' : 'text-white'}`}>
      <span className={`inline-flex w-7 h-7 rounded-lg items-center justify-center shrink-0 ${free ? 'bg-indigo-50 text-indigo-600' : 'bg-white/20 text-white'}`}>
        <Icon className="w-3.5 h-3.5" />
      </span>
      {text}
    </li>
  );
}

// ── Mockups ─────────────────────────────────────────────────────────────────

function BrainstormMockup() {
  return (
    <div className="rounded-3xl bg-white p-6 md:p-7 shadow-2xl shadow-violet-900/10 border border-slate-100 max-w-lg mx-auto">
      <div className="flex items-center gap-2 pb-4 mb-4 border-b border-slate-100">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center text-white shadow-md shadow-violet-200">
          <Sparkles className="w-4 h-4" />
        </div>
        <div>
          <div className="text-[13px] font-black text-slate-900 tracking-tight">Brainstorm · Lisbon</div>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">AI co-planner</div>
        </div>
      </div>
      <div className="space-y-3">
        <div className="bg-slate-100 rounded-2xl rounded-br-sm px-4 py-3 text-sm text-slate-700 font-medium ml-auto max-w-[80%]">
          3 days in Lisbon, foodie vibe, no museums
        </div>
        <div className="bg-violet-50 border border-violet-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-700 max-w-[92%]">
          <div className="font-bold text-violet-700 mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" /> Here&apos;s a starting list
          </div>
          <ul className="space-y-1.5 text-slate-700">
            <li>• Time Out Market — chef stalls</li>
            <li>• Pastéis de Belém — original recipe</li>
            <li>• Tasca da Esquina — bistro</li>
          </ul>
          <button className="mt-3 inline-flex items-center gap-1.5 text-xs font-bold text-violet-700 bg-white border border-violet-200 px-3 py-1.5 rounded-full">
            <Sparkles className="w-3 h-3" /> Add all to Idea Bin
          </button>
        </div>
        <div className="bg-slate-100 rounded-2xl rounded-br-sm px-4 py-3 text-sm text-slate-700 font-medium ml-auto max-w-[80%]">
          Skip the markets — add something for nightlife
        </div>
        <div className="bg-violet-50 border border-violet-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-700 max-w-[92%]">
          <div className="font-bold text-violet-700 mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" /> Got it — swapped them out
          </div>
          <ul className="space-y-1.5 text-slate-700">
            <li>• Tasca Bela — late-night Fado in Alfama</li>
            <li>• Park Bar — rooftop sundowners</li>
            <li>• Pensão Amor — old-Lisbon cocktails</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function IdeaBinMockup() {
  return (
    <div className="rounded-3xl bg-white p-5 shadow-2xl shadow-rose-900/10 border border-slate-100 max-w-md mx-auto space-y-3">
      {IDEA_BIN_ITEMS.slice(0, 4).map((it, i) => (
        <motion.div
          key={it.name}
          initial={{ opacity: 0, x: 20 }}
          whileInView={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.45, delay: i * 0.07, ease: [0.22, 1, 0.36, 1] }}
          viewport={{ once: true }}
          className="relative rounded-2xl bg-white border border-slate-200 shadow-sm overflow-hidden"
        >
          <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${it.accent}`} />
          <div className="p-3 pl-4">
            <div className="flex items-center gap-2 mb-1.5">
              <MapPin className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
              <span className="text-sm font-black text-slate-900 truncate flex-1">{it.name}</span>
            </div>
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-3 h-3 text-slate-400" />
              <span className="text-[11px] font-semibold text-slate-500">10am</span>
            </div>
            <span className={`inline-block text-[9px] font-bold uppercase tracking-wider rounded-md px-1.5 py-0.5 border ${it.catTint} mb-2`}>
              {it.cat}
            </span>
            <div className="flex items-center justify-between gap-2 pt-1.5 border-t border-slate-100">
              <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-semibold">
                <UserIcon className="w-3 h-3" /> Aman
              </div>
              <div className="flex items-center gap-1.5">
                <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-slate-700 bg-slate-50 rounded-md px-1.5 py-0.5 border border-slate-100">
                  <ThumbsUp className="w-2.5 h-2.5" />{it.up}
                </span>
                <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-slate-400 bg-slate-50 rounded-md px-1.5 py-0.5 border border-slate-100">
                  <ThumbsDown className="w-2.5 h-2.5" />{it.down}
                </span>
              </div>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

function ConciergeStoryboard() {
  const frames = [
    { label: 'Running late +45 min', icon: Clock },
    { label: 'Day reflows', icon: Wand2 },
    { label: 'Group pinged', icon: Bell },
  ];
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {frames.map((f, i) => (
          <motion.div
            key={f.label}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: i * 0.15, ease: [0.22, 1, 0.36, 1] }}
            viewport={{ once: true }}
            className="rounded-2xl bg-white border border-slate-200 p-5 flex flex-col items-start gap-3 hover:bg-indigo-50 hover:border-indigo-300 transition-colors"
          >
            <div className="w-10 h-10 rounded-xl bg-indigo-500 text-white flex items-center justify-center shadow-lg shadow-indigo-500/40">
              <f.icon className="w-5 h-5" />
            </div>
            <div className="text-[10px] font-bold text-indigo-500 uppercase tracking-widest">Step {i + 1}</div>
            <div className="text-base font-bold text-slate-900">{f.label}</div>
          </motion.div>
        ))}
      </div>

      <ConciergeChatPreview />
    </div>
  );
}

function ConciergeChatPreview() {
  const messages = [
    { from: 'user', text: "We're running 45 minutes late at lunch." },
    { from: 'ai', text: 'Got it — pushed your 2pm to 2:45pm. Skipped the LX Factory detour. Walking to Time Out Market is 8 min from here.' },
    { from: 'user', text: 'Find a coffee place nearby?' },
    { from: 'ai', text: 'Fábrica Coffee Roasters is 2 min away, 4.6★ — added between stops.' },
  ];
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
      viewport={{ once: true }}
      className="rounded-2xl bg-white border border-slate-200 p-5"
    >
      <div className="flex items-center gap-2 pb-4 mb-4 border-b border-slate-200">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-fuchsia-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
          <Wand2 className="w-4 h-4" />
        </div>
        <div>
          <div className="text-[13px] font-black text-slate-900 tracking-tight">Concierge · Live</div>
          <div className="text-[10px] font-bold text-indigo-500 uppercase tracking-widest flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Watching your trip
          </div>
        </div>
      </div>
      <div className="space-y-2.5">
        {messages.map((m, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: m.from === 'user' ? 12 : -12 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.1 + i * 0.08 }}
            viewport={{ once: true }}
            className={`max-w-[85%] px-3.5 py-2.5 text-[13px] leading-snug rounded-2xl ${
              m.from === 'user'
                ? 'ml-auto bg-indigo-600 text-white rounded-br-sm'
                : 'bg-indigo-50 border border-indigo-200 text-slate-900 rounded-tl-sm'
            }`}
          >
            {m.text}
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

function PersonaMockup({ persona, accent, items }: { persona: string; accent: 'amber' | 'fuchsia'; items: string[] }) {
  const accentClasses = accent === 'amber'
    ? { chip: 'bg-amber-50 text-amber-700 border-amber-200', bubble: 'bg-amber-50 border-amber-100' }
    : { chip: 'bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200', bubble: 'bg-fuchsia-50 border-fuchsia-100' };
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      viewport={{ once: true }}
      className="rounded-3xl bg-white p-6 border border-slate-100 shadow-lg hover:shadow-xl transition-shadow"
    >
      <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest mb-4 border ${accentClasses.chip}`}>
        {persona}
      </div>
      <div className="space-y-3">
        <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-slate-700 font-medium ml-auto max-w-[75%]">
          3 days in Lisbon
        </div>
        <div className={`${accentClasses.bubble} border rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-700 max-w-[90%]`}>
          <ul className="space-y-1.5">
            {items.map((it) => <li key={it}>• {it}</li>)}
          </ul>
        </div>
      </div>
    </motion.div>
  );
}

function FooterColumn({ title, links }: { title: string; links: { href: string; label: string }[] }) {
  return (
    <div className="space-y-5">
      <h5 className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">{title}</h5>
      <div className="flex flex-col gap-3 text-sm font-semibold text-slate-600">
        {links.map((l) => (
          <Link key={l.label} href={l.href} className="hover:text-indigo-600 transition-colors">{l.label}</Link>
        ))}
      </div>
    </div>
  );
}
