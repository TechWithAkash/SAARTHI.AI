import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Polyline } from 'react-native-svg';
import { colors, type } from '../theme';

interface SparklineProps {
  label: string;
  value: string; // pre-formatted current value, e.g. "72 bpm"
  data: number[]; // real measured points only, oldest→newest
  color: string;
  active?: boolean;
}

// A tiny shape-only trend, no axes/labels — this is what sits in the always-
// visible overview row so a real trend is visible without committing screen
// space to a full chart until the user taps in (progressive disclosure).
export default function Sparkline({ label, value, data, color, active }: SparklineProps) {
  const w = 72;
  const h = 28;
  const pad = 3;

  let points = '';
  if (data.length >= 2) {
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    points = data
      .map((v, i) => {
        const x = pad + (i / (data.length - 1)) * (w - pad * 2);
        const y = h - pad - ((v - min) / range) * (h - pad * 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }

  return (
    <View style={[styles.card, active && styles.cardActive]}>
      <Text style={styles.label} numberOfLines={1}>{label}</Text>
      <Text style={[styles.value, { color: colors.textPrimary }]} numberOfLines={1}>{value}</Text>
      {data.length >= 2 ? (
        <Svg width={w} height={h} style={styles.svg}>
          <Polyline points={points} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        </Svg>
      ) : (
        <View style={[styles.svg, { height: h, justifyContent: 'center' }]}>
          <Text style={styles.noData}>No trend yet</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { width: 104, backgroundColor: colors.surface, borderRadius: 14, padding: 10, borderWidth: 1, borderColor: colors.border },
  cardActive: { borderColor: colors.primary, borderWidth: 1.5, backgroundColor: colors.primarySoft },
  label: { ...type.micro, fontSize: 10.5, marginBottom: 2 },
  value: { fontSize: 14, fontWeight: '800', marginBottom: 6 },
  svg: { marginTop: 2 },
  noData: { fontSize: 9, color: colors.textTertiary },
});
