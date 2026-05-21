import Link from 'next/link';
import { Sparkles } from 'lucide-react';

export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-white">
      {/* Left: form */}
      <div className="flex-1 flex flex-col items-center justify-center px-8 md:px-20 lg:px-32 py-12">
        <div className="w-full max-w-md">
          <Link href="/" className="inline-flex items-center gap-2 mb-12">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center font-bold text-white text-lg">R</div>
            <span className="text-xl font-black text-slate-900 tracking-tight">Roammate</span>
          </Link>

          <h2 className="text-4xl font-black text-slate-900 mb-2 leading-tight">{title}</h2>
          {subtitle ? (
            <p className="text-slate-500 mb-10 font-medium">{subtitle}</p>
          ) : (
            <div className="mb-10" />
          )}

          {children}

          {footer ? <div className="mt-8 text-center">{footer}</div> : null}
        </div>
      </div>

      {/* Right: pitch panel */}
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
            <div className="w-12 h-12 rounded-full bg-white/20 border border-white/30 flex items-center justify-center text-white font-bold">R</div>
            <div>
              <p className="text-white font-black text-lg">Roammate</p>
              <p className="text-indigo-200 font-bold text-sm uppercase tracking-widest">Your AI Travel Concierge</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function StatusBanner({ status }: { status: { type: 'error' | 'success' | 'info'; message: string } | null }) {
  if (!status) return null;
  const cls =
    status.type === 'success'
      ? 'bg-green-50 border-green-100 text-green-700'
      : status.type === 'info'
      ? 'bg-indigo-50 border-indigo-100 text-indigo-700'
      : 'bg-rose-50 border-rose-100 text-rose-600';
  return (
    <div role={status.type === 'error' ? 'alert' : 'status'} className={`mb-6 p-4 rounded-2xl text-sm font-bold border ${cls}`}>
      {status.message}
    </div>
  );
}
