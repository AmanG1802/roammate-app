'use client';

import Link from 'next/link';
import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ApiError, auth } from '@/lib/api';
import { setToken } from '@/lib/auth';
import { AuthCard, StatusBanner } from '@/components/auth/AuthCard';
import { PrimaryButton } from '@/components/auth/PrimaryButton';

function CheckInner() {
  const router = useRouter();
  const search = useSearchParams();
  const email = search.get('email') ?? '';
  const next = search.get('next') ?? '/dashboard';
  const [status, setStatus] = useState<{ type: 'error' | 'success' | 'info'; message: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [skipping, setSkipping] = useState(false);

  const resend = async () => {
    if (!email) return;
    setLoading(true);
    setStatus(null);
    try {
      await auth.resendVerify(email);
      setStatus({ type: 'success', message: 'Verification email re-sent. Check your inbox.' });
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Could not resend';
      setStatus({ type: 'error', message: msg });
    } finally {
      setLoading(false);
    }
  };

  const skipVerification = async () => {
    if (!email) return;
    setSkipping(true);
    setStatus(null);
    try {
      const pwd = sessionStorage.getItem('_rv_pwd');
      if (!pwd) {
        router.push(`/login?next=${encodeURIComponent(next)}`);
        return;
      }
      const pair = await auth.login({ email, password: pwd, skip_verification: true });
      sessionStorage.removeItem('_rv_pwd');
      setToken(pair.access_token);
      if (typeof window !== 'undefined') localStorage.setItem('user', JSON.stringify(pair.user));
      router.push(next);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Could not skip verification';
      setStatus({ type: 'error', message: msg });
    } finally {
      setSkipping(false);
    }
  };

  return (
    <AuthCard
      title="Check your email"
      subtitle={email ? `We sent a verification link to ${email}.` : 'We sent you a verification link.'}
      footer={
        <p className="text-slate-500 font-medium">
          Wrong address?{' '}
          <Link href="/signup" className="text-indigo-600 font-black hover:text-indigo-700">
            Sign up again
          </Link>
        </p>
      }
    >
      <StatusBanner status={status} />
      <p className="text-sm text-slate-500 mb-6">
        Click the link in your inbox to finish setting up your account. Didn&apos;t get it? Check your spam folder, then resend.
      </p>
      <form onSubmit={(e) => { e.preventDefault(); resend(); }} className="space-y-3">
        <PrimaryButton loading={loading} disabled={!email}>
          Resend verification email
        </PrimaryButton>
        <button
          type="button"
          onClick={skipVerification}
          disabled={skipping || !email}
          className="w-full py-2.5 text-sm font-semibold text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-50"
        >
          {skipping ? 'Signing in…' : 'Skip for now'}
        </button>
      </form>
    </AuthCard>
  );
}

export default function VerifyCheckPage() {
  return (
    <Suspense fallback={null}>
      <CheckInner />
    </Suspense>
  );
}
