'use client';

import Link from 'next/link';
import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ApiError, auth, type TokenPair } from '@/lib/api';
import { setToken } from '@/lib/auth';
import { AuthCard, StatusBanner } from '@/components/auth/AuthCard';
import { EmailField, PasswordField } from '@/components/auth/Fields';
import { Divider, PrimaryButton } from '@/components/auth/PrimaryButton';
import { OAuthButtons } from '@/components/auth/OAuthButtons';

function LoginInner() {
  const router = useRouter();
  const search = useSearchParams();
  const next = search.get('next') ?? '/dashboard';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: 'error' | 'success' | 'info'; message: string } | null>(null);

  const onLand = (pair: TokenPair) => {
    setToken(pair.access_token);
    if (typeof window !== 'undefined') localStorage.setItem('user', JSON.stringify(pair.user));
    router.push(next);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus(null);
    setLoading(true);
    try {
      const pair = await auth.login({ email, password });
      onLand(pair);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        sessionStorage.setItem('_rv_pwd', password);
        router.push(`/verify/check?email=${encodeURIComponent(email)}&next=${encodeURIComponent(next)}`);
        return;
      }
      setStatus({ type: 'error', message: err instanceof Error ? err.message : 'Sign in failed' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthCard
      title="Welcome back, explorer."
      subtitle="Sign in to access your itineraries and concierge."
      footer={
        <p className="text-slate-500 font-medium">
          Don&apos;t have an account yet?{' '}
          <Link href="/signup" className="text-indigo-600 font-black hover:text-indigo-700 transition-colors">
            Sign Up
          </Link>
        </p>
      }
    >
      <StatusBanner status={status} />

      <OAuthButtons
        mode="sign_in"
        onSuccess={onLand}
        onError={(m) => setStatus({ type: 'error', message: m })}
      />

      <Divider label="or sign in with email" />

      <form onSubmit={onSubmit} className="space-y-4">
        <EmailField value={email} onChange={(e) => setEmail(e.target.value)} />
        <PasswordField value={password} onChange={(e) => setPassword(e.target.value)} />
        <div className="flex justify-end">
          <Link href="/forgot" className="text-sm font-bold text-indigo-600 hover:text-indigo-700">
            Forgot password?
          </Link>
        </div>
        <PrimaryButton loading={loading}>Sign In</PrimaryButton>
      </form>
    </AuthCard>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginInner />
    </Suspense>
  );
}
