/**
 * Wall-clock time-of-day helpers — the web counterpart to the iOS
 * `TimeOfDay` value type. After the backend schema split (see docs/[27]),
 * `Event.start_time`/`end_time` and `IdeaBinItem.start_time`/`end_time`
 * are TIME-only strings ("HH:MM:SS") in trip-local wall-clock. The
 * owning `day_date` and the trip's `timezone` are needed to recover an
 * absolute instant.
 *
 * Wire format: `"HH:MM:SS"` (no fractional seconds). Lexicographic sort
 * gives correct chronological order.
 */

/** A wall-clock time, no date, no tz. Always `"HH:MM:SS"` on the wire. */
export type TimeOfDay = string;

const TIME_RE = /^(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$/;

/** Parse `"HH:MM:SS"` or `"HH:MM"` → normalized `"HH:MM:SS"`, or null. */
export function parseTimeOfDay(raw: string | null | undefined): TimeOfDay | null {
  if (!raw) return null;
  const m = TIME_RE.exec(raw.trim());
  if (!m) return null;
  const h = Number(m[1]);
  const min = Number(m[2]);
  const s = m[3] ? Number(m[3]) : 0;
  if (h < 0 || h > 23 || min < 0 || min > 59 || s < 0 || s > 59) return null;
  return `${pad2(h)}:${pad2(min)}:${pad2(s)}`;
}

/** Format a TimeOfDay as `"h:mm AM/PM"` for display. */
export function formatTimeOfDay(tod: TimeOfDay | null | undefined): string {
  if (!tod) return '';
  const m = TIME_RE.exec(tod);
  if (!m) return tod;
  const h = Number(m[1]);
  const min = Number(m[2]);
  const suffix = h < 12 ? 'AM' : 'PM';
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${h12}:${pad2(min)} ${suffix}`;
}

/** Compare TimeOfDay strings — lexicographic order is correct. */
export function compareTimeOfDay(a: TimeOfDay | null, b: TimeOfDay | null): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;   // nulls sort last (TBD)
  if (b == null) return -1;
  return a < b ? -1 : a > b ? 1 : 0;
}

/**
 * Combine a `YYYY-MM-DD` calendar day with a TimeOfDay in *tzName* and
 * return an absolute instant. Used for "is this event happening right
 * now?" comparisons against `new Date()`.
 *
 * Falls back to UTC on unknown tz. Returns null if either input is missing
 * or malformed.
 */
export function combineInTz(
  dayDate: string | null | undefined,
  tod: TimeOfDay | null | undefined,
  tzName: string | null | undefined,
): Date | null {
  if (!dayDate || !tod) return null;
  const m = TIME_RE.exec(tod);
  if (!m) return null;
  const h = Number(m[1]);
  const min = Number(m[2]);
  const s = m[3] ? Number(m[3]) : 0;
  // Compute the UTC instant whose rendering in *tzName* matches (dayDate, tod).
  // Approach: form the naive local timestamp, then adjust by the tz's offset
  // at that instant. We use `Intl.DateTimeFormat` to read the offset.
  const tz = tzName || 'UTC';
  // Start with the wall-clock interpreted as UTC, then shift by the tz offset.
  const utcGuess = Date.UTC(
    Number(dayDate.slice(0, 4)),
    Number(dayDate.slice(5, 7)) - 1,
    Number(dayDate.slice(8, 10)),
    h, min, s,
  );
  if (Number.isNaN(utcGuess)) return null;
  const offsetMin = tzOffsetMinutes(new Date(utcGuess), tz);
  return new Date(utcGuess - offsetMin * 60_000);
}

/** Round-trip a Date back to a "HH:MM:SS" TimeOfDay using *tzName*. */
export function timeOfDayFromDate(
  date: Date,
  tzName: string | null | undefined,
): TimeOfDay {
  const fmt = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
    timeZone: tzName || 'UTC',
  });
  // en-GB with 2-digit + hour12=false gives "HH:MM:SS"
  return fmt.format(date);
}

// ── internals ──────────────────────────────────────────────────────────────

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

/** Minutes east of UTC for *tz* at *date*. e.g. +330 for IST, -300 for EST. */
function tzOffsetMinutes(date: Date, tz: string): number {
  // Intl gives us the wall-clock components in *tz* for the same instant.
  // Reconstruct UTC from those components, subtract original UTC → offset.
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).formatToParts(date);
  const get = (t: string) => Number(parts.find((p) => p.type === t)?.value);
  const localAsUtc = Date.UTC(
    get('year'), get('month') - 1, get('day'),
    get('hour') % 24, get('minute'), get('second'),
  );
  return Math.round((localAsUtc - date.getTime()) / 60_000);
}
