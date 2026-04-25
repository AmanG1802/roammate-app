'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Mail, Lock, User, ArrowRight, Loader2, Sparkles } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isSignupParam = searchParams.get('signup') === 'true';

  const [isSignup, setIsSignup] = useState(isSignupParam);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');

  const API = process.env.NEXT_PUBLIC_API_URL ?? '';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const endpoint = isSignup ? '/users/register' : '/users/login';
      const body = isSignup ? { email, password, name } : { email, password };

      const response = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Authentication failed');

      if (isSignup) {
        setIsSignup(false);
        setError('Account created! Please sign in.');
        setPassword('');
      } else {
        localStorage.setItem('token', data.access_token);
        const userRes = await fetch(`${API}/users/me`, {
          headers: { Authorization: `Bearer ${data.access_token}` },
        });
        if (userRes.ok) {
          const userData = await userRes.json();
          localStorage.setItem('user', JSON.stringify(userData));
        }
        // Always go to dashboard — it handles the persona onboarding modal
        router.push('/dashboard');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-white">
      {/* Left Side: Auth Form */}
      <div className="flex-1 flex flex-col items-center justify-center px-8 md:px-20 lg:px-32">
        <div className="w-full max-w-md">
          <Link href="/" className="inline-flex items-center gap-2 mb-12">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center font-bold text-white text-lg">R</div>
            <span className="text-xl font-black text-slate-900 tracking-tight">Roammate</span>
          </Link>

          <h2 className="text-4xl font-black text-slate-900 mb-2 leading-tight">
            {isSignup ? 'Start your next adventure.' : 'Welcome back, explorer.'}
          </h2>
          <p className="text-slate-500 mb-10 font-medium">
            {isSignup ? 'Join thousands of travelers planning with AI.' : 'Sign in to access your itineraries and concierge.'}
          </p>

          {error && (
            <div className={`mb-6 p-4 rounded-2xl text-sm font-bold border ${
              error.startsWith('Account created')
                ? 'bg-green-50 border-green-100 text-green-700'
                : 'bg-rose-50 border-rose-100 text-rose-600'
            }`}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isSignup && (
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <User className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  type="text"
                  placeholder="Full Name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="block w-full pl-11 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all font-medium"
                />
              </div>
            )}
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Mail className="h-5 w-5 text-slate-400" />
              </div>
              <input
                type="email"
                placeholder="Email Address"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="block w-full pl-11 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all font-medium"
              />
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Lock className="h-5 w-5 text-slate-400" />
              </div>
              <input
                type="password"
                placeholder="Password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="block w-full pl-11 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all font-medium"
              />
            </div>
            {!isSignup && (
              <div className="flex justify-end">
                <button type="button" className="text-sm font-bold text-indigo-600 hover:text-indigo-700">Forgot password?</button>
              </div>
            )}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-4 bg-indigo-600 text-white rounded-2xl font-black text-lg hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-100 disabled:opacity-50"
            >
              {isLoading ? <Loader2 className="w-6 h-6 animate-spin" /> : (
                <>{isSignup ? 'Create Account' : 'Sign In'}<ArrowRight className="w-5 h-5" /></>
              )}
            </button>
          </form>

          <div className="mt-8 text-center">
            <p className="text-slate-500 font-medium">
              {isSignup ? 'Already have an account?' : "Don't have an account yet?"}{' '}
              <button
                type="button"
                onClick={() => setIsSignup(!isSignup)}
                className="text-indigo-600 font-black hover:text-indigo-700 transition-colors"
              >
                {isSignup ? 'Sign In' : 'Sign Up'}
              </button>
            </p>
          </div>
        </div>
      </div>

      {/* Right Side: Decorative */}
      <div className="hidden lg:flex flex-1 bg-indigo-600 items-center justify-center p-20 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-indigo-500 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />
        <div className="max-w-md relative">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500/50 text-white rounded-full text-xs font-black uppercase tracking-[0.2em] mb-8 border border-white/20">
            <Sparkles className="w-3 h-3" />
            Concierge Active
          </div>
          <h3 className="text-5xl font-black text-white mb-8 leading-tight italic tracking-tighter">
            &ldquo;The best way to see the world is with a plan that knows how to change.&rdquo;
          </h3>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-white/20 border border-white/30 flex items-center justify-center text-white font-bold">AG</div>
            <div>
              <p className="text-white font-black text-lg">Aman Gupta</p>
              <p className="text-indigo-200 font-bold text-sm uppercase tracking-widest">Co-Founder, Roammate</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
