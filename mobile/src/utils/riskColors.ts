// Matches backend CATEGORY_THRESHOLDS exactly (ensemble_service.py):
// Low [0,20) / Moderate [20,40) / High [40,60) / Critical [60,100]
// Colors follow the Apple Health / Garmin convention: green=good,
// amber=caution, orange=elevated, red=urgent — never a flat "red means data
// exists" like the previous hardcoded badge did.
export interface RiskColors {
  text: string;
  bg: string;
  ring: string;
}

const CATEGORY_COLORS: Record<string, RiskColors> = {
  low: { text: '#15803D', bg: '#ECFDF5', ring: '#16A34A' },
  moderate: { text: '#B45309', bg: '#FFFBEB', ring: '#D97706' },
  high: { text: '#C2410C', bg: '#FFF7ED', ring: '#EA580C' },
  critical: { text: '#DC2626', bg: '#FEF2F2', ring: '#DC2626' },
};

const DEFAULT_COLORS: RiskColors = { text: '#6B7280', bg: '#F3F4F6', ring: '#9CA3AF' };

export function getRiskColors(category?: string | null): RiskColors {
  if (!category) return DEFAULT_COLORS;
  return CATEGORY_COLORS[category.toLowerCase()] ?? DEFAULT_COLORS;
}

// Per-disease rings use the same green/amber/orange/red bands as the overall
// category, just evaluated against that disease's own 0-100 score.
export function getScoreColor(score: number | null | undefined): string {
  if (score == null) return '#CBD5E1';
  if (score < 20) return '#16A34A';
  if (score < 40) return '#D97706';
  if (score < 60) return '#EA580C';
  return '#DC2626';
}
