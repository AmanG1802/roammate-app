'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';

const API = process.env.NEXT_PUBLIC_API_URL ?? '';
const STORAGE_KEY = 'admin_token';

export default function useAdminAuth() {
  const [adminToken, setAdminToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = sessionStorage.getItem(STORAGE_KEY);
    if (!token) {
      setIsLoading(false);
      return;
    }
    fetch(`${API}/admin/users`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (res.ok) {
          setAdminToken(token);
        } else {
          sessionStorage.removeItem(STORAGE_KEY);
        }
        setIsLoading(false);
      })
      .catch(() => {
        setIsLoading(false);
      });
  }, []);

  const login = useCallback(
    async (username: string, password: string): Promise<string | null> => {
      const res = await fetch(`${API}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        return data.detail || 'Invalid credentials';
      }
      const { access_token } = await res.json();
      sessionStorage.setItem(STORAGE_KEY, access_token);
      setAdminToken(access_token);
      return null;
    },
    []
  );

  const logout = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    setAdminToken(null);
    router.push('/admin');
  }, [router]);

  return { adminToken, login, logout, isLoading };
}
