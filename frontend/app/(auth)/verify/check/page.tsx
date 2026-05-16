'use client';

import Link from 'next/link';
import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { ApiError, auth } from '@/lib/api';
import { AuthCard, StatusBanner } from '@/components/auth/AuthCard';
import { PrimaryButton } from '@/components/auth/PrimaryButton';

function CheckInner() {
  const search = useSearchParams();
  const email = search.get('email') ?? '';
  const [status, setStatus] = useState<{ type: 'error' | 'success' | 'info'; message: string } | null>(null);
  const [loading, setLoading] = useState(false);

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
      <form onSubmit={(e) => { e.preventDefault(); resend(); }}>
        <PrimaryButton loading={loading} disabled={!email}>
          Resend verification email
        </PrimaryButton>
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
