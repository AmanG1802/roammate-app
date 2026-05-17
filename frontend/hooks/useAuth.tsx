'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { clearSession, getToken, setToken } from '@/lib/auth';
import { toastBus } from '@/lib/toast-bus';

/**
 * Read the current user. Source of truth is the cookie-backed /api/auth/me;
 * we also keep the legacy localStorage cache so offline reads still work.
 *
 * If `requireAuth` is true and we get a 401, redirect to /login. (Server-side
 * middleware does the same for non-API routes — this hook handles the case
 * where the access cookie has expired but middleware allowed the page through
 * because the refresh cookie is still there.)
 */
export default function useAuth(requireAuth: boolean = true) {
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/api/auth/me', { credentials: 'include' });
        if (res.ok) {
          const userData = await res.json();
          if (cancelled) return;
          setUser(userData);
          localStorage.setItem('user', JSON.stringify(userData));
          setIsLoading(false);
          return;
        }
        if (res.status === 401) {
          // Try silent refresh once.
          const r = await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' });
          if (r.ok) {
            const pair = await r.json();
            setToken(pair.access_token);
            const me = await fetch('/api/auth/me', { credentials: 'include' });
            if (me.ok) {
              const userData = await me.json();
              if (cancelled) return;
              setUser(userData);
              localStorage.setItem('user', JSON.stringify(userData));
              setIsLoading(false);
              return;
            }
          }
          clearSession();
          if (requireAuth) router.push('/login');
          else if (!cancelled) setIsLoading(false);
          return;
        }
        // Other status: treat as best-effort cached
        const savedUser = localStorage.getItem('user');
        if (savedUser && !cancelled) {
          try { setUser(JSON.parse(savedUser)); } catch { /* ignore */ }
        }
        if (!cancelled) setIsLoading(false);
      } catch {
        const savedUser = localStorage.getItem('user');
        if (savedUser && !cancelled) {
          try {
            setUser(JSON.parse(savedUser));
            toastBus('Offline — showing cached profile', { kind: 'info' });
          } catch { /* ignore */ }
        }
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [requireAuth, router]);

  return { user, isLoading };
}

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  // Server-side middleware already gates protected pages by the rm_access /
  // rm_refresh cookies. This component now just runs useAuth so the in-page
  // user state is hydrated; no extra redirect is needed.
  useAuth(true);
  // Suppress unused-import warning when getToken isn't referenced elsewhere
  void getToken;
  return <>{children}</>;
}
