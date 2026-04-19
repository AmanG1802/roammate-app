'use client';

import { useRef } from 'react';
import BrainstormChat from './BrainstormChat';
import BrainstormBin, { BrainstormBinHandle } from './BrainstormBin';
import { Loader2 } from 'lucide-react';

export default function BrainstormSection({ tripId }: { tripId: string | null }) {
  const binRef = useRef<BrainstormBinHandle>(null);

  if (!tripId) {
    return (
      <div className="flex-1 flex items-center justify-center gap-2 text-slate-400">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-xs font-black uppercase tracking-widest">Loading…</span>
      </div>
    );
  }

  return (
    <div className="flex-1 grid grid-cols-1 md:grid-cols-2 overflow-hidden bg-white">
      <div className="border-r border-slate-100 overflow-hidden">
        <BrainstormChat tripId={tripId} onItemsCreated={() => binRef.current?.refresh()} />
      </div>
      <div className="overflow-hidden">
        <BrainstormBin ref={binRef} tripId={tripId} />
      </div>
    </div>
  );
}
