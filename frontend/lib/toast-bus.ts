import type { ToastKind } from '@/components/ui/Toast';

type Emit = (message: string, options?: { kind?: ToastKind; durationMs?: number }) => void;

let emit: Emit | null = null;

export function registerToastEmitter(fn: Emit | null) {
  emit = fn;
}

export function toastBus(message: string, options?: { kind?: ToastKind; durationMs?: number }) {
  emit?.(message, options);
}
