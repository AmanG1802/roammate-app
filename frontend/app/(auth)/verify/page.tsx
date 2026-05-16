'use client';

import Link from 'next/link';
import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { auth } from '@/lib/api';
import { setToken } from '@/lib/auth';
import { AuthCard, StatusBanner } from '@/components/auth/AuthCard';

function VerifyInner() {
  const router = useRouter();
  const search = useSearchParams();
  const token = search.get('token');
  const [status, setStatus] = useState<{ type: 'error' | 'success' | 'info'; message: string } | null>(
    token ? { type: 'info', message: 'Verifying your email…' } : { type: 'error', message: 'Missing verification token.' }
  );

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const pair = await auth.verify(token);
        if (cancelled) return;
        setToken(pair.access_token);
        if (typeof window !== 'undefined') localStorage.setItem('user', JSON.stringify(pair.user));
        setStatus({ type: 'success', message: 'Email verified! Redirecting…' });
        setTimeout(() => router.push('/dashboard'), 600);
      } catch (err) {
        if (cancelled) return;
        setStatus({ type: 'error', message: err instanceof Error ? err.message : 'Verification failed' });
      }
    })();
    return () => { cancelled = true; };
  }, [token, router]);

  return (
    <AuthCard
      title="Verify your email"
      subtitle="Confirming the link you clicked from your inbox."
      footer={
        <p className="text-slate-500 font-medium">
          Trouble signing in?{' '}
          <Link href="/login" className="text-indigo-600 font-black hover:text-indigo-700 transition-colors">
            Back to sign in
          </Link>
        </p>
      }
    >
      <StatusBanner status={status} />
    </AuthCard>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyInner />
    </Suspense>
  );
}
