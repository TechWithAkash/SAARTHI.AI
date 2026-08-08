import React, { useCallback, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { fetchGarminStatus, syncGarmin, isTimeoutError, type GarminStatus } from '../services/api';

const DEFAULT_USER = 'user_demo_001';

// Previously this screen drove an on-device Apple HealthKit fetch
// (react-native-health), which needs HealthKit entitlements tied to an Apple
// Developer Program account — the exact access this project doesn't have.
// Garmin sync runs server-side instead: the backend already holds cached
// credentials/tokens and pulls real wearable data itself. This screen's job
// is just to trigger that and show what happened — no native health SDK, no
// entitlements, no Apple Developer account needed.
export default function SyncScreen() {
  const [status, setStatus] = useState<GarminStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  const addLog = (msg: string) => {
    setLogs((prev) => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev]);
  };

  const loadStatus = useCallback(async () => {
    try {
      setStatusLoading(true);
      const s = await fetchGarminStatus(DEFAULT_USER);
      setStatus(s);
    } catch (e: any) {
      addLog(`Could not reach backend: ${e.message ?? 'unknown error'}`);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadStatus();
    }, [loadStatus])
  );

  const handleSync = async () => {
    if (!status?.configured) return;
    setSyncing(true);
    addLog('Requesting sync from backend…');
    addLog('Pulling real data from Garmin — this can take up to a minute.');

    try {
      const result = await syncGarmin(DEFAULT_USER, 14);
      addLog(`Source: ${result.source} | Status: ${result.status}`);
      addLog(`Ingested ${result.days_ingested} day(s): ${result.date_range.start} → ${result.date_range.end}`);
      addLog('SUCCESS — dashboard will reflect this on next load.');
      await loadStatus();
    } catch (e: any) {
      if (isTimeoutError(e)) {
        addLog('TIMED OUT waiting for a response — Garmin can be slow.');
        addLog('The sync may still finish on the backend; pull to refresh status in a minute.');
      } else {
        const detail = e.response?.data?.detail ?? e.message ?? 'Sync failed';
        addLog(`ERROR: ${detail}`);
      }
    } finally {
      setSyncing(false);
    }
  };

  const connectionLabel = statusLoading
    ? 'Checking…'
    : !status?.configured
    ? 'Not Configured'
    : status.tokens_cached
    ? 'Connected'
    : 'Ready — Not Synced';

  const connectionColor = !status?.configured ? '#9CA3AF' : status.tokens_cached ? '#16A34A' : '#D97706';

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Data Sync</Text>
        <Text style={styles.subtitle}>Real wearable data, synced server-side</Text>
      </View>

      <View style={styles.card}>
        <View style={styles.row}>
          <View style={styles.deviceIcon}>
            <Ionicons name="watch" size={20} color="#2563EB" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.cardTitle}>Garmin Connect</Text>
            <Text style={styles.cardDesc}>
              {status?.last_sync?.last_synced_at
                ? `Last synced ${new Date(status.last_sync.last_synced_at).toLocaleString()}`
                : 'No sync recorded yet'}
            </Text>
          </View>
          <View style={[styles.statusPill, { backgroundColor: `${connectionColor}18` }]}>
            <View style={[styles.statusDot, { backgroundColor: connectionColor }]} />
            <Text style={[styles.statusPillText, { color: connectionColor }]}>{connectionLabel}</Text>
          </View>
        </View>

        {status && !status.configured && (
          <Text style={styles.hintText}>{status.hint ?? 'Garmin credentials are not configured on the backend yet.'}</Text>
        )}
      </View>

      <TouchableOpacity
        style={[styles.syncButton, (!status?.configured || syncing) && styles.syncButtonDisabled]}
        onPress={handleSync}
        disabled={!status?.configured || syncing}
        activeOpacity={0.85}
      >
        {syncing ? (
          <>
            <ActivityIndicator color="#ffffff" />
            <Text style={styles.syncButtonText}>SYNCING…</Text>
          </>
        ) : (
          <>
            <Ionicons name="sync" size={16} color="#ffffff" />
            <Text style={styles.syncButtonText}>SYNC GARMIN DATA</Text>
          </>
        )}
      </TouchableOpacity>

      <View style={styles.terminalContainer}>
        <Text style={styles.terminalTitle}>SYNC LIFECYCLE LOGS</Text>
        <ScrollView style={styles.terminal}>
          {logs.map((L, i) => <Text key={i} style={styles.logText}>{L}</Text>)}
          {logs.length === 0 && <Text style={styles.logTextIdle}>Awaiting user sequence...</Text>}
        </ScrollView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb', padding: 20 },
  header: { marginTop: 40, marginBottom: 30 },
  title: { fontSize: 32, fontWeight: '900', color: '#111827' },
  subtitle: { fontSize: 14, color: '#6B7280', marginTop: 4 },
  card: { backgroundColor: '#ffffff', borderRadius: 24, padding: 20, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.03, shadowRadius: 10, elevation: 2, marginBottom: 20 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12 },
  deviceIcon: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#EFF6FF', alignItems: 'center', justifyContent: 'center' },
  cardTitle: { fontSize: 16, fontWeight: 'bold', color: '#111827' },
  cardDesc: { fontSize: 12, color: '#6B7280', marginTop: 2 },
  statusPill: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 20 },
  statusDot: { width: 6, height: 6, borderRadius: 3 },
  statusPillText: { fontSize: 11, fontWeight: '700' },
  hintText: { fontSize: 11, color: '#9CA3AF', marginTop: 12, lineHeight: 16 },
  syncButton: { flexDirection: 'row', gap: 8, backgroundColor: '#111827', borderRadius: 100, paddingVertical: 18, alignItems: 'center', justifyContent: 'center', shadowColor: '#111827', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.2, shadowRadius: 15, elevation: 5, marginBottom: 30 },
  syncButtonDisabled: { opacity: 0.4 },
  syncButtonText: { color: '#ffffff', fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  terminalContainer: { flex: 1, backgroundColor: '#1F2937', borderRadius: 16, padding: 16, overflow: 'hidden' },
  terminalTitle: { color: '#9CA3AF', fontSize: 10, fontWeight: '900', letterSpacing: 2, marginBottom: 12 },
  terminal: { flex: 1 },
  logText: { color: '#86EFAC', fontFamily: 'Menlo', fontSize: 11, marginBottom: 6 },
  logTextIdle: { color: '#4B5563', fontFamily: 'Menlo', fontSize: 11, fontStyle: 'italic' },
});
