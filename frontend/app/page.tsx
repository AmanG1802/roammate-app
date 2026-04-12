'use client';

import { useEffect, useRef } from 'react';
import Link from "next/link";
import { 
  Compass, Sparkles, Zap, Clock, Users, ArrowRight, 
  ChevronDown, CheckCircle2, Map as MapIcon, 
  Calendar, Globe, CloudOff, HeartPulse, ShieldCheck 
} from 'lucide-react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Navbar from '@/components/layout/Navbar';

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

export default function Home() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const ctx = gsap.context(() => {
      // 1. HERO REVEAL (Perspective Scale-In)
      const tlHero = gsap.timeline();
      tlHero.to(".hero-title span", {
        y: 0,
        opacity: 1,
        scale: 1,
        rotateX: 0,
        duration: 1.5,
        stagger: 0.1,
        ease: "expo.out"
      })
      .to(".hero-subtitle, .hero-cta, .concierge-badge", {
        opacity: 1,
        y: 0,
        duration: 1,
        stagger: 0.1,
        ease: "power3.out"
      }, "-=1");

      // 2. MAGNETIC BUTTONS
      const buttons = gsap.utils.toArray<HTMLElement>('.magnetic-btn');
      buttons.forEach((btn) => {
        btn.addEventListener('mousemove', (e: MouseEvent) => {
          const rect = btn.getBoundingClientRect();
          const x = e.clientX - rect.left - rect.width / 2;
          const y = e.clientY - rect.top - rect.height / 2;
          gsap.to(btn, { x: x * 0.3, y: y * 0.3, duration: 0.3 });
        });
        btn.addEventListener('mouseleave', () => {
          gsap.to(btn, { x: 0, y: 0, duration: 0.5, ease: "elastic.out(1, 0.3)" });
        });
      });

      // 3. CLIP-PATH SECTION WIPES
      const revealSections = gsap.utils.toArray<HTMLElement>('section[data-scene]');
      revealSections.forEach((section) => {
        gsap.fromTo(section, 
          { clipPath: "inset(5% 5% 5% 5% round 4rem)" },
          {
            clipPath: "inset(0% 0% 0% 0% round 0rem)",
            scrollTrigger: {
              trigger: section,
              start: "top 95%",
              end: "top 20%",
              scrub: 1,
            }
          }
        );
      });

      // 4. FEATURE CARDS (Cascading 3D Tilt)
      gsap.to(".feature-card", {
        scrollTrigger: {
          trigger: "#features",
          start: "top 85%",
        },
        y: 0,
        opacity: 1,
        rotationY: 0,
        duration: 1,
        stagger: 0.1,
        ease: "expo.out"
      });

      // 5. SHOWCASE ANIMATION (Ensuring high visibility)
      gsap.to(".showcase-content, .showcase-image", {
        scrollTrigger: {
          trigger: "#showcase",
          start: "top 80%",
        },
        opacity: 1,
        x: 0,
        duration: 1.2,
        stagger: 0.2,
        ease: "power4.out"
      });

      gsap.to(".showcase-image-inner", {
        scrollTrigger: {
          trigger: "#showcase",
          start: "top bottom",
          end: "bottom top",
          scrub: true,
        },
        rotateY: 10,
        rotateX: 2,
        ease: "none"
      });

      // 6. UNIVERSAL EXIT (Shrink & Blur)
      revealSections.forEach((scene) => {
        gsap.to(scene, {
          scrollTrigger: {
            trigger: scene,
            start: "bottom 90%",
            end: "bottom top",
            scrub: true,
          },
          opacity: 0,
          scale: 0.95,
          filter: "blur(8px)",
          ease: "none"
        });
      });

      // 7. FLOATING LOOPS
      gsap.to(".float-icon", {
        y: 10,
        duration: 2.5,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut"
      });

    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={containerRef} className="flex flex-col min-h-screen bg-white text-slate-900 overflow-x-hidden selection:bg-indigo-600 selection:text-white">
      <Navbar />
      
      {/* SECTION 1: HERO */}
      <section data-scene className="relative min-h-screen flex flex-col items-center justify-start pt-32 pb-12 bg-white overflow-hidden">
        <div className="absolute inset-0 -z-10 pointer-events-none">
          <div className="absolute top-[-20%] left-[-10%] w-[60vw] h-[60vw] bg-indigo-50/50 rounded-full blur-[140px]" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[50vw] h-[50vw] bg-violet-50/50 rounded-full blur-[120px]" />
        </div>

        <div className="relative z-10 max-w-6xl w-full flex flex-col items-center text-center">
          <div className="concierge-badge opacity-0 translate-y-4 inline-flex items-center gap-2 px-5 py-2 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-black uppercase tracking-[0.3em] mb-6 shadow-sm border border-indigo-100/50 float-icon">
            <Sparkles className="w-3.5 h-3.5" />
            Adaptive Concierge Engine
          </div>

          <h1 className="hero-title text-5xl md:text-7xl lg:text-8xl font-black text-slate-900 mb-10 leading-[1.1] tracking-tighter flex flex-col items-center perspective-1000">
            <span className="inline-block opacity-0 translate-y-20 scale-110 rotate-x-12 py-2">Plan Anything.</span>
            <span className="inline-block opacity-0 translate-y-20 scale-110 rotate-x-12 italic text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-violet-600 py-2">Move Everywhere.</span>
          </h1>

          <p className="hero-subtitle opacity-0 translate-y-4 text-lg md:text-xl text-slate-500 mb-12 max-w-2xl mx-auto leading-relaxed font-medium">
            Roammate is the world's first <span className="text-slate-900 font-bold">Self-Healing</span> itinerary. It adapts to weather, your mood, and the chaos of travel.
          </p>
          
          <div className="hero-cta opacity-0 translate-y-4 flex flex-col sm:flex-row gap-6 justify-center w-full max-w-md mx-auto relative z-20">
            <Link 
              href="/login?signup=true" 
              className="magnetic-btn flex-1 px-8 py-5 bg-slate-900 text-white rounded-[1.5rem] font-black text-lg hover:bg-indigo-600 transition-all shadow-xl shadow-indigo-100 group flex items-center justify-center gap-2 overflow-hidden relative"
            >
              <span className="relative z-10">Start Trip</span>
              <Compass className="relative z-10 w-5 h-5 group-hover:rotate-45 transition-transform duration-500" />
            </Link>
            <a 
              href="#showcase"
              className="magnetic-btn flex-1 px-8 py-5 bg-white text-slate-900 border-2 border-slate-100 rounded-[1.5rem] font-black text-lg hover:border-indigo-200 hover:shadow-lg transition-all flex items-center justify-center gap-2"
            >
              See Product
            </a>
          </div>
        </div>

        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 opacity-40">
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 font-mono tracking-widest">Scroll Story</span>
          <ChevronDown className="w-4 h-4 animate-bounce text-indigo-600" />
        </div>
      </section>

      {/* SECTION 2: FEATURES */}
      <section data-scene id="features" className="py-32 px-8 max-w-7xl mx-auto w-full bg-slate-50 rounded-[4rem] relative z-20 my-20 border border-slate-100 shadow-inner scroll-mt-24">
        <div className="flex flex-col items-center mb-24 text-center">
          <div className="px-4 py-1 bg-indigo-600 text-white rounded-full text-[10px] font-black uppercase tracking-widest mb-6">Capabilities</div>
          <h2 className="text-4xl md:text-7xl font-black text-slate-900 mb-6 tracking-tighter leading-tight">Itineraries with <span className="italic text-indigo-600">Instinct.</span></h2>
          <p className="text-lg md:text-xl text-slate-600 font-medium max-w-2xl">Traditional itineraries are static. Roammate evolves as you move through the world.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 perspective-1000">
          {[
            { icon: Zap, title: "Ripple Engine", desc: "Running late? Our engine recursively shifts your entire day, preserving transit buffers and reservations.", color: "bg-indigo-600" },
            { icon: Clock, title: "Smart Timeboxing", desc: "Real-time Google Maps transit calculations between every stop. If it's physically impossible, we warn you.", color: "bg-rose-500" },
            { icon: Users, title: "Co-Pilot Sync", desc: "Real-time collaborative planning. See active member cursors and live itinerary mutations as they happen.", color: "bg-amber-500" },
            { icon: HeartPulse, title: "Vibe Check", desc: "Proactive prompts that re-optimize your route based on your energy levels and local conditions.", color: "bg-green-500" },
            { icon: CloudOff, title: "Offline-First", desc: "Reliable logic even in the dead zones. Your itinerary stays synced locally and pushes updates later.", color: "bg-slate-700" },
            { icon: ShieldCheck, title: "Anchor Locking", desc: "Define hard constraints like flights or tour starts. The engine shifts everything around them.", color: "bg-violet-600" }
          ].map((feature, i) => (
            <div key={i} className="feature-card opacity-0 translate-y-10 rotate-y-10 group p-10 rounded-[2.5rem] bg-white border border-slate-200 shadow-xl shadow-indigo-900/5 transition-all duration-500 cursor-default hover:shadow-2xl hover:border-indigo-300 hover:-translate-y-2">
              <div className={`w-16 h-16 ${feature.color} text-white rounded-2xl flex items-center justify-center mb-8 group-hover:scale-110 transition-transform duration-500 shadow-lg shadow-indigo-200/50`}>
                <feature.icon className="w-8 h-8" />
              </div>
              <h3 className="text-2xl font-black mb-4 text-slate-900 tracking-tighter">{feature.title}</h3>
              <p className="text-base text-slate-500 leading-relaxed font-medium">{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* SECTION 3: SHOWCASE */}
      <section data-scene id="showcase" className="py-32 bg-slate-900 text-white overflow-hidden relative rounded-[4rem] mx-4 md:mx-8 shadow-2xl scroll-mt-24">
        <div className="max-w-7xl mx-auto px-8 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
            <div className="showcase-content opacity-0 -translate-x-10">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/10 rounded-full text-[10px] font-black uppercase tracking-widest mb-8 border border-white/10">
                <Globe className="w-3 h-3 text-indigo-400" />
                World-Class Interface
              </div>
              <h2 className="text-4xl md:text-7xl font-black mb-10 tracking-tighter leading-[0.9] text-white">Everything in its <br/>Right Place.</h2>
              <div className="space-y-8">
                {[
                  { title: "3-Pane Strategy", desc: "Map, Vertical Timeline, and Idea Bin all synced in real-time." },
                  { title: "Contextual Action Bar", desc: "Floating 'Concierge' buttons for when life actually happens." },
                  { title: "Draggable Logic", desc: "Simply move an idea to the timeline; we handle the geo-math." }
                ].map((item, i) => (
                  <div key={i} className="flex gap-4 items-start group">
                    <div className="mt-1 w-6 h-6 rounded-full bg-indigo-500 flex items-center justify-center shrink-0">
                      <CheckCircle2 className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <h4 className="text-xl font-bold mb-1 tracking-tight text-white">{item.title}</h4>
                      <p className="text-slate-400 font-medium text-sm leading-relaxed">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="showcase-image opacity-0 translate-x-10 relative perspective-1000">
              <div className="showcase-image-inner aspect-[4/3] bg-white rounded-[2rem] overflow-hidden shadow-[0_50px_100px_-20px_rgba(0,0,0,0.5)] border-[10px] border-slate-800 relative transform-gpu">
                {/* Mockup Dashboard Content (High Contrast) */}
                <div className="flex h-full text-slate-900 bg-white">
                  {/* Sidebar */}
                  <div className="w-[20%] border-r border-slate-200 bg-slate-50/50 p-4 space-y-6">
                    <div className="w-8 h-8 bg-indigo-600 rounded-lg mb-8 shadow-lg shadow-indigo-200" />
                    <div className="space-y-3">
                      <div className="h-2 w-full bg-slate-200 rounded-full" />
                      <div className="h-2 w-2/3 bg-slate-200 rounded-full opacity-50" />
                    </div>
                    <div className="pt-10 space-y-4">
                      <div className="h-10 w-full bg-indigo-100/50 border border-indigo-200 rounded-xl" />
                      <div className="h-10 w-full bg-slate-100 rounded-xl" />
                    </div>
                  </div>
                  {/* Main Area */}
                  <div className="flex-1 p-8 space-y-8 flex flex-col bg-white">
                    <div className="flex justify-between items-center shrink-0">
                      <div className="h-6 w-1/3 bg-slate-900 rounded-lg opacity-80" />
                      <div className="flex -space-x-3">
                        <div className="w-8 h-8 rounded-full bg-indigo-500 border-2 border-white shadow-sm" />
                        <div className="w-8 h-8 rounded-full bg-violet-500 border-2 border-white shadow-sm" />
                        <div className="w-8 h-8 rounded-full bg-slate-200 border-2 border-white flex items-center justify-center text-[8px] font-bold">+2</div>
                      </div>
                    </div>
                    {/* Fake Map */}
                    <div className="h-48 w-full bg-indigo-50/30 border-2 border-dashed border-indigo-200 rounded-[2.5rem] flex items-center justify-center relative overflow-hidden group-hover:bg-indigo-50/50 transition-colors">
                       <MapIcon className="w-12 h-12 text-indigo-300 animate-pulse" />
                       {/* Markers */}
                       <div className="absolute top-1/2 left-1/3 w-4 h-4 bg-indigo-600 rounded-full border-2 border-white shadow-lg" />
                       <div className="absolute top-1/3 right-1/4 w-4 h-4 bg-violet-600 rounded-full border-2 border-white shadow-lg" />
                    </div>
                    {/* Itinerary Cards */}
                    <div className="grid grid-cols-2 gap-6 flex-1">
                      <div className="bg-slate-50 border border-slate-100 rounded-3xl p-5 space-y-3 shadow-sm">
                        <div className="flex justify-between">
                          <div className="h-4 w-1/2 bg-slate-900 rounded-full opacity-70" />
                          <div className="h-4 w-8 bg-indigo-100 rounded-lg" />
                        </div>
                        <div className="h-2 w-3/4 bg-slate-300 rounded-full opacity-30" />
                      </div>
                      <div className="bg-white border border-indigo-100 rounded-3xl p-5 space-y-3 shadow-md ring-4 ring-indigo-50">
                        <div className="flex justify-between">
                          <div className="h-4 w-1/2 bg-indigo-600 rounded-full" />
                          <div className="h-4 w-8 bg-indigo-50 rounded-lg" />
                        </div>
                        <div className="h-2 w-3/4 bg-indigo-200 rounded-full opacity-50" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              {/* Atmospheric Glow */}
              <div className="absolute -z-10 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-indigo-500/40 blur-[140px]" />
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 4: HOW IT WORKS */}
      <section data-scene id="how-it-works" className="py-32 bg-white scroll-mt-24">
        <div className="max-w-7xl mx-auto px-8">
          <div className="text-center mb-24">
            <h2 className="text-4xl md:text-7xl font-black text-slate-900 mb-6 tracking-tighter">Zero Friction.</h2>
            <p className="text-lg text-slate-500 font-medium">From chaos to clarity in three simple steps.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-16">
            {[
              { step: "01", title: "Smart Ingest", desc: "Paste location lists, blog URLs, or just raw notes.", icon: MapIcon },
              { step: "02", title: "Drag & Plan", desc: "Organize your day visually. We handle the transit math.", icon: Calendar },
              { step: "03", title: "Adaptive Sync", desc: "The Concierge re-balances your day while keeping everyone in sync.", icon: Sparkles }
            ].map((item, i) => (
              <div key={i} className="relative group">
                <div className="text-8xl font-black text-slate-100 leading-none absolute -top-12 -left-4 -z-10 group-hover:text-indigo-50 transition-colors">{item.step}</div>
                <div className="w-14 h-14 bg-slate-900 text-white rounded-2xl flex items-center justify-center mb-6 shadow-lg group-hover:bg-indigo-600 transition-colors">
                  <item.icon className="w-7 h-7" />
                </div>
                <h3 className="text-2xl font-black mb-3 text-slate-900 tracking-tighter">{item.title}</h3>
                <p className="text-slate-500 font-medium leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 5: THE CATCH (CTA) */}
      <section className="py-32 bg-indigo-600 relative overflow-hidden rounded-[4rem] mx-4 md:mx-8 mb-20 shadow-2xl">
        <div className="absolute top-0 right-0 w-[1000px] h-[1000px] bg-white/10 rounded-full blur-[160px] -translate-y-1/2 translate-x-1/2" />
        <div className="max-w-4xl mx-auto px-8 text-center relative z-10">
          <h2 className="text-5xl md:text-[8rem] font-black text-white mb-10 tracking-tighter leading-[0.8]">Ready to <br/><span className="italic opacity-80">Roam?</span></h2>
          <p className="text-xl text-indigo-100 mb-12 font-medium max-w-lg mx-auto">The best way to see the world is with a plan that knows how to change.</p>
          <Link 
            href="/login?signup=true" 
            className="magnetic-btn inline-flex items-center gap-4 px-12 py-8 bg-white text-indigo-600 rounded-[2.5rem] font-black text-2xl hover:bg-slate-900 hover:text-white transition-all shadow-2xl active:scale-95 group"
          >
            Start Your First Trip
            <Compass className="w-10 h-10 group-hover:rotate-90 transition-transform duration-1000" />
          </Link>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-slate-100 pt-24 pb-12 px-8 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-16 mb-20 text-left">
            <div className="col-span-1 md:col-span-2 space-y-8">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center font-black text-white text-2xl shadow-xl">R</div>
                <span className="text-3xl font-black tracking-tighter text-slate-900">Roammate</span>
              </div>
              <p className="text-slate-500 font-medium max-w-sm leading-relaxed text-xl">
                Building the world's first intelligent travel concierge. Plan with intent, move with ease.
              </p>
            </div>
            
            <div className="space-y-8">
              <h5 className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-400">Product</h5>
              <div className="flex flex-col gap-5 text-sm font-bold text-slate-600">
                <a href="#features" className="hover:text-indigo-600 transition-all hover:translate-x-1">Capabilities</a>
                <a href="#showcase" className="hover:text-indigo-600 transition-all hover:translate-x-1">Showcase</a>
                <a href="#how-it-works" className="hover:text-indigo-600 transition-all hover:translate-x-1">Process</a>
              </div>
            </div>

            <div className="space-y-8">
              <h5 className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-400">Connect</h5>
              <div className="flex flex-col gap-5 text-sm font-bold text-slate-600">
                <a href="#" className="hover:text-indigo-600 transition-all hover:translate-x-1">X / Twitter</a>
                <a href="#" className="hover:text-indigo-600 transition-all hover:translate-x-1">Instagram</a>
                <a href="#" className="hover:text-indigo-600 transition-all hover:translate-x-1">LinkedIn</a>
              </div>
            </div>
          </div>

          <div className="pt-12 border-t border-slate-100 flex flex-col md:flex-row justify-between items-center gap-8">
            <p className="text-slate-400 text-xs font-black uppercase tracking-[0.2em]">© 2026 Roammate Technologies. All rights reserved.</p>
            <div className="flex gap-10 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
              <a href="#" className="hover:text-indigo-600 transition-colors">Privacy Policy</a>
              <a href="#" className="hover:text-indigo-600 transition-colors">Terms of Service</a>
            </div>
          </div>
        </div>
      </footer>

      <style jsx global>{`
        html { scroll-behavior: smooth; }
        .perspective-1000 { perspective: 1000px; }
        .rotate-x-12 { transform: rotateX(12deg); }
        .rotate-y-10 { transform: rotateY(10deg); }
        .ease-expo { transition-timing-function: cubic-bezier(0.87, 0, 0.13, 1); }
        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
          }
        }
      `}</style>
    </div>
  );
}
