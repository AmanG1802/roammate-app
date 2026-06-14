import { describe, it, expect } from 'vitest';
import { categoryAccent, categoryPinColor } from '@/lib/categoryColors';

describe('categoryAccent', () => {
  it('returns the slate default for null/undefined', () => {
    expect(categoryAccent(null).bar).toBe('bg-slate-300');
    expect(categoryAccent(undefined).dot).toBe('bg-slate-400');
  });

  it('returns the indigo fallback for an unknown category', () => {
    expect(categoryAccent('quantum-mechanics')).toEqual({
      bar: 'bg-indigo-400',
      badge: 'bg-indigo-50 text-indigo-600 border border-indigo-200',
      dot: 'bg-indigo-500',
    });
  });

  it('matches food/dining keywords (case-insensitive)', () => {
    expect(categoryAccent('Restaurant').bar).toBe('bg-amber-400');
    expect(categoryAccent('STREET FOOD').dot).toBe('bg-amber-500');
    expect(categoryAccent('café').bar).toBe('bg-amber-400');
  });

  it('matches culture & arts', () => {
    expect(categoryAccent('museum').bar).toBe('bg-violet-400');
    expect(categoryAccent('Art Gallery').bar).toBe('bg-violet-400');
  });

  it('matches nature & outdoors', () => {
    expect(categoryAccent('National Park').bar).toBe('bg-emerald-400');
    expect(categoryAccent('beach').bar).toBe('bg-emerald-400');
  });

  it('returns a complete accent triple for every match', () => {
    const a = categoryAccent('hotel');
    expect(a).toHaveProperty('bar');
    expect(a).toHaveProperty('badge');
    expect(a).toHaveProperty('dot');
    expect(a.badge).toContain('border');
  });
});

describe('categoryPinColor', () => {
  it('returns the indigo default for null/unknown', () => {
    expect(categoryPinColor(null)).toBe('#4f46e5');
    expect(categoryPinColor('something-unmapped')).toBe('#4f46e5');
  });

  it.each([
    ['restaurant', '#f59e0b'],
    ['museum', '#8b5cf6'],
    ['hiking trail', '#10b981'],
    ['shopping mall', '#f43f5e'],
    ['hotel', '#3b82f6'],
    ['airport', '#64748b'],
  ])('maps %s to %s', (cat, hex) => {
    expect(categoryPinColor(cat)).toBe(hex);
  });

  it('is case-insensitive', () => {
    expect(categoryPinColor('MUSEUM')).toBe('#8b5cf6');
  });

  it('always returns a valid hex color', () => {
    for (const c of ['food', 'temple', 'nightclub', 'spa', 'unknown', null]) {
      expect(categoryPinColor(c)).toMatch(/^#[0-9a-f]{6}$/);
    }
  });
});
