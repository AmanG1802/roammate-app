'use client';

import { useRef } from 'react';
import BrainstormChat from './BrainstormChat';
import BrainstormBin, { BrainstormBinHandle } from './BrainstormBin';

export default function BrainstormSection({ tripId }: { tripId: string | null }) {
  const binRef = useRef<BrainstormBinHandle>(null);

  if (!tripId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400 font-bold">
        Loading...
      </div>
    );
  }

  return (
    <div className="flex-1 grid grid-cols-1 md:grid-cols-2 overflow-hidden bg-slate-50">
      <div className="border-r border-slate-100 overflow-hidden">
        <BrainstormChat tripId={tripId} onItemsCreated={() => binRef.current?.refresh()} />
      </div>
      <div className="overflow-hidden">
        <BrainstormBin ref={binRef} tripId={tripId} />
      </div>
    </div>
  );
}
