/**
 * Cookie-forwarding proxy from the Next.js edge to the FastAPI backend.
 *
 * The browser hits /api/auth/login (and friends) on the same origin so that
 * Set-Cookie from the backend lands as first-party. We strip the absolute
 * URL, forward method+body+cookies, and pipe the response (including
 * Set-Cookie headers) back to the client.
 *
 * Routes covered: /api/auth/{signup,login,verify,verify/resend,refresh,
 * logout,google,apple,password/forgot,password/reset,me,me/identities,...}
 */
import { NextRequest, NextResponse } from 'next/server';

const BACKEND =
  process.env.BACKEND_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  'http://localhost:8000/api';

async function proxy(req: NextRequest, segments: string[]) {
  const path = segments.join('/');
  const url = `${BACKEND.replace(/\/$/, '')}/auth/${path}${req.nextUrl.search}`;

  const headers = new Headers();
  req.headers.forEach((v, k) => {
    // Hop-by-hop and host headers must not be forwarded.
    if (['host', 'connection', 'content-length'].includes(k.toLowerCase())) return;
    headers.set(k, v);
  });

  const init: RequestInit = {
    method: req.method,
    headers,
    redirect: 'manual',
  };
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    init.body = await req.arrayBuffer();
  }

  const res = await fetch(url, init);
  const respHeaders = new Headers();
  res.headers.forEach((value, key) => {
    // Node.js fetch auto-decompresses the body, so forwarding Content-Encoding
    // would cause the browser to attempt a second decompression and fail with
    // ERR_CONTENT_DECODING_FAILED. Strip it (and Content-Length, whose value
    // changes after decompression) so the browser reads the raw bytes directly.
    const lower = key.toLowerCase();
    if (lower === 'content-encoding' || lower === 'content-length') return;
    // pass everything else including Set-Cookie
    respHeaders.append(key, value);
  });
  const body = await res.arrayBuffer();
  return new NextResponse(body, { status: res.status, headers: respHeaders });
}

type Ctx = { params: { path: string[] } };

export async function GET(req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params.path); }
export async function POST(req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params.path); }
export async function PUT(req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params.path); }
export async function PATCH(req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params.path); }
export async function DELETE(req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params.path); }
