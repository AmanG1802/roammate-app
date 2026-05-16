'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { auth, type TokenPair } from '@/lib/api';
import { setToken } from '@/lib/auth';
import { AuthCard, StatusBanner } from '@/components/auth/AuthCard';
import { EmailField, NameField, PasswordField } from '@/components/auth/Fields';
import { Divider, PrimaryButton } from '@/components/auth/PrimaryButton';
import { OAuthButtons } from '@/components/auth/OAuthButtons';

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: 'error' | 'success' | 'info'; message: string } | null>(null);

  const onLand = (pair: TokenPair) => {
    setToken(pair.access_token);
    if (typeof window !== 'undefined') localStorage.setItem('user', JSON.stringify(pair.user));
    router.push('/dashboard');
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus(null);
    setLoading(true);
    try {
      await auth.signup({ name, email, password });
      router.push(`/verify/check?email=${encodeURIComponent(email)}`);
    } catch (err) {
      setStatus({ type: 'error', message: err instanceof Error ? err.message : 'Sign up failed' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthCard
      title="Start your next adventure."
      subtitle="Join thousands of travelers planning with AI."
      footer={
        <p className="text-slate-500 font-medium">
          Already have an account?{' '}
          <Link href="/login" className="text-indigo-600 font-black hover:text-indigo-700 transition-colors">
            Sign In
          </Link>
        </p>
      }
    >
      <StatusBanner status={status} />

      <OAuthButtons
        mode="sign_up"
        onSuccess={onLand}
        onError={(m) => setStatus({ type: 'error', message: m })}
      />

      <Divider />

      <form onSubmit={onSubmit} className="space-y-4">
        <NameField value={name} onChange={(e) => setName(e.target.value)} />
        <EmailField value={email} onChange={(e) => setEmail(e.target.value)} />
        <PasswordField value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
        <PrimaryButton loading={loading}>Create Account</PrimaryButton>
      </form>
    </AuthCard>
  );
}
