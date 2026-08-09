import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { STATUS_STYLES, type MetricStatus } from '../utils/metricRanges';
import { colors, radius, type } from '../theme';

interface PastelTone {
  bg: string;
  fg: string;
  icon: string;
}

interface MetricCardProps {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: number | string;
  unit?: string;
  status?: MetricStatus;
  iconColor?: string;
  notMeasured?: boolean; // when true, shows an honest "not tracked yet" state instead of a value
  compact?: boolean;
  pastel?: PastelTone; // when set, the card becomes a flat pastel tile instead of a white bordered one
  asOf?: string; // set when the value shown isn't from today — e.g. "Aug 7" — never hide the fact it's not current
}

export default function MetricCard({
  icon,
  label,
  value,
  unit,
  status = 'neutral',
  iconColor = colors.primary,
  notMeasured = false,
  compact = false,
  pastel,
  asOf,
}: MetricCardProps) {
  const style = STATUS_STYLES[status];
  const isPastel = !!pastel;

  return (
    <View
      style={[
        styles.card,
        compact && styles.cardCompact,
        isPastel && { backgroundColor: pastel!.bg, borderWidth: 0 },
      ]}
    >
      <View style={styles.topRow}>
        <Text style={[styles.label, isPastel && { color: pastel!.fg, opacity: 0.75 }]} numberOfLines={1}>{label}</Text>
        <View style={[styles.iconWrap, { backgroundColor: isPastel ? 'rgba(255,255,255,0.55)' : `${iconColor}14` }]}>
          <Ionicons name={icon} size={13} color={isPastel ? pastel!.icon : iconColor} />
        </View>
      </View>

      {notMeasured ? (
        <>
          <Text style={[styles.dash, isPastel && { color: pastel!.fg, opacity: 0.35 }]}>—</Text>
          <Text style={[styles.notMeasuredText, isPastel && { color: pastel!.fg, opacity: 0.6 }]}>Not tracked yet</Text>
        </>
      ) : (
        <>
          <Text style={[styles.value, isPastel && { color: pastel!.fg }]} numberOfLines={1} adjustsFontSizeToFit>
            {value}
            {unit ? <Text style={[styles.unit, isPastel && { color: pastel!.fg, opacity: 0.6 }]}> {unit}</Text> : null}
          </Text>
          <View style={styles.bottomRow}>
            {!isPastel && status !== 'neutral' && (
              <View style={[styles.pill, { backgroundColor: style.bg }]}>
                <Text style={[styles.pillText, { color: style.color }]}>{style.label}</Text>
              </View>
            )}
            {asOf && (
              <Text style={[styles.asOf, isPastel && { color: pastel!.fg, opacity: 0.55 }]} numberOfLines={1}>
                as of {asOf}
              </Text>
            )}
          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexBasis: '48%',
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardCompact: { padding: 10, borderRadius: radius.md },
  topRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10, gap: 6 },
  iconWrap: { width: 24, height: 24, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  pill: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 7 },
  pillText: { fontSize: 8.5, fontWeight: '800', letterSpacing: 0.2 },
  value: { fontSize: 22, fontWeight: '900', color: colors.textPrimary },
  unit: { fontSize: 11, fontWeight: '700', color: colors.textTertiary },
  dash: { fontSize: 22, fontWeight: '900', color: '#D1D5DB' },
  notMeasuredText: { fontSize: 9.5, color: colors.textTertiary, fontWeight: '600', marginTop: 2 },
  label: { ...type.micro, fontSize: 10.5, color: colors.textSecondary, flexShrink: 1 },
  bottomRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 5 },
  asOf: { fontSize: 9.5, fontWeight: '600', color: colors.textTertiary },
});
