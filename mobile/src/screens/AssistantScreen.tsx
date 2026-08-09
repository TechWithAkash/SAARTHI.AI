import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView,
  KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { streamChat, type ChatMessage } from '../services/api';

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
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + delta } : m))
          );
        },
        onDone: (newChips) => {
          setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, streaming: false } : m)));
          setChips(newChips && newChips.length > 0 ? newChips : STARTER_CHIPS);
          setBusy(false);
        },
        onError: (message) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content || `⚠️ ${message}`, streaming: false }
                : m
            )
          );
          setBusy(false);
        },
      }
    );
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <View style={styles.aiIcon}>
            <Ionicons name="sparkles" size={16} color="#2563EB" />
          </View>
          <View>
            <Text style={styles.title}>Health Assistant</Text>
            <Text style={styles.subtitle}>AI-generated · grounded in your synced data</Text>
          </View>
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
            <Ionicons name="chatbubble-ellipses-outline" size={30} color="#CBD5E1" />
            <Text style={styles.emptyText}>
              Ask anything about your risk score, Garmin trends, or what to do next — answers use your
              actual synced data, not generic advice.
            </Text>
          </View>
        )}

        {messages.map((m) => (
          <View
            key={m.id}
            style={[styles.bubbleRow, m.role === 'user' ? styles.bubbleRowUser : styles.bubbleRowAssistant]}
          >
            <View style={[styles.bubble, m.role === 'user' ? styles.bubbleUser : styles.bubbleAssistant]}>
              {m.role === 'assistant' && m.content === '' && m.streaming ? (
                <ActivityIndicator size="small" color="#9CA3AF" />
              ) : (
                <Text style={[styles.bubbleText, m.role === 'user' && styles.bubbleTextUser]}>
                  {m.content}
                  {m.streaming && m.content !== '' ? ' ▍' : ''}
                </Text>
              )}
            </View>
          </View>
        ))}
      </ScrollView>

      {chips.length > 0 && !busy && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.chipsRow}
          contentContainerStyle={{ gap: 8, paddingHorizontal: 16 }}
        >
          {chips.map((chip, i) => (
            <TouchableOpacity key={i} style={styles.chip} onPress={() => send(chip)}>
              <Text style={styles.chipText}>{chip}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      <View style={styles.inputBar}>
        <TextInput
          style={styles.input}
          placeholder="Ask about your health data…"
          placeholderTextColor="#9CA3AF"
          value={input}
          onChangeText={setInput}
          editable={!busy}
          multiline
          maxLength={500}
        />
        <TouchableOpacity
          style={[styles.sendBtn, (busy || !input.trim()) && styles.sendBtnDisabled]}
          onPress={() => send(input)}
          disabled={busy || !input.trim()}
        >
          {busy ? <ActivityIndicator size="small" color="#ffffff" /> : <Ionicons name="arrow-up" size={18} color="#ffffff" />}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: '#f9fafb' },
  header: { paddingTop: 40, paddingHorizontal: 20, paddingBottom: 14, backgroundColor: '#f9fafb', borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  aiIcon: { width: 34, height: 34, borderRadius: 12, backgroundColor: '#EFF6FF', alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 18, fontWeight: '900', color: '#111827' },
  subtitle: { fontSize: 11, color: '#9CA3AF', fontWeight: '600', marginTop: 1 },
  messagesContent: { padding: 16, paddingBottom: 24, flexGrow: 1 },
  emptyState: { alignItems: 'center', justifyContent: 'center', flex: 1, gap: 12, paddingHorizontal: 30, paddingTop: 60 },
  emptyText: { textAlign: 'center', color: '#9CA3AF', fontSize: 13, lineHeight: 19 },
  bubbleRow: { flexDirection: 'row', marginBottom: 12 },
  bubbleRowUser: { justifyContent: 'flex-end' },
  bubbleRowAssistant: { justifyContent: 'flex-start' },
  bubble: { maxWidth: '82%', borderRadius: 18, paddingHorizontal: 14, paddingVertical: 10 },
  bubbleUser: { backgroundColor: '#2563EB', borderBottomRightRadius: 4 },
  bubbleAssistant: { backgroundColor: '#ffffff', borderBottomLeftRadius: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.04, shadowRadius: 6, elevation: 1 },
  bubbleText: { fontSize: 14, lineHeight: 20, color: '#1F2937' },
  bubbleTextUser: { color: '#ffffff' },
  chipsRow: { maxHeight: 44, marginBottom: 8 },
  chip: { backgroundColor: '#ffffff', borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 8 },
  chipText: { fontSize: 12, fontWeight: '600', color: '#374151' },
  inputBar: { flexDirection: 'row', alignItems: 'flex-end', gap: 10, padding: 16, backgroundColor: '#f9fafb', borderTopWidth: 1, borderTopColor: '#F1F5F9' },
  input: { flex: 1, backgroundColor: '#ffffff', borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, fontSize: 14, color: '#111827', maxHeight: 100, borderWidth: 1, borderColor: '#E5E7EB' },
  sendBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#2563EB', alignItems: 'center', justifyContent: 'center' },
  sendBtnDisabled: { backgroundColor: '#CBD5E1' },
});
