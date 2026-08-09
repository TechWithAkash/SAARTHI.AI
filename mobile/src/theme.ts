// Single source of truth for spacing, color, type, and shadow — every screen
// pulls from here instead of re-declaring its own numbers, which is what let
// the same "card" pattern drift into five slightly different paddings/radii
// across screens. Tokens are deliberately restrained (few sizes, few shadows)
// because a "premium" feel here comes from consistency, not decoration.

export const colors = {
  bg: '#F7F9FC',
  surface: '#FFFFFF',
  surfaceAlt: '#F1F5F9',
  border: '#EDF1F6',
  textPrimary: '#0F172A',
  textSecondary: '#64748B',
  textTertiary: '#98A2B3',

  primary: '#2563EB',
  primarySoft: '#EEF4FF',
  success: '#16A34A',
  successSoft: '#ECFDF5',
  warning: '#D97706',
  warningSoft: '#FFFBEB',
  elevated: '#EA580C',
  elevatedSoft: '#FFF3EA',
  danger: '#DC2626',
  dangerSoft: '#FEF2F2',
  purple: '#7C3AED',
  purpleSoft: '#F5F3FF',
  teal: '#0D9488',
  tealSoft: '#F0FDFA',
} as const;

// A fixed pastel assigned per metric (not rotated randomly) so "steps" is
// always the same sand tile and "heart rate" the same lavender one across
// the whole app — recognizable at a glance, the way Apple Health/Garmin
// Connect keep a metric's color constant everywhere it appears.
export const pastel = {
  steps: { bg: '#F6EAD4', fg: '#8A6A2F', icon: '#B4863A' },
  heartRate: { bg: '#EFE4FB', fg: '#5B3A99', icon: '#7C3AED' },
  sleep: { bg: '#DFF3E6', fg: '#1B7A43', icon: '#16A34A' },
  stress: { bg: '#FBE7DC', fg: '#B4531F', icon: '#EA580C' },
  info: { bg: '#DCEEFB', fg: '#1D5FA8', icon: '#2563EB' },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 28,
} as const;

export const radius = {
  sm: 10,
  md: 14,
  lg: 18,
  pill: 999,
} as const;

export const shadow = {
  card: {
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  raised: {
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.12,
    shadowRadius: 14,
    elevation: 5,
  },
} as const;

export const type = {
  display: { fontSize: 40, fontWeight: '900' as const, color: colors.textPrimary },
  h1: { fontSize: 20, fontWeight: '800' as const, color: colors.textPrimary },
  h2: { fontSize: 15, fontWeight: '800' as const, color: colors.textPrimary },
  eyebrow: { fontSize: 10.5, fontWeight: '800' as const, letterSpacing: 0.6, color: colors.textSecondary },
  body: { fontSize: 14, fontWeight: '500' as const, color: colors.textPrimary },
  bodyBold: { fontSize: 14, fontWeight: '700' as const, color: colors.textPrimary },
  caption: { fontSize: 12, fontWeight: '600' as const, color: colors.textSecondary },
  micro: { fontSize: 10, fontWeight: '700' as const, color: colors.textTertiary },
} as const;
