'use client';

import { useState, useCallback } from 'react';

export type ProfileData = {
  id: number;
  email: string;
  name: string;
  personas: string[] | null;
  avatar_url: string | null;
  home_city: string | null;
  timezone: string | null;
  currency: string | null;
  travel_blurb: string | null;
  created_at: string | null;
};

type ProfileUpdate = {
  name?: string;
  avatar_url?: string;
  home_city?: string;
  timezone?: string;
  currency?: string;
  travel_blurb?: string;
  password?: string;
  current_password?: string;
};

export function useProfile() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getToken = () => (typeof window !== 'undefined' ? localStorage.getItem('token') : null);

  const fetchProfile = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const API = process.env.NEXT_PUBLIC_API_URL ?? '';
      const res = await fetch(`${API}/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load profile');
      const data = await res.json();
      setProfile(data);
      localStorage.setItem('user', JSON.stringify(data));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateProfile = useCallback(async (updates: ProfileUpdate): Promise<boolean> => {
    const token = getToken();
    if (!token) return false;
    try {
      const API = process.env.NEXT_PUBLIC_API_URL ?? '';
      const res = await fetch(`${API}/users/me`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Update failed');
      }
      const data = await res.json();
      setProfile(data);
      localStorage.setItem('user', JSON.stringify(data));
      return true;
    } catch (e: any) {
      setError(e.message);
      return false;
    }
  }, []);

  const updatePersonas = useCallback(async (personas: string[]): Promise<boolean> => {
    const token = getToken();
    if (!token) return false;
    try {
      const API = process.env.NEXT_PUBLIC_API_URL ?? '';
      const res = await fetch(`${API}/users/me/personas`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ personas }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to save personas');
      }
      if (profile) {
        const updated = { ...profile, personas };
        setProfile(updated);
        localStorage.setItem('user', JSON.stringify(updated));
      }
      return true;
    } catch (e: any) {
      setError(e.message);
      return false;
    }
  }, [profile]);

  const deleteAccount = useCallback(async (): Promise<boolean> => {
    const token = getToken();
    if (!token) return false;
    try {
      const API = process.env.NEXT_PUBLIC_API_URL ?? '';
      const res = await fetch(`${API}/users/me`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to delete account');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      return true;
    } catch (e: any) {
      setError(e.message);
      return false;
    }
  }, []);

  return {
    profile,
    isLoading,
    error,
    fetchProfile,
    updateProfile,
    updatePersonas,
    deleteAccount,
  };
}
