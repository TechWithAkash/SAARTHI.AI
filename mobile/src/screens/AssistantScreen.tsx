import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView,
  KeyboardAvoidingView, Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useBottomTabBarHeight } from '@react-navigation/bottom-tabs';
import { streamChat, type ChatMessage } from '../services/api';
import TypingDots from '../components/TypingDots';
import FormattedMessage from '../components/FormattedMessage';
import { colors, radius, spacing, type } from '../theme';

const DEFAULT_USER = 'user_demo_001';

const STARTER_CHIPS = [
  "What's driving my risk score?",
  'How did my sleep trend this week?',
  'Is my resting heart rate normal?',
  'What should I improve first?',
];

interface DisplayMessage extends ChatMessage {
  id: string;
  streaming?: boolean;
}

export default function AssistantScreen() {
  const tabBarHeight = useBottomTabBarHeight();
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [chips, setChips] = useState<string[]>(STARTER_CHIPS);
  const scrollRef = useRef<ScrollView>(null);
  const abortRef = useRef<(() => void) | null>(null);

  useEffect(() => () => abortRef.current?.(), []);

  const send = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;

    const history = messages.map(({ role, content }) => ({ role, content }));
    const userMsg: DisplayMessage = { id: `u-${Date.now()}`, role: 'user', content: trimmed };
    const assistantId = `a-${Date.now()}`;
    setMessages((prev) => [...prev, userMsg, { id: assistantId, role: 'assistant', content: '', streaming: true }]);
    setInput('');
    setChips([]);
    setBusy(true);

    abortRef.current = streamChat(
      DEFAULT_USER,
      trimmed,
      history,
      {
        onToken: (delta) => {
          setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + delta } : m)));
        },
        onDone: (newChips) => {
          setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, streaming: false } : m)));
          setChips(newChips && newChips.length > 0 ? newChips : STARTER_CHIPS);
          setBusy(false);
        },
        onError: (message) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: m.content || `⚠️ ${message}`, streaming: false } : m))
          );
          setBusy(false);
        },
      }
    );
  };

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
      <View style={styles.header}>
        <View style={styles.aiIcon}>
          <Ionicons name="sparkles" size={14} color={colors.primary} />
        </View>
        <View>
          <Text style={styles.title}>Health Assistant</Text>
          <Text style={styles.subtitle}>AI-generated · grounded in your synced data</Text>
        </View>
      </View>

      <ScrollView
        ref={scrollRef}
        style={styles.flex}
        contentContainerStyle={styles.messagesContent}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.length === 0 && (
          <View style={styles.emptyState}>
            <Ionicons name="chatbubble-ellipses-outline" size={26} color={colors.textTertiary} />
            <Text style={styles.emptyText}>
              Ask about your risk score, Garmin trends, or what to do next — answers use your actual synced data.
            </Text>
          </View>
        )}

        {messages.map((m) => (
          <View key={m.id} style={[styles.bubbleRow, m.role === 'user' ? styles.bubbleRowUser : styles.bubbleRowAssistant]}>
            <View style={[styles.bubble, m.role === 'user' ? styles.bubbleUser : styles.bubbleAssistant]}>
              {m.role === 'assistant' && m.content === '' && m.streaming ? (
                <TypingDots />
              ) : m.role === 'assistant' ? (
                <>
                  <FormattedMessage text={m.content} />
                  {m.streaming && <Text style={styles.cursor}> ▍</Text>}
                </>
              ) : (
                <Text style={[styles.bubbleText, styles.bubbleTextUser]}>{m.content}</Text>
              )}
            </View>
          </View>
        ))}
      </ScrollView>

      {chips.length > 0 && !busy && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipsRow} contentContainerStyle={styles.chipsContent}>
          {chips.map((chip, i) => (
            <TouchableOpacity key={i} style={styles.chip} onPress={() => send(chip)} activeOpacity={0.7}>
              <Text style={styles.chipText}>{chip}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      <View style={[styles.inputBar, { paddingBottom: tabBarHeight + spacing.sm }]}>
        <TextInput
          style={styles.input}
          placeholder="Ask about your health data…"
          placeholderTextColor={colors.textTertiary}
          value={input}
          onChangeText={setInput}
          editable={!busy}
          multiline
          maxLength={500}
        />
        <TouchableOpacity style={[styles.sendBtn, (busy || !input.trim()) && styles.sendBtnDisabled]} onPress={() => send(input)} disabled={busy || !input.trim()}>
          {busy ? <TypingDots color="#ffffff" /> : <Ionicons name="arrow-up" size={17} color="#ffffff" />}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  header: { flexDirection: 'row', alignItems: 'center', gap: 9, paddingTop: 54, paddingHorizontal: spacing.lg, paddingBottom: spacing.md, backgroundColor: colors.bg, borderBottomWidth: 1, borderBottomColor: colors.border },
  aiIcon: { width: 30, height: 30, borderRadius: 10, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 15, fontWeight: '900', color: colors.textPrimary },
  subtitle: { fontSize: 10.5, color: colors.textTertiary, fontWeight: '600', marginTop: 1 },
  messagesContent: { padding: spacing.lg, paddingBottom: 12, flexGrow: 1 },
  emptyState: { alignItems: 'center', justifyContent: 'center', flex: 1, gap: 10, paddingHorizontal: 30, paddingTop: 50 },
  emptyText: { textAlign: 'center', color: colors.textTertiary, fontSize: 12.5, lineHeight: 18 },
  bubbleRow: { flexDirection: 'row', marginBottom: 10 },
  bubbleRowUser: { justifyContent: 'flex-end' },
  bubbleRowAssistant: { justifyContent: 'flex-start' },
  bubble: { maxWidth: '84%', borderRadius: radius.lg, paddingHorizontal: 13, paddingVertical: 9 },
  bubbleUser: { backgroundColor: colors.primary, borderBottomRightRadius: 4 },
  bubbleAssistant: { backgroundColor: colors.surface, borderBottomLeftRadius: 4, borderWidth: 1, borderColor: colors.border },
  bubbleText: { fontSize: 13.5, lineHeight: 19, color: colors.textPrimary },
  cursor: { color: colors.primary, fontWeight: '700' },
  bubbleTextUser: { color: '#ffffff' },
  chipsRow: { maxHeight: 40 },
  chipsContent: { gap: 7, paddingHorizontal: spacing.lg, paddingBottom: 6 },
  chip: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.pill, paddingHorizontal: 12, paddingVertical: 7 },
  chipText: { fontSize: 11.5, fontWeight: '600', color: colors.textSecondary },
  inputBar: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, padding: spacing.lg, backgroundColor: colors.bg, borderTopWidth: 1, borderTopColor: colors.border },
  input: { flex: 1, backgroundColor: colors.surface, borderRadius: radius.lg, paddingHorizontal: 14, paddingVertical: 9, fontSize: 13.5, color: colors.textPrimary, maxHeight: 90, borderWidth: 1, borderColor: colors.border },
  sendBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  sendBtnDisabled: { backgroundColor: '#CBD5E1' },
});
