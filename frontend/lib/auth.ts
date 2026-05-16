/**
 * Legacy localStorage token helpers — retained as a transition shim.
 *
 * After the auth refactor, the canonical session is the `rm_access` cookie set
 * by the backend (forwarded through /api/auth/*). New code should use lib/api
 * which automatically attaches cookies and silently refreshes on 401.
 *
 * Existing fetch sites that still pass `Authorization: Bearer ${getToken()}`
 * keep working because the backend accepts both transports.
 */
import { create } from 'zustand';

interface AuthState {
  token: string | null;
  setToken: (token: string | null) => void;
}

const useAuthStore = create<AuthState>((set) => ({
  token: typeof window !== 'undefined' ? localStorage.getItem('token') : null,
  setToken: (token) => set({ token }),
}));

/** Read the current access token (in-memory first, then localStorage). */
export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return useAuthStore.getState().token ?? localStorage.getItem('token');
}

/** Persist a new access token everywhere. Pass null to clear. */
export function setToken(token: string | null): void {
  useAuthStore.getState().setToken(token);
  if (typeof window === 'undefined') return;
  if (token) localStorage.setItem('token', token);
  else localStorage.removeItem('token');
}

export function clearSession(): void {
  setToken(null);
  if (typeof window !== 'undefined') localStorage.removeItem('user');
}

export { useAuthStore };
