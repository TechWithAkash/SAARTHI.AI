import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { colors } from '../theme';

// Apple Health-style activity ring, repurposed to show a single disease risk
// percentage at a glance. Deliberately simple — one ring, one number, one
// label — over a dashboard of dense text, matching how Apple/Garmin surface
// glanceable health metrics.
interface RiskRingProps {
  label: string;
  value: number | null | undefined; // 0-100
  color: string;
  size?: number;
}

export default function RiskRing({ label, value, color, size = 64 }: RiskRingProps) {
  const strokeWidth = 6;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = value == null ? 0 : Math.max(0, Math.min(100, value));
  const dashOffset = circumference * (1 - pct / 100);

  return (
    <View style={styles.wrap}>
      <View style={{ width: size, height: size }}>
        <Svg width={size} height={size}>
          <Circle cx={size / 2} cy={size / 2} r={radius} stroke={colors.surfaceAlt} strokeWidth={strokeWidth} fill="none" />
          {value != null && (
            <Circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke={color}
              strokeWidth={strokeWidth}
              strokeDasharray={`${circumference} ${circumference}`}
              strokeDashoffset={dashOffset}
              strokeLinecap="round"
              fill="none"
              rotation={-90}
              origin={`${size / 2}, ${size / 2}`}
            />
          )}
        </Svg>
        <View style={StyleSheet.absoluteFill}>
          <View style={styles.centerLabel}>
            <Text style={[styles.value, { color: value == null ? '#CBD5E1' : colors.textPrimary }]}>
              {value == null ? '—' : Math.round(value)}
            </Text>
          </View>
        </View>
      </View>
      <Text style={styles.label} numberOfLines={1}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', flex: 1 },
  centerLabel: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  value: { fontSize: 15, fontWeight: '800' },
  label: { fontSize: 10.5, fontWeight: '700', color: colors.textSecondary, marginTop: 6, textAlign: 'center' },
});
