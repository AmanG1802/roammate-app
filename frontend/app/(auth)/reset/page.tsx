'use client';

import Link from 'next/link';
import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { auth } from '@/lib/api';
import { setToken } from '@/lib/auth';
import { AuthCard, StatusBanner } from '@/components/auth/AuthCard';
import { PasswordField } from '@/components/auth/Fields';
import { PrimaryButton } from '@/components/auth/PrimaryButton';

function ResetInner() {
  const router = useRouter();
  const search = useSearchParams();
  const token = search.get('token') ?? '';
  const [pwd, setPwd] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: 'error' | 'success' | 'info'; message: string } | null>(
    token ? null : { type: 'error', message: 'Missing reset token.' }
  );

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pwd !== confirm) {
      setStatus({ type: 'error', message: 'Passwords do not match' });
      return;
    }
    setLoading(true);
    setStatus(null);
    try {
      const pair = await auth.reset(token, pwd);
      setToken(pair.access_token);
      if (typeof window !== 'undefined') localStorage.setItem('user', JSON.stringify(pair.user));
      router.push('/dashboard');
    } catch (err) {
      setStatus({ type: 'error', message: err instanceof Error ? err.message : 'Reset failed' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthCard
      title="Choose a new password"
      subtitle="Make it long, unique, and unforgettable."
      footer={
        <p className="text-slate-500 font-medium">
          <Link href="/login" className="text-indigo-600 font-black hover:text-indigo-700">
            Back to sign in
          </Link>
        </p>
      }
    >
      <StatusBanner status={status} />
      <form onSubmit={onSubmit} className="space-y-4">
        <PasswordField value={pwd} onChange={(e) => setPwd(e.target.value)} placeholder="New password" autoComplete="new-password" />
        <PasswordField value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Confirm password" autoComplete="new-password" />
        <PrimaryButton loading={loading} disabled={!token}>Update password</PrimaryButton>
      </form>
    </AuthCard>
  );
}

export default function ResetPage() {
  return (
    <Suspense fallback={null}>
      <ResetInner />
    </Suspense>
  );
}
