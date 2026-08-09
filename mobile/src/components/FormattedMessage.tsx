import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme';

// The backend's chat system prompt explicitly tells the model to "use
// markdown for structure — bold, bullet points" (chat_service.py), the same
// instruction the web app's chat page follows — but a bare RN <Text> just
// prints "**bmi**" and "* item" literally instead of rendering them, which
// is exactly the wall-of-asterisks the assistant was producing. This is the
// mobile equivalent of the web app's own hand-rolled MarkdownText/renderInline
// (chat/page.tsx) — same idea, not a markdown library, since responses arrive
// token-by-token and get re-rendered on every chunk. Widened bullet detection
// to "*", "-", *and* "•" (the web version only catches "-"/"•"), since the
// model's real output uses plain "* " bullets, which the web page's own
// narrower check would silently leave un-rendered too.
function renderInline(text: string, keyPrefix: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+?\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? (
      <Text key={`${keyPrefix}-${i}`} style={styles.bold}>{part.slice(2, -2)}</Text>
    ) : (
      part
    )
  );
}

export default function FormattedMessage({ text, color = colors.textPrimary }: { text: string; color?: string }) {
  if (!text) return null;
  const lines = text.split('\n');

  return (
    <View>
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <View key={i} style={styles.spacer} />;

        const bulletMatch = trimmed.match(/^([*\-•])\s+(.*)/);
        if (bulletMatch) {
          return (
            <View key={i} style={styles.bulletRow}>
              <View style={[styles.bulletDot, { backgroundColor: color, opacity: 0.4 }]} />
              <Text style={[styles.text, { color }]}>{renderInline(bulletMatch[2], String(i))}</Text>
            </View>
          );
        }

        if (trimmed.startsWith('_') && trimmed.endsWith('_') && trimmed.length > 2) {
          return (
            <Text key={i} style={[styles.caption, { color }]}>{trimmed.slice(1, -1)}</Text>
          );
        }

        return (
          <Text key={i} style={[styles.text, { color }]}>{renderInline(trimmed, String(i))}</Text>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  text: { fontSize: 13.5, lineHeight: 19, marginBottom: 3 },
  bold: { fontWeight: '800' },
  spacer: { height: 6 },
  bulletRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 4 },
  bulletDot: { width: 4, height: 4, borderRadius: 2, marginTop: 7 },
  caption: { fontSize: 11.5, fontStyle: 'italic', opacity: 0.7, marginBottom: 3 },
});
