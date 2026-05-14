import { create } from 'zustand';

interface AuthState {
  token: string | null;
  setToken: (token: string | null) => void;
}

const useAuthStore = create<AuthState>((set) => ({
  token: typeof window !== 'undefined' ? localStorage.getItem('token') : null,
  setToken: (token) => set({ token }),
}));

/** Read the current auth token from Zustand; falls back to localStorage for SSR/hydration. */
export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return useAuthStore.getState().token ?? localStorage.getItem('token');
}

/** Persist a new token to Zustand (does NOT write localStorage — callers do that). */
export function setToken(token: string | null): void {
  useAuthStore.getState().setToken(token);
}

export { useAuthStore };
