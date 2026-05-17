/**
 * Cookie-based route protection.
 *
 * Public routes: anything under /auth/* (login, signup, verify, reset, etc.),
 * /pricing, /api/*, and Next internals.
 *
 * Private routes: everything else. If `rm_access` is missing, redirect to
 * /login?next=<original-path>. We don't decode the JWT here (no backend
 * secret in middleware); the API will reject expired tokens, and the api()
 * wrapper handles silent /api/auth/refresh.
 */
import { NextRequest, NextResponse } from 'next/server';

const PUBLIC_PREFIXES = [
  '/api',
  '/_next',
  '/favicon',
  '/pricing',
  '/verify',     // /verify and /verify/check
];

const PUBLIC_FILES = new Set(['/', '/login', '/signup', '/forgot', '/reset']);

function isPublic(pathname: string): boolean {
  if (PUBLIC_FILES.has(pathname)) return true;
  return PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + '/'));
}

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (isPublic(pathname)) return NextResponse.next();

  const hasAccess = req.cookies.has('rm_access');
  const hasRefresh = req.cookies.has('rm_refresh');
  if (hasAccess || hasRefresh) return NextResponse.next();

  const url = req.nextUrl.clone();
  url.pathname = '/login';
  url.search = `?next=${encodeURIComponent(pathname + search)}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
