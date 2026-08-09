import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated, Easing } from 'react-native';
import { colors, type } from '../theme';

interface LiveStatusProps {
  live: boolean; // true = actively connected (tokens cached), false = pending/attention state
  label: string;
}

// A gently pulsing dot is the one animation this app leans on repeatedly —
// it's how Garmin Connect/Apple Health signal "this number is current," and
// doing it once here (rather than a static dot) is what makes the sync state
// read as real-time instead of a screenshot.
export default function LiveStatus({ live, label }: LiveStatusProps) {
  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!live) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 0.35, duration: 900, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1, duration: 900, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [live, pulse]);

  return (
    <View style={styles.row}>
      <Animated.View
        style={[
          styles.dot,
          { backgroundColor: live ? colors.success : colors.warning, opacity: live ? pulse : 1 },
        ]}
      />
      <Text style={styles.label} numberOfLines={1}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 6, height: 6, borderRadius: 3 },
  label: { ...type.micro, color: colors.textSecondary, fontSize: 11 },
});
