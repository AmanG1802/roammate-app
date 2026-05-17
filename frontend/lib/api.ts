/**
 * fetch wrapper for cookie-based auth.
 *
 * - All requests go to /api/... on the same origin (proxied to backend).
 * - On 401 we try /api/auth/refresh once, then retry the original request.
 * - JSON parsing + structured error are returned to callers.
 *
 * Existing components that still hit `${NEXT_PUBLIC_API_URL}/...` with an
 * Authorization: Bearer header continue to work — the backend accepts both
 * cookies and bearer tokens during the transition.
 */
export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, message: string, data: unknown = null) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

type ApiOptions = Omit<RequestInit, 'body'> & { json?: unknown };

async function doFetch(path: string, opts: ApiOptions): Promise<Response> {
  const headers = new Headers(opts.headers);
  let body: BodyInit | undefined;
  if (opts.json !== undefined) {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(opts.json);
  }
  return fetch(path.startsWith('/') ? path : `/${path}`, {
    ...opts,
    headers,
    body,
    credentials: 'include',
  });
}

let refreshing: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  if (refreshing) return refreshing;
  refreshing = (async () => {
    try {
      const r = await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' });
      return r.ok;
    } catch {
      return false;
    } finally {
      // give callers a window to read, then clear
      setTimeout(() => { refreshing = null; }, 0);
    }
  })();
  return refreshing;
}

export async function api<T = unknown>(path: string, opts: ApiOptions = {}): Promise<T> {
  let res = await doFetch(path, opts);
  if (res.status === 401 && !path.startsWith('/api/auth/')) {
    const ok = await refreshSession();
    if (ok) res = await doFetch(path, opts);
  }
  const ct = res.headers.get('content-type') ?? '';
  const data = ct.includes('application/json') ? await res.json().catch(() => null) : await res.text();
  if (!res.ok) {
    const detail =
      (data && typeof data === 'object' && 'detail' in data && (data as any).detail) ||
      res.statusText;
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail), data);
  }
  return data as T;
}

export const auth = {
  signup: (body: { email: string; password: string; name: string }) =>
    api<{ detail: string }>('/api/auth/signup', { method: 'POST', json: body }),
  login: (body: { email: string; password: string; skip_verification?: boolean }) =>
    api<TokenPair>('/api/auth/login', { method: 'POST', json: body }),
  verify: (token: string) =>
    api<TokenPair>('/api/auth/verify', { method: 'POST', json: { token } }),
  resendVerify: (email: string) =>
    api<void>('/api/auth/verify/resend', { method: 'POST', json: { email } }),
  google: (id_token: string) =>
    api<TokenPair>('/api/auth/google', { method: 'POST', json: { id_token, platform: 'web' } }),
  apple: (id_token: string, nonce?: string) =>
    api<TokenPair>('/api/auth/apple', { method: 'POST', json: { id_token, platform: 'web', nonce } }),
  forgot: (email: string) =>
    api<void>('/api/auth/password/forgot', { method: 'POST', json: { email } }),
  reset: (token: string, new_password: string) =>
    api<TokenPair>('/api/auth/password/reset', { method: 'POST', json: { token, new_password } }),
  logout: () => api<void>('/api/auth/logout', { method: 'POST' }),
  me: () => api<MeResponse>('/api/auth/me'),
  identities: () => api<IdentitiesResponse>('/api/auth/me/identities'),
  unlink: (provider: 'google' | 'apple') =>
    api<void>(`/api/auth/me/identities/${provider}`, { method: 'DELETE' }),
};

export type MeResponse = {
  id: number;
  email: string;
  name: string | null;
  avatar_url: string | null;
  email_verified: boolean;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: MeResponse;
};

export type IdentitiesResponse = {
  has_password: boolean;
  identities: { provider: string; email_at_link: string | null; created_at: string | null }[];
};
