import { describe, it, expect } from 'vitest';
import {
  parseTimeOfDay,
  formatTimeOfDay,
  compareTimeOfDay,
  combineInTz,
  timeOfDayFromDate,
} from '@/lib/time';

describe('parseTimeOfDay', () => {
  it('normalizes HH:MM to HH:MM:SS', () => {
    expect(parseTimeOfDay('09:30')).toBe('09:30:00');
  });

  it('pads single-digit components', () => {
    expect(parseTimeOfDay('9:5:3')).toBe('09:05:03');
  });

  it('preserves a full HH:MM:SS', () => {
    expect(parseTimeOfDay('23:59:59')).toBe('23:59:59');
  });

  it('trims surrounding whitespace', () => {
    expect(parseTimeOfDay('  10:15  ')).toBe('10:15:00');
  });

  it.each([null, undefined, ''])('returns null for empty input %s', (v) => {
    expect(parseTimeOfDay(v)).toBeNull();
  });

  it.each(['25:00', '12:60', '10:00:61', 'not-a-time', '99'])(
    'returns null for out-of-range / malformed %s',
    (v) => {
      expect(parseTimeOfDay(v)).toBeNull();
    },
  );
});

describe('formatTimeOfDay', () => {
  it.each([
    ['00:00:00', '12:00 AM'],
    ['00:05:00', '12:05 AM'],
    ['09:30:00', '9:30 AM'],
    ['12:00:00', '12:00 PM'],
    ['12:30:00', '12:30 PM'],
    ['13:05:00', '1:05 PM'],
    ['23:59:00', '11:59 PM'],
  ])('formats %s as %s', (input, expected) => {
    expect(formatTimeOfDay(input)).toBe(expected);
  });

  it.each([null, undefined, ''])('returns empty string for %s', (v) => {
    expect(formatTimeOfDay(v)).toBe('');
  });

  it('passes through an unparseable value unchanged', () => {
    expect(formatTimeOfDay('garbage')).toBe('garbage');
  });
});

describe('compareTimeOfDay', () => {
  it('orders earlier before later', () => {
    expect(compareTimeOfDay('09:00:00', '14:00:00')).toBe(-1);
    expect(compareTimeOfDay('14:00:00', '09:00:00')).toBe(1);
  });

  it('returns 0 for equal times', () => {
    expect(compareTimeOfDay('10:00:00', '10:00:00')).toBe(0);
  });

  it('sorts nulls last', () => {
    expect(compareTimeOfDay(null, '10:00:00')).toBe(1);
    expect(compareTimeOfDay('10:00:00', null)).toBe(-1);
    expect(compareTimeOfDay(null, null)).toBe(0);
  });

  it('works as an Array.sort comparator with nulls', () => {
    const sorted = ['14:00:00', null, '09:00:00'].sort(compareTimeOfDay);
    expect(sorted).toEqual(['09:00:00', '14:00:00', null]);
  });
});

describe('combineInTz', () => {
  it('combines a UTC wall-clock into the matching instant', () => {
    const d = combineInTz('2026-06-14', '12:00:00', 'UTC');
    expect(d?.toISOString()).toBe('2026-06-14T12:00:00.000Z');
  });

  it('shifts a positive-offset zone (IST, +5:30) back to UTC', () => {
    const d = combineInTz('2026-06-14', '12:00:00', 'Asia/Kolkata');
    expect(d?.toISOString()).toBe('2026-06-14T06:30:00.000Z');
  });

  it('shifts a negative-offset zone (EDT, -4 in June) forward to UTC', () => {
    const d = combineInTz('2026-06-14', '12:00:00', 'America/New_York');
    expect(d?.toISOString()).toBe('2026-06-14T16:00:00.000Z');
  });

  it('falls back to UTC for an unknown/empty tz', () => {
    const d = combineInTz('2026-06-14', '08:00:00', null);
    expect(d?.toISOString()).toBe('2026-06-14T08:00:00.000Z');
  });

  it('returns null when day or time is missing', () => {
    expect(combineInTz(null, '12:00:00', 'UTC')).toBeNull();
    expect(combineInTz('2026-06-14', null, 'UTC')).toBeNull();
  });

  it('returns null for a malformed time', () => {
    expect(combineInTz('2026-06-14', 'nope', 'UTC')).toBeNull();
  });
});

describe('timeOfDayFromDate', () => {
  it('renders an instant as wall-clock in UTC', () => {
    expect(timeOfDayFromDate(new Date('2026-06-14T16:00:00Z'), 'UTC')).toBe('16:00:00');
  });

  it('renders an instant as wall-clock in a named zone', () => {
    expect(timeOfDayFromDate(new Date('2026-06-14T16:00:00Z'), 'America/New_York')).toBe('12:00:00');
  });

  it('round-trips with combineInTz', () => {
    const tz = 'Asia/Kolkata';
    const instant = combineInTz('2026-06-14', '14:25:00', tz)!;
    expect(timeOfDayFromDate(instant, tz)).toBe('14:25:00');
  });
});
