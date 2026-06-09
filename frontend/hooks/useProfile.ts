'use client';

import { useState, useCallback } from 'react';
import { api, ApiError } from '@/lib/api';

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

  const fetchProfile = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api<ProfileData>('/api/users/me');
      setProfile(data);
      localStorage.setItem('user', JSON.stringify(data));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateProfile = useCallback(async (updates: ProfileUpdate): Promise<boolean> => {
    try {
      const data = await api<ProfileData>('/api/users/me', { method: 'PUT', json: updates });
      setProfile(data);
      localStorage.setItem('user', JSON.stringify(data));
      return true;
    } catch (e: any) {
      setError(e instanceof ApiError ? e.message : 'Update failed');
      return false;
    }
  }, []);

  const updatePersonas = useCallback(async (personas: string[]): Promise<boolean> => {
    try {
      await api('/api/users/me/personas', { method: 'PUT', json: { personas } });
      if (profile) {
        const updated = { ...profile, personas };
        setProfile(updated);
        localStorage.setItem('user', JSON.stringify(updated));
      }
      return true;
    } catch (e: any) {
      setError(e instanceof ApiError ? e.message : 'Failed to save personas');
      return false;
    }
  }, [profile]);

  const deleteAccount = useCallback(async (): Promise<boolean> => {
    try {
      await api('/api/users/me', { method: 'DELETE' });
      // Clear localStorage and the rm_access / rm_refresh cookies.
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      await fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
      return true;
    } catch (e: any) {
      setError(e instanceof ApiError ? e.message : 'Failed to delete account');
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
