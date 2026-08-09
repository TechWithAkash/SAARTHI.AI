import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, type } from '../theme';

interface SectionHeaderProps {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle?: string;
  tint?: string;
  right?: React.ReactNode;
}

// Consistent section framing so "this is raw device data" vs "this is a
// trend" vs "this is AI-generated" always reads the same way across screens.
export default function SectionHeader({ icon, title, subtitle, tint = colors.primary, right }: SectionHeaderProps) {
  return (
    <View style={styles.row}>
      <View style={[styles.iconWrap, { backgroundColor: `${tint}14` }]}>
        <Ionicons name={icon} size={13} color={tint} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={type.eyebrow}>{title.toUpperCase()}</Text>
        {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
      </View>
      {right}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10 },
  iconWrap: { width: 22, height: 22, borderRadius: 7, alignItems: 'center', justifyContent: 'center' },
  subtitle: { fontSize: 10.5, color: colors.textTertiary, marginTop: 1, fontWeight: '600' },
});
