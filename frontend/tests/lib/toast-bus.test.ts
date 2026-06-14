import { describe, it, expect, vi, afterEach } from 'vitest';
import { registerToastEmitter, toastBus } from '@/lib/toast-bus';

afterEach(() => {
  // Detach any emitter so suites don't leak into each other.
  registerToastEmitter(null);
});

describe('toast-bus', () => {
  it('does nothing when no emitter is registered', () => {
    expect(() => toastBus('hello')).not.toThrow();
  });

  it('forwards message and options to the registered emitter', () => {
    const emit = vi.fn();
    registerToastEmitter(emit);

    toastBus('Saved!', { kind: 'success', durationMs: 2000 });

    expect(emit).toHaveBeenCalledTimes(1);
    expect(emit).toHaveBeenCalledWith('Saved!', { kind: 'success', durationMs: 2000 });
  });

  it('stops forwarding after the emitter is detached', () => {
    const emit = vi.fn();
    registerToastEmitter(emit);
    registerToastEmitter(null);

    toastBus('ignored');

    expect(emit).not.toHaveBeenCalled();
  });

  it('uses the most recently registered emitter', () => {
    const first = vi.fn();
    const second = vi.fn();
    registerToastEmitter(first);
    registerToastEmitter(second);

    toastBus('hi');

    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledWith('hi', undefined);
  });
});
