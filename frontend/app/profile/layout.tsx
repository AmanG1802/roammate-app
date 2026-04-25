'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { User, Sparkles, CreditCard, ArrowLeft, Loader2 } from 'lucide-react';
import useAuth from '@/hooks/useAuth';

const NAV_ITEMS = [
  { href: '/profile/edit', label: 'Edit Profile', icon: User },
  { href: '/profile/persona', label: 'User Persona', icon: Sparkles },
  { href: '/profile/subscription', label: 'Subscription', icon: CreditCard, badge: 'Soon' },
];

export default function ProfileLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading } = useAuth(true);

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-white">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-screen bg-slate-50 flex flex-col overflow-hidden">
      {/* Top bar */}
      <header className="h-14 bg-white border-b border-slate-100 flex items-center px-6 gap-4 shrink-0">
        <button
          onClick={() => router.push('/dashboard')}
          className="flex items-center gap-1.5 text-sm font-bold text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          Dashboard
        </button>
        <span className="text-slate-200">|</span>
        <span className="text-sm font-black text-slate-800">Profile</span>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left nav rail */}
        <aside className="w-60 shrink-0 bg-white border-r border-slate-100 flex flex-col py-6 px-3">
          {/* Avatar + name */}
          <div className="flex flex-col items-center gap-2 mb-8 px-3">
            <div className="w-16 h-16 rounded-full bg-indigo-600 flex items-center justify-center text-white font-black text-lg shrink-0 overflow-hidden">
              {(user as any)?.avatar_url
                ? <img src={(user as any).avatar_url} alt="Avatar" className="w-full h-full object-cover" />
                : user?.name?.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2) ?? '?'
              }
            </div>
            <p className="text-sm font-black text-slate-800 text-center truncate w-full">{user?.name ?? '—'}</p>
          </div>

          <nav className="flex flex-col gap-1">
            {NAV_ITEMS.map(({ href, label, icon: Icon, badge }) => {
              const active = pathname === href || (href === '/profile/edit' && pathname === '/profile');
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold transition-all relative
                    ${active
                      ? 'bg-indigo-50 text-indigo-700 border-l-[3px] border-indigo-600 pl-[9px]'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-800'
                    }`}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="flex-1">{label}</span>
                  {badge && (
                    <span className="text-[9px] font-black px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded-full uppercase tracking-wide">
                      {badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
