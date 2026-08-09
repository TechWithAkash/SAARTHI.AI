import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { LineChart } from 'react-native-chart-kit';

const screenWidth = Dimensions.get('window').width;

interface TrendChartProps {
  title: string;
  labels: string[];
  data: number[];
  color: string; // "R, G, B" — interpolated into rgba() at various opacities
  unit?: string;
  gapNote?: string; // shown when some days were skipped because nothing was measured
}

// A day with no real reading for this metric is simply absent from `data` —
// react-native-chart-kit connects straight across the gap rather than
// dropping to zero, which reads as "no signal" instead of fabricating a flat
// line at zero for a day nothing was actually measured.
export default function TrendChart({ title, labels, data, color, unit, gapNote }: TrendChartProps) {
  if (data.length < 2) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.emptyText}>Not enough readings yet to chart a trend.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>{title}</Text>
        {unit && <Text style={styles.unitTag}>{unit}</Text>}
      </View>
      <LineChart
        data={{ labels, datasets: [{ data }] }}
        width={screenWidth - 72}
        height={160}
        withInnerLines={true}
        withOuterLines={false}
        chartConfig={{
          backgroundColor: '#ffffff',
          backgroundGradientFrom: '#ffffff',
          backgroundGradientTo: '#ffffff',
          decimalPlaces: 0,
          color: (opacity = 1) => `rgba(${color}, ${opacity})`,
          labelColor: (opacity = 1) => `rgba(156, 163, 175, ${opacity})`,
          style: { borderRadius: 12 },
          propsForDots: { r: '3', strokeWidth: '2', stroke: `rgb(${color})` },
          propsForBackgroundLines: { stroke: '#F1F5F9' },
        }}
        bezier
        style={styles.chart}
      />
      {gapNote && <Text style={styles.gapNote}>{gapNote}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginBottom: 24 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  title: { fontSize: 13, fontWeight: '800', color: '#374151' },
  unitTag: { fontSize: 11, fontWeight: '700', color: '#9CA3AF' },
  chart: { borderRadius: 12, marginLeft: -16 },
  emptyText: { fontSize: 12, color: '#9CA3AF', paddingVertical: 20, textAlign: 'center' },
  gapNote: { fontSize: 10, color: '#B0B7C3', marginTop: 4, fontStyle: 'italic' },
});
