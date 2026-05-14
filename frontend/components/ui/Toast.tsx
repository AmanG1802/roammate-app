'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { registerToastEmitter } from '@/lib/toast-bus';

export type ToastKind = 'error' | 'info' | 'success';

export interface ToastOptions {
  kind?: ToastKind;
  durationMs?: number;
  action?: { label: string; onClick: () => void };
}

interface ToastRecord {
  id: number;
  kind: ToastKind;
  message: string;
  action?: { label: string; onClick: () => void };
}

interface ToastContextValue {
  show: (message: string, options?: ToastOptions) => number;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let toastSeq = 1;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const show = useCallback(
    (message: string, options: ToastOptions = {}) => {
      const id = toastSeq++;
      const kind = options.kind ?? 'info';
      const duration = options.durationMs ?? (kind === 'error' ? 6000 : 4000);
      setToasts((prev) => [...prev, { id, kind, message, action: options.action }]);
      if (duration > 0) {
        const timer = setTimeout(() => dismiss(id), duration);
        timers.current.set(id, timer);
      }
      return id;
    },
    [dismiss],
  );

  useEffect(() => {
    const captured = timers.current;
    return () => {
      captured.forEach((t) => clearTimeout(t));
      captured.clear();
    };
  }, []);

  useEffect(() => {
    registerToastEmitter((message, options) => {
      show(message, options);
    });
    return () => registerToastEmitter(null);
  }, [show]);

  const value = useMemo(() => ({ show, dismiss }), [show, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <Toaster toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return ctx;
}

const PALETTE: Record<ToastKind, { wrap: string; icon: React.ReactNode }> = {
  error: {
    wrap: 'bg-rose-50 border-rose-200 text-rose-700',
    icon: <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />,
  },
  info: {
    wrap: 'bg-slate-50 border-slate-200 text-slate-700',
    icon: <Info className="w-4 h-4 mt-0.5 shrink-0" />,
  },
  success: {
    wrap: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    icon: <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />,
  },
};

function Toaster({
  toasts,
  onDismiss,
}: {
  toasts: ToastRecord[];
  onDismiss: (id: number) => void;
}) {
  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="pointer-events-none fixed inset-x-0 top-4 z-[100] flex flex-col items-center gap-2 px-4 sm:top-6"
    >
      <AnimatePresence initial={false}>
        {toasts.map((t) => {
          const palette = PALETTE[t.kind];
          return (
            <motion.div
              key={t.id}
              role={t.kind === 'error' ? 'alert' : 'status'}
              initial={{ opacity: 0, y: -16, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.98 }}
              transition={{ duration: 0.18 }}
              className={`pointer-events-auto flex w-full max-w-md items-start gap-2 rounded-xl border px-4 py-3 shadow-lg backdrop-blur ${palette.wrap}`}
            >
              {palette.icon}
              <p className="flex-1 text-xs font-bold leading-relaxed">{t.message}</p>
              {t.action && (
                <button
                  onClick={() => {
                    t.action!.onClick();
                    onDismiss(t.id);
                  }}
                  className="text-[10px] font-black uppercase tracking-widest underline-offset-2 hover:underline"
                >
                  {t.action.label}
                </button>
              )}
              <button
                onClick={() => onDismiss(t.id)}
                aria-label="Dismiss notification"
                className="opacity-60 transition-opacity hover:opacity-100"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
