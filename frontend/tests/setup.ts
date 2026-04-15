import '@testing-library/jest-dom';
import { vi, beforeEach } from 'vitest';

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

// ── localStorage stub (jsdom's implementation is incomplete in some versions) ─
const localStorageData: Record<string, string> = {};
const localStorageMock: Storage = {
  getItem: (key: string) => localStorageData[key] ?? null,
  setItem: (key: string, value: string) => { localStorageData[key] = value; },
  removeItem: (key: string) => { delete localStorageData[key]; },
  clear: () => { Object.keys(localStorageData).forEach((k) => delete localStorageData[k]); },
  get length() { return Object.keys(localStorageData).length; },
  key: (index: number) => Object.keys(localStorageData)[index] ?? null,
};
vi.stubGlobal('localStorage', localStorageMock);

// Reset localStorage before every test so tests don't bleed into each other
beforeEach(() => {
  localStorageMock.clear();
});
