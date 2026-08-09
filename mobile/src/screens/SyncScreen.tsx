import React, { useCallback, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useBottomTabBarHeight } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { fetchGarminStatus, syncGarmin, isTimeoutError, type GarminStatus } from '../services/api';
import Card from '../components/Card';
import LiveStatus from '../components/LiveStatus';
import { colors, radius, spacing, type } from '../theme';

const DEFAULT_USER = 'user_demo_001';

// Previously this screen drove an on-device Apple HealthKit fetch
// (react-native-health), which needs HealthKit entitlements tied to an Apple
// Developer Program account — the exact access this project doesn't have.
// Garmin sync runs server-side instead: the backend already holds cached
// credentials/tokens and pulls real wearable data itself. This screen's job
// is just to trigger that and show what happened — no native health SDK, no
// entitlements, no Apple Developer account needed.
export default function SyncScreen() {
  const tabBarHeight = useBottomTabBarHeight();
  const [status, setStatus] = useState<GarminStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [logsOpen, setLogsOpen] = useState(false);

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
    setLogsOpen(true);
    addLog('Requesting sync from backend…');
    addLog('Pulling 30 days of real data from Garmin — this can take a minute or two.');

    try {
      const result = await syncGarmin(DEFAULT_USER, 30);
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

  const connectionColor = !status?.configured ? colors.textTertiary : status.tokens_cached ? colors.success : colors.warning;

  return (
    <ScrollView style={styles.container} contentContainerStyle={[styles.content, { paddingBottom: tabBarHeight + 20 }]}>
      <View style={styles.header}>
        <Text style={styles.title}>Data Sync</Text>
        <Text style={styles.subtitle}>Real wearable data, synced server-side</Text>
      </View>

      <Card style={styles.card}>
        <View style={styles.row}>
          <View style={styles.deviceIcon}>
            <Ionicons name="watch" size={18} color={colors.primary} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.cardTitle}>Garmin Connect</Text>
            <LiveStatus
              live={!!status?.tokens_cached}
              label={
                status?.last_sync?.last_synced_at
                  ? `Last synced ${new Date(status.last_sync.last_synced_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}`
                  : 'No sync recorded yet'
              }
            />
          </View>
          <View style={[styles.statusPill, { backgroundColor: `${connectionColor}18` }]}>
            <Text style={[styles.statusPillText, { color: connectionColor }]}>{connectionLabel}</Text>
          </View>
        </View>

        {status && !status.configured && (
          <Text style={styles.hintText}>{status.hint ?? 'Garmin credentials are not configured on the backend yet.'}</Text>
        )}

        {status && (
          <View style={styles.metaRow}>
            <Text style={styles.metaText}>{status.last_sync?.days_synced ?? 0} days synced</Text>
            <View style={styles.metaDot} />
            <Text style={styles.metaText}>{status.garmin_rows_in_db ?? 0} rows stored</Text>
          </View>
        )}
      </Card>

      <TouchableOpacity
        style={[styles.syncButton, (!status?.configured || syncing) && styles.syncButtonDisabled]}
        onPress={handleSync}
        disabled={!status?.configured || syncing}
        activeOpacity={0.85}
      >
        {syncing ? (
          <>
            <ActivityIndicator color="#ffffff" size="small" />
            <Text style={styles.syncButtonText}>SYNCING…</Text>
          </>
        ) : (
          <>
            <Ionicons name="sync" size={15} color="#ffffff" />
            <Text style={styles.syncButtonText}>SYNC GARMIN DATA</Text>
          </>
        )}
      </TouchableOpacity>

      <TouchableOpacity style={styles.logsToggle} onPress={() => setLogsOpen((v) => !v)} activeOpacity={0.7}>
        <Text style={styles.logsToggleText}>
          {logsOpen ? 'Hide' : 'Show'} sync logs {logs.length > 0 ? `(${logs.length})` : ''}
        </Text>
        <Ionicons name={logsOpen ? 'chevron-up' : 'chevron-down'} size={14} color={colors.textSecondary} />
      </TouchableOpacity>

      {logsOpen && (
        <View style={styles.terminalContainer}>
          <ScrollView style={styles.terminal}>
            {logs.map((L, i) => (
              <Text key={i} style={styles.logText}>{L}</Text>
            ))}
            {logs.length === 0 && <Text style={styles.logTextIdle}>Awaiting user sequence...</Text>}
          </ScrollView>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, paddingTop: 54, paddingBottom: 32, flexGrow: 1 },
  header: { marginBottom: spacing.lg },
  title: { ...type.h1, fontSize: 22 },
  subtitle: { fontSize: 12, color: colors.textTertiary, marginTop: 3, fontWeight: '600' },
  card: { marginBottom: spacing.md },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 10 },
  deviceIcon: { width: 36, height: 36, borderRadius: 11, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  cardTitle: { fontSize: 14, fontWeight: '800', color: colors.textPrimary, marginBottom: 3 },
  statusPill: { paddingHorizontal: 9, paddingVertical: 5, borderRadius: 8 },
  statusPillText: { fontSize: 10.5, fontWeight: '800' },
  hintText: { fontSize: 11, color: colors.textTertiary, marginTop: 10, lineHeight: 15 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: colors.border },
  metaText: { fontSize: 11, color: colors.textSecondary, fontWeight: '600' },
  metaDot: { width: 3, height: 3, borderRadius: 1.5, backgroundColor: colors.textTertiary },
  syncButton: { flexDirection: 'row', gap: 8, backgroundColor: colors.textPrimary, borderRadius: radius.pill, paddingVertical: 15, alignItems: 'center', justifyContent: 'center', marginBottom: spacing.md },
  syncButtonDisabled: { opacity: 0.4 },
  syncButtonText: { color: '#ffffff', fontWeight: '900', letterSpacing: 1.2, fontSize: 12.5 },
  logsToggle: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4, paddingVertical: 8, marginBottom: spacing.sm },
  logsToggleText: { fontSize: 12, fontWeight: '700', color: colors.textSecondary },
  terminalContainer: { flex: 1, minHeight: 160, backgroundColor: '#1F2937', borderRadius: radius.md, padding: spacing.md, overflow: 'hidden' },
  terminal: { flex: 1 },
  logText: { color: '#86EFAC', fontFamily: 'Menlo', fontSize: 10.5, marginBottom: 5 },
  logTextIdle: { color: '#4B5563', fontFamily: 'Menlo', fontSize: 10.5, fontStyle: 'italic' },
});
