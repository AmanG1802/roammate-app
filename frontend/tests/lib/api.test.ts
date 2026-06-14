import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, ApiError } from '@/lib/api';

// ── Response builders ─────────────────────────────────────────────────────────

function jsonResponse(
  body: unknown,
  { status = 200, ok, statusText = 'Status' }: { status?: number; ok?: boolean; statusText?: string } = {},
): Response {
  return {
    ok: ok ?? (status >= 200 && status < 300),
    status,
    statusText,
    headers: { get: (h: string) => (h.toLowerCase() === 'content-type' ? 'application/json' : null) },
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

function textResponse(text: string, { status = 200 }: { status?: number } = {}): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: 'OK',
    headers: { get: () => 'text/plain' },
    text: async () => text,
    json: async () => { throw new Error('not json'); },
  } as unknown as Response;
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(async () => {
  // lib/api.ts clears its module-level `refreshing` latch on a macrotask;
  // flush it so the next test starts from a clean slate.
  await new Promise((r) => setTimeout(r, 0));
  vi.unstubAllGlobals();
});

// ── Happy path ────────────────────────────────────────────────────────────────

describe('api() — requests', () => {
  it('parses a JSON response', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ hello: 'world' }));
    await expect(api('/api/trips')).resolves.toEqual({ hello: 'world' });
  });

  it('always sends credentials and normalizes a relative path', async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));
    await api('foo');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/foo');
    expect((init as RequestInit).credentials).toBe('include');
  });

  it('serializes a JSON body and sets Content-Type', async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));
    await api('/api/trips', { method: 'POST', json: { name: 'Trip' } });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect(init.body).toBe(JSON.stringify({ name: 'Trip' }));
    expect((init.headers as Headers).get('Content-Type')).toBe('application/json');
  });

  it('returns raw text for non-JSON responses', async () => {
    fetchMock.mockResolvedValue(textResponse('pong'));
    await expect(api('/api/ping')).resolves.toBe('pong');
  });
});

// ── Error mapping ─────────────────────────────────────────────────────────────

describe('api() — error handling', () => {
  it('throws ApiError with a string detail', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'Trip not found' }, { status: 404 }));
    const err: any = await api('/api/trips/999').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(404);
    expect(err.message).toBe('Trip not found');
  });

  it('stringifies an object detail and preserves raw data', async () => {
    const body = { detail: { code: 'needs_plus', feature: 'active_trips' } };
    fetchMock.mockResolvedValue(jsonResponse(body, { status: 402 }));
    const err: any = await api('/api/trips').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe(JSON.stringify(body.detail));
    expect(err.data).toEqual(body);
  });

  it('falls back to statusText when there is no detail', async () => {
    fetchMock.mockResolvedValue(jsonResponse({}, { status: 500, statusText: 'Server Error' }));
    const err: any = await api('/api/trips').catch((e) => e);
    expect(err.message).toBe('Server Error');
  });

  it('throws a friendly ApiError when JSON parsing fails', async () => {
    const broken = {
      ok: true,
      status: 200,
      statusText: 'OK',
      headers: { get: () => 'application/json' },
      json: async () => { throw new Error('boom'); },
      text: async () => '',
    } as unknown as Response;
    fetchMock.mockResolvedValue(broken);
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const err: any = await api('/api/trips').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toMatch(/Unexpected response/i);

    spy.mockRestore();
  });
});

// ── 401 refresh-and-retry ─────────────────────────────────────────────────────

describe('api() — 401 refresh flow', () => {
  it('refreshes once and retries the original request on 401', async () => {
    let tripCalls = 0;
    fetchMock.mockImplementation((url: string) => {
      if (url === '/api/auth/refresh') return Promise.resolve(jsonResponse({}, { status: 200 }));
      tripCalls += 1;
      return Promise.resolve(
        tripCalls === 1
          ? jsonResponse({ detail: 'unauthorized' }, { status: 401 })
          : jsonResponse({ ok: true }),
      );
    });

    await expect(api('/api/trips')).resolves.toEqual({ ok: true });
    expect(fetchMock.mock.calls.some(([u]) => u === '/api/auth/refresh')).toBe(true);
    expect(tripCalls).toBe(2);
  });

  it('does NOT refresh for auth endpoints', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'bad credentials' }, { status: 401 }));
    await expect(api('/api/auth/login', { method: 'POST', json: {} })).rejects.toMatchObject({
      status: 401,
    });
    expect(fetchMock.mock.calls.some(([u]) => u === '/api/auth/refresh')).toBe(false);
  });

  it('does not retry when the refresh fails', async () => {
    let tripCalls = 0;
    fetchMock.mockImplementation((url: string) => {
      if (url === '/api/auth/refresh') return Promise.resolve(jsonResponse({}, { status: 401 }));
      tripCalls += 1;
      return Promise.resolve(jsonResponse({ detail: 'unauthorized' }, { status: 401 }));
    });

    const err: any = await api('/api/trips').catch((e) => e);
    expect(err.status).toBe(401);
    expect(tripCalls).toBe(1);
  });
});
