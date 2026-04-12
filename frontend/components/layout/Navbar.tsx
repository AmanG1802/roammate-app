'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Compass, Sparkles, User, LogOut, LayoutGrid, Map as MapIcon, Menu, X } from 'lucide-react';
import { useState, useEffect } from 'react';

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isScrolled, setIsScrolled] = useState(false);
  const [user, setUser] = useState<{ name: string } | null>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    
    // Check for user
    const checkUser = () => {
      const savedUser = localStorage.getItem('user');
      if (savedUser) {
        try {
          setUser(JSON.parse(savedUser));
        } catch (e) {
          localStorage.removeItem('user');
        }
      } else {
        setUser(null);
      }
    };

    checkUser();
    window.addEventListener('storage', checkUser);
    
    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('storage', checkUser);
    };
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    router.push('/');
  };

  const isLanding = pathname === '/';

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
      isScrolled || !isLanding ? 'bg-white/90 backdrop-blur-xl border-b border-slate-100 py-4 shadow-sm' : 'bg-transparent py-6'
    }`}>
      <div className="max-w-7xl mx-auto px-6 md:px-10 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center font-black text-white text-2xl shadow-lg shadow-indigo-200 group-hover:scale-110 transition-transform">R</div>
          <span className="text-2xl font-black tracking-tighter text-slate-900">Roammate</span>
        </Link>

        {/* Desktop Nav - Ordered by Landing Content */}
        <div className="hidden md:flex items-center gap-10">
          {!user ? (
            <>
              <a href="#features" className="text-[11px] font-black text-slate-500 hover:text-indigo-600 transition-colors uppercase tracking-[0.2em]">Features</a>
              <a href="#showcase" className="text-[11px] font-black text-slate-500 hover:text-indigo-600 transition-colors uppercase tracking-[0.2em]">Showcase</a>
              <a href="#how-it-works" className="text-[11px] font-black text-slate-500 hover:text-indigo-600 transition-colors uppercase tracking-[0.2em]">How it works</a>
            </>
          ) : (
            <>
              <Link href="/dashboard" className="text-[11px] font-black text-slate-500 hover:text-indigo-600 transition-colors uppercase tracking-[0.2em]">Dashboard</Link>
              <Link href="/trips" className="text-[11px] font-black text-slate-500 hover:text-indigo-600 transition-colors uppercase tracking-[0.2em]">Planner</Link>
            </>
          )}
        </div>

        <div className="flex items-center gap-4">
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
          
          {/* Mobile Menu Toggle */}
          <button className="md:hidden p-2 text-slate-600" onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
            {isMobileMenuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 bg-white border-b border-slate-100 p-6 flex flex-col gap-4 shadow-xl">
          {!user && (
            <>
              <a href="#features" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-bold text-slate-600">Features</a>
              <a href="#showcase" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-bold text-slate-600">Showcase</a>
              <a href="#how-it-works" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-bold text-slate-600">How it works</a>
              <Link href="/login" className="text-sm font-bold text-slate-600">Log In</Link>
              <Link href="/login?signup=true" className="w-full py-4 bg-indigo-600 text-white rounded-2xl text-center font-bold">Join Roammate</Link>
            </>
          )}
          {user && (
            <>
              <Link href="/dashboard" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-bold text-slate-600">Dashboard</Link>
              <Link href="/trips" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-bold text-slate-600">Planner</Link>
              <button onClick={handleLogout} className="text-left text-sm font-bold text-rose-500">Log Out</button>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
