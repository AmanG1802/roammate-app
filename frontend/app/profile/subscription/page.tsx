import { CreditCard } from 'lucide-react';

export default function SubscriptionPage() {
  return (
    <div>
      <h1 className="text-2xl font-black text-slate-900 mb-6">Subscription</h1>
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 flex flex-col items-center gap-4 text-center max-w-md">
        <div className="w-14 h-14 rounded-2xl bg-indigo-50 flex items-center justify-center">
          <CreditCard className="w-7 h-7 text-indigo-400" />
        </div>
        <h2 className="text-lg font-black text-slate-800">Coming Soon</h2>
        <p className="text-sm text-slate-500">
          Subscription management and premium plans are on the way. Stay tuned!
        </p>
      </div>
    </div>
  );
}
