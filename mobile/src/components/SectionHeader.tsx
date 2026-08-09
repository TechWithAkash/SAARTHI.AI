import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface SectionHeaderProps {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle?: string;
  tint?: string;
}

// Consistent section framing used across screens so "this is raw device
// data" vs "this is a trend over time" vs "this is AI-generated" always
// reads the same way, instead of every card looking like every other card.
export default function SectionHeader({ icon, title, subtitle, tint = '#2563EB' }: SectionHeaderProps) {
  return (
    <View style={styles.row}>
      <View style={[styles.iconWrap, { backgroundColor: `${tint}14` }]}>
        <Ionicons name={icon} size={14} color={tint} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.title}>{title}</Text>
        {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 14 },
  iconWrap: { width: 26, height: 26, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 12, fontWeight: '900', color: '#111827', letterSpacing: 0.8, textTransform: 'uppercase' },
  subtitle: { fontSize: 11, color: '#9CA3AF', marginTop: 1 },
});
