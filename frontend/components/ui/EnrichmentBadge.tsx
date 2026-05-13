'use client';

import { useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { AlertTriangle, RotateCcw, Loader2 } from 'lucide-react';

interface EnrichmentBadgeProps {
  size?: number;
  onRetry?: () => void;
  retrying?: boolean;
}

export default function EnrichmentBadge({ size = 3, onRetry, retrying = false }: EnrichmentBadgeProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const [visible, setVisible] = useState(false);
  const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback(() => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setVisible(true);
  }, []);

  const hide = useCallback(() => {
    hoverTimeout.current = setTimeout(() => setVisible(false), 120);
  }, []);

  const keepOpen = useCallback(() => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
  }, []);

  const sizeClass = size === 3 ? 'w-3 h-3' : 'w-3.5 h-3.5';

  const rect = visible && ref.current ? ref.current.getBoundingClientRect() : null;

  return (
    <>
      <span
        ref={ref}
        onMouseEnter={show}
        onMouseLeave={hide}
        className="shrink-0 inline-flex items-center"
      >
        <AlertTriangle className={`${sizeClass} text-amber-500`} />
      </span>
      {rect &&
        createPortal(
          <div
            style={{ left: rect.left + rect.width / 2, top: rect.top }}
            className="fixed z-[9999] -translate-x-1/2 -translate-y-full"
            onMouseEnter={keepOpen}
            onMouseLeave={hide}
          >
            <div className="mb-1 flex items-center gap-1.5 px-2 py-1 rounded-lg bg-amber-50 border border-amber-200 shadow-md shadow-amber-100/40">
              <span className="text-[10px] font-bold text-amber-700 whitespace-nowrap">
                Map data unavailable
              </span>
              {onRetry && (
                <button
                  onClick={(e) => { e.stopPropagation(); onRetry(); }}
                  disabled={retrying}
                  className="p-0.5 rounded-md text-amber-600 hover:bg-amber-100 disabled:opacity-50 transition-colors cursor-pointer"
                  title="Retry enrichment"
                >
                  {retrying
                    ? <Loader2 className="w-3 h-3 animate-spin" />
                    : <RotateCcw className="w-3 h-3" />}
                </button>
              )}
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
