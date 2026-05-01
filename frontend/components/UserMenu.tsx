'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { MoreVertical, User, LogOut } from 'lucide-react';

type UserMenuProps = {
  user: { name?: string; email?: string; avatar_url?: string | null } | null;
  getInitials: (name: string) => string;
};

export default function UserMenu({ user, getInitials }: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    router.push('/');
  };

  return (
    <div className="mt-auto pt-4 border-t border-slate-100">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center text-white font-black text-xs shrink-0 overflow-hidden">
          {user?.avatar_url
            ? <img src={user.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
            : user?.name ? getInitials(user.name) : '?'
          }
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-black text-slate-800 truncate">{user?.name ?? '—'}</p>
          <p className="text-[10px] font-bold text-slate-400 truncate">{user?.email ?? ''}</p>
        </div>
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setOpen((v) => !v)}
            title="More options"
            className="p-1.5 text-slate-300 hover:text-slate-600 transition-colors cursor-pointer"
            aria-label="User menu"
          >
            <MoreVertical className="w-4 h-4" />
          </button>
          {open && (
            <div className="absolute bottom-full right-0 mb-1 w-44 bg-white rounded-xl border border-slate-100 shadow-lg py-1 z-50">
              <button
                onClick={() => { setOpen(false); router.push('/profile'); }}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
              >
                <User className="w-4 h-4 text-slate-400" />
                Profile
              </button>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-sm font-bold text-rose-500 hover:bg-rose-50 transition-colors cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
