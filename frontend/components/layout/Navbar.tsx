'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { LogOut, Menu, X, ChevronRight } from 'lucide-react';
import { useState, useEffect, useRef, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { clearPlusOnboardingSeen, currentUserIdFromCache } from '@/lib/plusOnboarding';
import { motionTokens } from '@/lib/motion';

type SubItem = { id: string; label: string };

const FEATURE_SUB_ITEMS: SubItem[] = [
  { id: 'brainstorm', label: 'Brainstorm' },
  { id: 'idea-bin', label: 'Idea Bin' },
  { id: 'plan-mode', label: 'Plan Mode' },
  { id: 'how-it-works', label: 'Concierge' },
];

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<{ name: string } | null>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [featuresOpen, setFeaturesOpen] = useState(false);
  const featuresRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const checkUser = () => {
      const savedUser = localStorage.getItem('user');
      if (savedUser) {
        try {
          setUser(JSON.parse(savedUser));
        } catch {
          localStorage.removeItem('user');
        }
      } else {
        setUser(null);
      }
    };

    checkUser();
    window.addEventListener('storage', checkUser);
    return () => {
      window.removeEventListener('storage', checkUser);
    };
  }, []);

  // Collapse the Features submenu whenever the route changes.
  useEffect(() => {
    setFeaturesOpen(false);
    setIsMobileMenuOpen(false);
  }, [pathname]);

  // Click outside collapses the Features submenu.
  useEffect(() => {
    if (!featuresOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (!featuresRef.current?.contains(e.target as Node)) setFeaturesOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [featuresOpen]);

  const handleLogout = () => {
    const uid = currentUserIdFromCache();
    if (uid != null) clearPlusOnboardingSeen(uid);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    router.push('/');
  };

  const goToSection = useCallback((id: string) => {
    // Keep the Features submenu open when navigating between sub-items —
    // users often jump between sections. The menu collapses on route change
    // (e.g. clicking Pricing) via the pathname useEffect above.
    setIsMobileMenuOpen(false);
    if (pathname === '/') {
      const el = document.getElementById(id);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      router.push(`/#${id}`);
    }
  }, [pathname, router]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 transition-all duration-500 bg-white/90 backdrop-blur-xl border-b border-slate-100 py-4 shadow-sm">
      <div className="max-w-7xl mx-auto px-6 md:px-10 flex items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-2 group shrink-0">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center font-black text-white text-2xl shadow-lg shadow-indigo-200 group-hover:scale-110 transition-transform">R</div>
          <span className="text-2xl font-black tracking-tighter text-slate-900">Roammate</span>
        </Link>

        {/* Desktop center nav */}
        <div className="hidden md:flex items-center flex-1 justify-center">
          {!user ? (
            <div ref={featuresRef} className="relative flex items-center gap-2">
              <motion.div
                layout
                transition={{ type: 'spring', stiffness: 360, damping: 32 }}
                className="flex items-center gap-2"
              >
                <button
                  type="button"
                  onClick={() => setFeaturesOpen((v) => !v)}
                  aria-expanded={featuresOpen}
                  className={`text-[11px] font-black uppercase tracking-[0.2em] px-4 py-2 rounded-full transition-all flex items-center gap-1.5 ${
                    featuresOpen
                      ? 'bg-slate-900 text-white shadow-md'
                      : 'text-slate-500 hover:text-indigo-600'
                  }`}
                >
                  Features
                  <motion.span
                    animate={{ rotate: featuresOpen ? 90 : 0 }}
                    transition={{ duration: 0.25, ease: motionTokens.ease.out }}
                    className="inline-flex"
                  >
                    <ChevronRight className="w-3 h-3" />
                  </motion.span>
                </button>

                <AnimatePresence initial={false}>
                  {featuresOpen && (
                    <motion.div
                      key="sub"
                      initial={{ opacity: 0, width: 0, x: -8 }}
                      animate={{ opacity: 1, width: 'auto', x: 0 }}
                      exit={{ opacity: 0, width: 0, x: -8 }}
                      transition={{ duration: 0.32, ease: motionTokens.ease.out }}
                      className="flex items-center gap-1 overflow-hidden"
                    >
                      <span className="text-slate-300 mx-1">/</span>
                      {FEATURE_SUB_ITEMS.map((s, i) => (
                        <motion.button
                          key={s.id}
                          type="button"
                          onClick={() => goToSection(s.id)}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -6 }}
                          transition={{ duration: 0.25, delay: 0.04 * i, ease: motionTokens.ease.out }}
                          className="text-[11px] font-black uppercase tracking-[0.15em] text-slate-500 hover:text-indigo-600 px-3 py-2 rounded-full hover:bg-indigo-50 whitespace-nowrap transition-colors"
                        >
                          {s.label}
                        </motion.button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>

                <Link
                  href="/pricing"
                  className={`text-[11px] font-black uppercase tracking-[0.2em] px-4 py-2 rounded-full transition-colors ml-2 ${
                    pathname === '/pricing'
                      ? 'bg-slate-900 text-white shadow-md'
                      : 'text-slate-500 hover:text-indigo-600'
                  }`}
                >
                  Pricing
                </Link>
              </motion.div>
            </div>
          ) : (
            <div className="flex items-center gap-10">
              <Link href="/dashboard" className="text-[11px] font-black text-slate-500 hover:text-indigo-600 transition-colors uppercase tracking-[0.2em]">Dashboard</Link>
              <Link href="/trips" className="text-[11px] font-black text-slate-500 hover:text-indigo-600 transition-colors uppercase tracking-[0.2em]">Planner</Link>
            </div>
          )}
        </div>

        <div className="flex items-center gap-4 shrink-0">
          {user ? (
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex flex-col items-end">
                <span className="text-xs font-black text-slate-900">{user.name}</span>
                <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-tighter">Pro Member</span>
              </div>
              <button
                onClick={handleLogout}
                className="p-2.5 bg-slate-50 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-xl transition-all border border-slate-100"
                title="Logout"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          ) : (
            <div className="hidden sm:flex items-center gap-2">
              <Link href="/login" className="px-6 py-3 text-sm font-black text-slate-600 hover:text-indigo-600 transition-colors">Log In</Link>
              <Link href="/login?signup=true" className="px-8 py-3 bg-slate-900 text-white rounded-full text-sm font-black hover:bg-indigo-600 transition-all shadow-xl shadow-slate-200 active:scale-95">
                Join Free
              </Link>
            </div>
          )}

          <button className="md:hidden p-2 text-slate-600" onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
            {isMobileMenuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="md:hidden absolute top-full left-0 right-0 bg-white border-b border-slate-100 p-6 flex flex-col gap-3 shadow-xl"
          >
            {!user && (
              <>
                <button
                  type="button"
                  onClick={() => setFeaturesOpen((v) => !v)}
                  className="flex items-center justify-between text-sm font-bold text-slate-600"
                >
                  Features
                  <motion.span animate={{ rotate: featuresOpen ? 90 : 0 }}>
                    <ChevronRight className="w-4 h-4" />
                  </motion.span>
                </button>
                <AnimatePresence initial={false}>
                  {featuresOpen && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="flex flex-col gap-2 pl-4 overflow-hidden"
                    >
                      {FEATURE_SUB_ITEMS.map((s) => (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => goToSection(s.id)}
                          className="text-left text-sm font-semibold text-slate-500 hover:text-indigo-600"
                        >
                          {s.label}
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
                <Link href="/pricing" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-bold text-slate-600">Pricing</Link>
                <Link href="/login" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-bold text-slate-600">Log In</Link>
                <Link href="/login?signup=true" onClick={() => setIsMobileMenuOpen(false)} className="w-full py-4 bg-indigo-600 text-white rounded-2xl text-center font-bold">Join Roammate</Link>
              </>
            )}
            {user && (
              <>
                <Link href="/dashboard" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-bold text-slate-600">Dashboard</Link>
                <Link href="/trips" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-bold text-slate-600">Planner</Link>
                <button onClick={handleLogout} className="text-left text-sm font-bold text-rose-500">Log Out</button>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
