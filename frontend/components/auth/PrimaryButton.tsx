import { ArrowRight, Loader2 } from 'lucide-react';

export function PrimaryButton({
  loading,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean }) {
  return (
    <button
      type="submit"
      disabled={loading || props.disabled}
      {...props}
      className="w-full flex items-center justify-center gap-2 py-4 bg-indigo-600 text-white rounded-2xl font-black text-lg hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-100 disabled:opacity-50"
    >
      {loading ? (
        <Loader2 className="w-6 h-6 animate-spin" />
      ) : (
        <>
          {children}
          <ArrowRight className="w-5 h-5" />
        </>
      )}
    </button>
  );
}

export function Divider({ label = 'or continue with' }: { label?: string }) {
  return (
    <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-[0.2em] font-bold text-slate-400">
      <div className="flex-1 h-px bg-slate-200" />
      {label}
      <div className="flex-1 h-px bg-slate-200" />
    </div>
  );
}
