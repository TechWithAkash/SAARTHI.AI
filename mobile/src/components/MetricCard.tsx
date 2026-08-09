import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { STATUS_STYLES, type MetricStatus } from '../utils/metricRanges';

interface MetricCardProps {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: number | string;
  unit?: string;
  status?: MetricStatus;
  iconColor?: string;
  notMeasured?: boolean; // when true, shows an honest "not tracked today" state instead of a value
}

export default function MetricCard({
  icon,
  label,
  value,
  unit,
  status = 'neutral',
  iconColor = '#2563EB',
  notMeasured = false,
}: MetricCardProps) {
  const style = STATUS_STYLES[status];

  return (
    <View style={styles.card}>
      <View style={styles.topRow}>
        <View style={[styles.iconWrap, { backgroundColor: `${iconColor}14` }]}>
          <Ionicons name={icon} size={16} color={iconColor} />
        </View>
        {!notMeasured && status !== 'neutral' && (
          <View style={[styles.pill, { backgroundColor: style.bg }]}>
            <Text style={[styles.pillText, { color: style.color }]}>{style.label}</Text>
          </View>
        )}
      </View>

      {notMeasured ? (
        <>
          <Text style={styles.dash}>—</Text>
          <Text style={styles.notMeasuredText}>Not tracked today</Text>
        </>
      ) : (
        <Text style={styles.value} numberOfLines={1} adjustsFontSizeToFit>
          {value}
          {unit ? <Text style={styles.unit}> {unit}</Text> : null}
        </Text>
      )}
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexBasis: '48%',
    backgroundColor: '#ffffff',
    borderRadius: 20,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.04,
    shadowRadius: 10,
    elevation: 2,
  },
  topRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  iconWrap: { width: 30, height: 30, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
  pill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  pillText: { fontSize: 9, fontWeight: '800', letterSpacing: 0.3 },
  value: { fontSize: 22, fontWeight: '900', color: '#111827' },
  unit: { fontSize: 12, fontWeight: '700', color: '#9CA3AF' },
  dash: { fontSize: 22, fontWeight: '900', color: '#D1D5DB' },
  notMeasuredText: { fontSize: 10, color: '#B0B7C3', fontWeight: '600', marginTop: 2 },
  label: { fontSize: 11, fontWeight: '700', color: '#6B7280', marginTop: 6 },
});
