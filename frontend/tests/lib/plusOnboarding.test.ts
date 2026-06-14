import { describe, it, expect } from 'vitest';
import {
  hasSeenPlusOnboarding,
  markPlusOnboardingSeen,
  clearPlusOnboardingSeen,
  currentUserIdFromCache,
} from '@/lib/plusOnboarding';

describe('plus onboarding "seen" flag', () => {
  it('reports not-seen by default', () => {
    expect(hasSeenPlusOnboarding(7)).toBe(false);
  });

  it('reports seen after marking', () => {
    markPlusOnboardingSeen(7);
    expect(hasSeenPlusOnboarding(7)).toBe(true);
  });

  it('scopes the flag per user id', () => {
    markPlusOnboardingSeen(7);
    expect(hasSeenPlusOnboarding(7)).toBe(true);
    expect(hasSeenPlusOnboarding(8)).toBe(false);
  });

  it('clears the flag', () => {
    markPlusOnboardingSeen(7);
    clearPlusOnboardingSeen(7);
    expect(hasSeenPlusOnboarding(7)).toBe(false);
  });

  it('treats string and number ids consistently', () => {
    markPlusOnboardingSeen('42');
    expect(hasSeenPlusOnboarding(42)).toBe(true);
  });
});

describe('currentUserIdFromCache', () => {
  it('returns null when no user is cached', () => {
    expect(currentUserIdFromCache()).toBeNull();
  });

  it('reads the id from the cached user object', () => {
    localStorage.setItem('user', JSON.stringify({ id: 99, email: 'a@b.com' }));
    expect(currentUserIdFromCache()).toBe(99);
  });

  it('returns null for malformed JSON', () => {
    localStorage.setItem('user', '{not json');
    expect(currentUserIdFromCache()).toBeNull();
  });

  it('returns null when the cached object has no id', () => {
    localStorage.setItem('user', JSON.stringify({ email: 'a@b.com' }));
    expect(currentUserIdFromCache()).toBeNull();
  });
});
