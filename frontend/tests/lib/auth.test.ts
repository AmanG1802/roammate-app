import { describe, it, expect } from 'vitest';
import { clearSession } from '@/lib/auth';

describe('clearSession', () => {
  it('removes the cached user from localStorage', () => {
    localStorage.setItem('user', JSON.stringify({ id: 1 }));
    expect(localStorage.getItem('user')).not.toBeNull();

    clearSession();

    expect(localStorage.getItem('user')).toBeNull();
  });

  it('is a no-op when no user is cached', () => {
    expect(() => clearSession()).not.toThrow();
    expect(localStorage.getItem('user')).toBeNull();
  });
});
