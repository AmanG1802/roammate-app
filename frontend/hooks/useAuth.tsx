'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

function clearSession() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
}

export default function useAuth(requireAuth: boolean = true) {
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');

    if (requireAuth && !token) {
      router.push('/login');
      return;
    }

    if (!token) {
      setIsLoading(false);
      return;
    }

    // Validate the token against the backend
    const API = process.env.NEXT_PUBLIC_API_URL ?? '';
    fetch(`${API}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.ok) {
          const userData = await res.json();
          setUser(userData);
          localStorage.setItem('user', JSON.stringify(userData));
          setIsLoading(false);
        } else {
          // Token expired or invalid
          clearSession();
          if (requireAuth) router.push('/login');
          else setIsLoading(false);
        }
      })
      .catch(() => {
        // Network error — use cached user data if available
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
          try { setUser(JSON.parse(savedUser)); } catch { /* ignore */ }
        }
        setIsLoading(false);
      });
  }, [requireAuth, router]);

  return { user, isLoading };
}

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  // Pure redirect guard — always render children so SSR markup matches the
  // first client render (no hydration mismatch). If there's no token, kick
  // the user to /login on mount; if the token is rejected by the API later,
  // useAuth's background validator handles the redirect.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!localStorage.getItem('token')) {
      router.push('/login');
    }
  }, [router]);

  useAuth(true);

  return <>{children}</>;
}
