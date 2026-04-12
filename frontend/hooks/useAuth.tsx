'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function useAuth(requireAuth: boolean = true) {
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');

    if (requireAuth && !token) {
      router.push('/login');
      // keep isLoading=true so ProtectedRoute shows spinner during redirect
      return;
    }

    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        // Corrupt user data — clear session and redirect
        localStorage.removeItem('user');
        localStorage.removeItem('token');
        if (requireAuth) {
          router.push('/login');
          return;
        }
      }
    } else if (token && requireAuth) {
      // Token present but no user data (e.g. partial localStorage clear) — clear and redirect
      localStorage.removeItem('token');
      router.push('/login');
      return;
    }

    setIsLoading(false);
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
