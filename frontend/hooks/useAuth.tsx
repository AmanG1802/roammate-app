'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

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
  const { isLoading } = useAuth(true);

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-white">
        <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}
