/**
 * Helpers for the "Plus onboarding modal seen once" flag.
 *
 * Shown at most once per user per device. Cleared on logout and when a Plus
 * subscriber downgrades back to free, so they see the pitch again on their
 * next free visit.
 */

const KEY_PREFIX = 'plus_onboarding_shown_';

function keyFor(userId: string | number): string {
  return `${KEY_PREFIX}${userId}`;
}

export function hasSeenPlusOnboarding(userId: string | number): boolean {
  if (typeof window === 'undefined') return true;
  return localStorage.getItem(keyFor(userId)) !== null;
}

export function markPlusOnboardingSeen(userId: string | number): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(keyFor(userId), '1');
}

export function clearPlusOnboardingSeen(userId: string | number): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(keyFor(userId));
}

/** Read current user id from the cached user object, if any. */
export function currentUserIdFromCache(): string | number | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem('user');
    if (!raw) return null;
    const u = JSON.parse(raw);
    return u?.id ?? null;
  } catch {
    return null;
  }
}
