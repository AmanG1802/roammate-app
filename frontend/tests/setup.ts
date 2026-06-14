import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { vi, beforeEach, afterEach } from 'vitest';

// Unmount React trees and clear jsdom between tests.
afterEach(() => {
  cleanup();
});

// ── matchMedia stub (not in jsdom) ────────────────────────────────────────────
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// ── ResizeObserver / IntersectionObserver stubs (not in jsdom) ────────────────
class MockObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  takeRecords = vi.fn(() => []);
}
vi.stubGlobal('ResizeObserver', MockObserver);
vi.stubGlobal('IntersectionObserver', MockObserver);

// ── scroll APIs (jsdom no-ops, but components call them) ───────────────────────
window.HTMLElement.prototype.scrollIntoView = vi.fn();
(window.HTMLElement.prototype as HTMLElement & { scrollTo: unknown }).scrollTo = vi.fn();
window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;

// ── localStorage stub (jsdom's implementation is incomplete in some versions) ─
const localStorageData: Record<string, string> = {};
const localStorageMock: Storage = {
  getItem: (key: string) => localStorageData[key] ?? null,
  setItem: (key: string, value: string) => { localStorageData[key] = String(value); },
  removeItem: (key: string) => { delete localStorageData[key]; },
  clear: () => { Object.keys(localStorageData).forEach((k) => delete localStorageData[k]); },
  get length() { return Object.keys(localStorageData).length; },
  key: (index: number) => Object.keys(localStorageData)[index] ?? null,
};
vi.stubGlobal('localStorage', localStorageMock);

// Reset localStorage before every test so tests don't bleed into each other.
beforeEach(() => {
  localStorageMock.clear();
});
