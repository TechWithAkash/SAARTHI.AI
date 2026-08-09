import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { colors, radius, type } from '../theme';

interface SegmentedControlProps<T extends string> {
  options: readonly T[];
  value: T;
  onChange: (v: T) => void;
  scrollable?: boolean;
}

export default function SegmentedControl<T extends string>({ options, value, onChange, scrollable }: SegmentedControlProps<T>) {
  const content = (
    <View style={styles.track}>
      {options.map((opt) => {
        const active = opt === value;
        return (
          <TouchableOpacity
            key={opt}
            onPress={() => onChange(opt)}
            style={[styles.segment, active && styles.segmentActive]}
            hitSlop={{ top: 6, bottom: 6 }}
          >
            <Text style={[styles.segmentText, active && styles.segmentTextActive]} numberOfLines={1}>
              {opt}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );

  if (scrollable) {
    return (
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ flexGrow: 1 }}>
        {content}
      </ScrollView>
    );
  }
  return content;
}

const styles = StyleSheet.create({
  track: { flexDirection: 'row', backgroundColor: colors.surfaceAlt, borderRadius: radius.md, padding: 3, gap: 2 },
  segment: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: radius.sm },
  segmentActive: { backgroundColor: colors.surface, shadowColor: '#0F172A', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.08, shadowRadius: 3, elevation: 1 },
  segmentText: { ...type.caption, fontSize: 12.5, color: colors.textTertiary, fontWeight: '700' },
  segmentTextActive: { color: colors.primary },
});
