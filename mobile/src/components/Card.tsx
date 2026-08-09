import React from 'react';
import { View, StyleProp, ViewStyle, StyleSheet } from 'react-native';
import { colors, radius, spacing } from '../theme';

interface CardProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  tight?: boolean; // smaller padding for dense/secondary cards
}

// One card treatment everywhere: flat surface + hairline border + a very
// subtle shadow, not the heavy drop-shadow "floating tile" look the previous
// design used on every single card, which is what made the screen feel
// oversized and fragmented rather than like one continuous surface.
export default function Card({ children, style, tight }: CardProps) {
  return <View style={[styles.card, tight && styles.cardTight, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
  },
  cardTight: { padding: spacing.md },
});
