import type { HealthDay } from '../services/api';

export function shortDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}

export function relativeSync(iso: string | null | undefined): string {
  if (!iso) return 'Never synced';
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return 'Synced just now';
  if (mins < 60) return `Synced ${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `Synced ${hrs}h ago`;
  return `Synced ${Math.round(hrs / 24)}d ago`;
}

// Sleep (and several other metrics) are inherently retrospective — a device
// doesn't have "today's sleep" until tonight is over, so the most recent
// calendar row often genuinely has no reading for it yet. Rigidly reading
// only that last row makes real, recent data (e.g. two days old) look like
// it doesn't exist. Real wearable apps show the latest real reading with its
// own date instead — this walks backward until it finds one.
export function latestMeasured<T>(
  days: HealthDay[],
  extract: (d: HealthDay) => T | null | undefined,
  measured: (d: HealthDay) => boolean
): { value: T; date: string; isLatestDay: boolean } | null {
  for (let i = days.length - 1; i >= 0; i--) {
    if (measured(days[i])) {
      const v = extract(days[i]);
      if (v != null) return { value: v, date: days[i].date, isLatestDay: i === days.length - 1 };
    }
  }
  return null;
}
