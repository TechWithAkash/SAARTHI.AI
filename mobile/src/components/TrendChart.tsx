import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { colors, type } from '../theme';

const screenWidth = Dimensions.get('window').width;

interface TrendChartProps {
  title?: string;
  labels: string[];
  data: number[];
  color: string; // "R, G, B" — interpolated into rgba() at various opacities
  unit?: string;
  height?: number;
  widthOffset?: number; // total horizontal space to subtract (card padding etc.)
}

// A day with no real reading for this metric is simply absent from `data` —
// react-native-chart-kit connects straight across the gap rather than
// dropping to zero, which reads as "no signal" instead of fabricating a flat
// line at zero for a day nothing was actually measured.
export default function TrendChart({ title, labels, data, color, unit, height = 148, widthOffset = 64 }: TrendChartProps) {
  if (data.length < 2) {
    return (
      <View style={styles.emptyWrap}>
        <Text style={styles.emptyText}>Not enough readings yet to chart a trend.</Text>
      </View>
    );
  }

  return (
    <View>
      {title && (
        <View style={styles.headerRow}>
          <Text style={styles.title}>{title}</Text>
          {unit && <Text style={styles.unitTag}>{unit}</Text>}
        </View>
      )}
      <LineChart
        data={{ labels, datasets: [{ data }] }}
        width={screenWidth - widthOffset}
        height={height}
        withInnerLines
        withOuterLines={false}
        chartConfig={{
          backgroundColor: colors.surface,
          backgroundGradientFrom: colors.surface,
          backgroundGradientTo: colors.surface,
          decimalPlaces: 0,
          color: (opacity = 1) => `rgba(${color}, ${opacity})`,
          labelColor: (opacity = 1) => `rgba(148, 163, 184, ${opacity})`,
          style: { borderRadius: 12 },
          propsForDots: { r: '2.5', strokeWidth: '2', stroke: `rgb(${color})` },
          propsForBackgroundLines: { stroke: colors.border },
        }}
        bezier
        style={styles.chart}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  title: { ...type.caption, fontSize: 12.5 },
  unitTag: { ...type.micro, fontSize: 10.5 },
  chart: { borderRadius: 12, marginLeft: -16 },
  emptyWrap: { paddingVertical: 24, alignItems: 'center' },
  emptyText: { ...type.caption, color: colors.textTertiary, fontSize: 11.5 },
});
