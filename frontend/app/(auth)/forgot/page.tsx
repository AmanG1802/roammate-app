'use client';

import Link from 'next/link';
import { useState } from 'react';
import { auth } from '@/lib/api';
import { AuthCard, StatusBanner } from '@/components/auth/AuthCard';
import { EmailField } from '@/components/auth/Fields';
import { PrimaryButton } from '@/components/auth/PrimaryButton';

export default function ForgotPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: 'error' | 'success' | 'info'; message: string } | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatus(null);
    try {
      await auth.forgot(email);
      setStatus({ type: 'success', message: 'If an account exists for that email, a reset link is on its way.' });
    } catch (err) {
      setStatus({ type: 'error', message: err instanceof Error ? err.message : 'Could not send reset email' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthCard
      title="Reset your password"
      subtitle="Enter your email and we'll send you a reset link."
      footer={
        <p className="text-slate-500 font-medium">
          Remembered it?{' '}
          <Link href="/login" className="text-indigo-600 font-black hover:text-indigo-700">
            Back to sign in
          </Link>
        </p>
      }
    >
      <StatusBanner status={status} />
      <form onSubmit={onSubmit} className="space-y-4">
        <EmailField value={email} onChange={(e) => setEmail(e.target.value)} />
        <PrimaryButton loading={loading}>Send reset link</PrimaryButton>
      </form>
    </AuthCard>
  );
}
