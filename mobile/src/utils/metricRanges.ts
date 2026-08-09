// Status bands used to color-code each metric card. These are well-known,
// generic wellness reference ranges (CDC/WHO sleep & steps guidance, standard
// resting-HR and SpO2 bands, Garmin's own published Body Battery/Stress
// bands) — general context for an average adult, not a diagnosis and not
// specific to any one user. The *values* themselves always come straight
// from the synced Garmin data; nothing here invents a number, it only labels
// one that's already real.
export type MetricStatus = 'good' | 'normal' | 'caution' | 'low' | 'high' | 'neutral';

export interface StatusStyle {
  label: string;
  color: string;
  bg: string;
}

export const STATUS_STYLES: Record<MetricStatus, StatusStyle> = {
  good: { label: 'Good', color: '#15803D', bg: '#ECFDF5' },
  normal: { label: 'Normal', color: '#15803D', bg: '#ECFDF5' },
  caution: { label: 'Caution', color: '#B45309', bg: '#FFFBEB' },
  low: { label: 'Low', color: '#B45309', bg: '#FFFBEB' },
  high: { label: 'High', color: '#C2410C', bg: '#FFF7ED' },
  neutral: { label: '—', color: '#6B7280', bg: '#F3F4F6' },
};

export function restingHeartRateStatus(bpm: number): MetricStatus {
  if (bpm < 50) return 'neutral'; // athletic range — not a concern, but not a generic "good" claim either
  if (bpm <= 100) return 'normal';
  return 'high';
}

export function stepsStatus(steps: number): MetricStatus {
  if (steps >= 10000) return 'good';
  if (steps >= 7500) return 'normal';
  if (steps >= 5000) return 'caution';
  return 'low';
}

export function sleepStatus(hours: number): MetricStatus {
  if (hours >= 7 && hours <= 9) return 'good';
  if (hours >= 6) return 'caution';
  return 'low';
}

// This app's stress field is normalized to 1-10 (see HealthDataInput), not
// Garmin's raw 0-100 scale — bands scaled down to match.
export function stressStatus(level: number): MetricStatus {
  if (level <= 3) return 'good';
  if (level <= 6) return 'caution';
  return 'high';
}

export function spo2Status(pct: number): MetricStatus {
  if (pct >= 95) return 'normal';
  return 'low';
}

export function respirationStatus(breathsPerMin: number): MetricStatus {
  if (breathsPerMin >= 12 && breathsPerMin <= 20) return 'normal';
  return 'caution';
}

export function bmiStatus(bmi: number): MetricStatus {
  if (bmi < 18.5) return 'caution';
  if (bmi < 25) return 'good';
  if (bmi < 30) return 'caution';
  return 'high';
}

export function bodyBatteryStatus(score: number): MetricStatus {
  if (score >= 76) return 'good';
  if (score >= 51) return 'normal';
  if (score >= 26) return 'caution';
  return 'low';
}
