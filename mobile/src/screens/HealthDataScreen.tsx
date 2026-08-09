import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import {
  fetchHealthTimeline,
  fetchGarminStatus,
  isFieldMeasured,
  type HealthDay,
  type GarminStatus,
} from '../services/api';
import SectionHeader from '../components/SectionHeader';
import MetricCard from '../components/MetricCard';
import TrendChart from '../components/TrendChart';
import {
  restingHeartRateStatus,
  stepsStatus,
  sleepStatus,
  stressStatus,
  spo2Status,
  respirationStatus,
  bmiStatus,
} from '../utils/metricRanges';

const DEFAULT_USER = 'user_demo_001';
const RANGE_OPTIONS = [7, 14, 30] as const;

function shortDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }).replace(' ', '\n');
}

function trendFor(
  days: HealthDay[],
  extract: (d: HealthDay) => number | null,
  measuredCheck: (d: HealthDay) => boolean
) {
  const points = days.filter(measuredCheck).map((d) => ({ label: shortDate(d.date), value: extract(d) as number }));
  return { labels: points.map((p) => p.label), data: points.map((p) => p.value) };
}

export default function HealthDataScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [days, setDays] = useState<HealthDay[]>([]);
  const [status, setStatus] = useState<GarminStatus | null>(null);
  const [rangeDays, setRangeDays] = useState<(typeof RANGE_OPTIONS)[number]>(14);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (range: number) => {
    try {
      setError(null);
      const [timeline, s] = await Promise.all([
        fetchHealthTimeline(DEFAULT_USER, range),
        fetchGarminStatus(DEFAULT_USER),
      ]);
      setDays(timeline.days);
      setStatus(s);
    } catch (e: any) {
      setError(e.message ?? 'Could not load health data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load(rangeDays);
    }, [load, rangeDays])
  );

  const onRefresh = () => {
    setRefreshing(true);
    load(rangeDays);
  };

  const latest = days.length > 0 ? days[days.length - 1] : null;

  const trends = useMemo(() => {
    if (days.length === 0) return null;
    return {
      heart_rate: trendFor(days, (d) => d.heart_rate, (d) => isFieldMeasured(d, 'heart_rate')),
      steps: trendFor(days, (d) => d.steps, (d) => isFieldMeasured(d, 'steps')),
      sleep: trendFor(days, (d) => d.sleep, (d) => isFieldMeasured(d, 'sleep')),
      stress: trendFor(days, (d) => d.stress_level, (d) => isFieldMeasured(d, 'stress_level')),
    };
  }, [days]);

  const lastSyncLabel = status?.last_sync?.last_synced_at
    ? new Date(status.last_sync.last_synced_at).toLocaleString(undefined, {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    : null;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#2563EB" />}
    >
      <View style={styles.header}>
        <Text style={styles.title}>Health Data</Text>
        <View style={styles.syncRow}>
          <View style={[styles.liveDot, { backgroundColor: status?.tokens_cached ? '#16A34A' : '#D97706' }]} />
          <Text style={styles.syncText}>
            {lastSyncLabel ? `Synced from Garmin · ${lastSyncLabel}` : 'Waiting for first sync'}
          </Text>
        </View>
      </View>

      {loading ? (
        <View style={styles.centerState}>
          <ActivityIndicator color="#2563EB" />
        </View>
      ) : error ? (
        <View style={styles.centerState}>
          <Ionicons name="cloud-offline-outline" size={28} color="#CBD5E1" />
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : !latest ? (
        <View style={styles.centerState}>
          <Ionicons name="watch-outline" size={28} color="#CBD5E1" />
          <Text style={styles.errorText}>No synced data yet — sync Garmin data from the Sync tab first.</Text>
        </View>
      ) : (
        <>
          {/* ── Raw Garmin data — today's readings ─────────────────────── */}
          <View style={styles.card}>
            <SectionHeader
              icon="watch-outline"
              title="Today's Readings"
              subtitle="Straight from your Garmin device — nothing estimated"
              tint="#2563EB"
            />
            <View style={styles.grid}>
              <MetricCard
                icon="heart"
                label="Heart Rate"
                value={Math.round(latest.heart_rate ?? 0)}
                unit="bpm"
                iconColor="#DC2626"
                notMeasured={!isFieldMeasured(latest, 'heart_rate')}
                status={latest.heart_rate != null ? restingHeartRateStatus(latest.heart_rate) : 'neutral'}
              />
              <MetricCard
                icon="walk"
                label="Steps"
                value={(latest.steps ?? 0).toLocaleString()}
                iconColor="#2563EB"
                notMeasured={!isFieldMeasured(latest, 'steps')}
                status={latest.steps != null ? stepsStatus(latest.steps) : 'neutral'}
              />
              <MetricCard
                icon="moon"
                label="Sleep"
                value={latest.sleep != null ? latest.sleep.toFixed(1) : 0}
                unit="hrs"
                iconColor="#7C3AED"
                notMeasured={!isFieldMeasured(latest, 'sleep')}
                status={latest.sleep != null ? sleepStatus(latest.sleep) : 'neutral'}
              />
              <MetricCard
                icon="pulse"
                label="Stress"
                value={latest.stress_level != null ? latest.stress_level.toFixed(1) : 0}
                unit="/10"
                iconColor="#D97706"
                notMeasured={!isFieldMeasured(latest, 'stress_level')}
                status={latest.stress_level != null ? stressStatus(latest.stress_level) : 'neutral'}
              />
              {isFieldMeasured(latest, 'bmi') && (
                <MetricCard
                  icon="body"
                  label="BMI"
                  value={latest.bmi!.toFixed(1)}
                  iconColor="#0EA5E9"
                  status={bmiStatus(latest.bmi!)}
                />
              )}
              {latest.extras.hrv_rmssd != null && (
                <MetricCard icon="analytics" label="HRV (RMSSD)" value={Math.round(latest.extras.hrv_rmssd)} unit="ms" iconColor="#16A34A" />
              )}
              {latest.extras.spo2_avg != null && (
                <MetricCard
                  icon="water"
                  label="Blood Oxygen"
                  value={Math.round(latest.extras.spo2_avg)}
                  unit="%"
                  iconColor="#0EA5E9"
                  status={spo2Status(latest.extras.spo2_avg)}
                />
              )}
              {latest.extras.respiration_avg != null && (
                <MetricCard
                  icon="cloud"
                  label="Respiration"
                  value={Math.round(latest.extras.respiration_avg)}
                  unit="brpm"
                  iconColor="#059669"
                  status={respirationStatus(latest.extras.respiration_avg)}
                />
              )}
              {latest.extras.body_battery_charged != null && (
                <MetricCard icon="battery-charging" label="Body Battery Charged" value={Math.round(latest.extras.body_battery_charged)} unit="pts" iconColor="#16A34A" />
              )}
              {latest.extras.body_battery_drained != null && (
                <MetricCard icon="battery-half" label="Body Battery Drained" value={Math.round(latest.extras.body_battery_drained)} unit="pts" iconColor="#DC2626" />
              )}
            </View>
            <Text style={styles.dateCaption}>{new Date(latest.date + 'T00:00:00').toDateString()}</Text>
          </View>

          {/* ── Historical trends ───────────────────────────────────────── */}
          <View style={styles.card}>
            <SectionHeader icon="trending-up-outline" title="Trends" subtitle="Real readings only — gaps mean nothing was measured" tint="#7C3AED" />

            <View style={styles.rangeToggle}>
              {RANGE_OPTIONS.map((opt) => (
                <TouchableOpacity
                  key={opt}
                  style={[styles.rangeBtn, rangeDays === opt && styles.rangeBtnActive]}
                  onPress={() => setRangeDays(opt)}
                >
                  <Text style={[styles.rangeBtnText, rangeDays === opt && styles.rangeBtnTextActive]}>{opt}D</Text>
                </TouchableOpacity>
              ))}
            </View>

            {trends && (
              <>
                <TrendChart title="Heart Rate" labels={trends.heart_rate.labels} data={trends.heart_rate.data} color="220, 38, 38" unit="bpm" />
                <TrendChart title="Steps" labels={trends.steps.labels} data={trends.steps.data} color="37, 99, 235" unit="steps" />
                <TrendChart title="Sleep" labels={trends.sleep.labels} data={trends.sleep.data} color="124, 58, 237" unit="hrs" />
                <TrendChart title="Stress" labels={trends.stress.labels} data={trends.stress.data} color="217, 119, 6" unit="/10" />
              </>
            )}
          </View>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb', padding: 20 },
  header: { marginTop: 40, marginBottom: 20 },
  title: { fontSize: 28, fontWeight: '900', color: '#111827', marginBottom: 8 },
  syncRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  liveDot: { width: 6, height: 6, borderRadius: 3 },
  syncText: { fontSize: 12, color: '#6B7280', fontWeight: '600' },
  centerState: { alignItems: 'center', justifyContent: 'center', paddingVertical: 60, gap: 10 },
  errorText: { color: '#9CA3AF', fontSize: 13, textAlign: 'center', paddingHorizontal: 30 },
  card: {
    backgroundColor: '#ffffff', borderRadius: 24, padding: 20, marginBottom: 16,
    shadowColor: '#000', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.05, shadowRadius: 20, elevation: 5,
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  dateCaption: { fontSize: 11, color: '#B0B7C3', marginTop: 14, textAlign: 'right', fontWeight: '600' },
  rangeToggle: { flexDirection: 'row', backgroundColor: '#F3F4F6', borderRadius: 12, padding: 3, marginBottom: 18, alignSelf: 'flex-start' },
  rangeBtn: { paddingHorizontal: 16, paddingVertical: 6, borderRadius: 9 },
  rangeBtnActive: { backgroundColor: '#ffffff', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.08, shadowRadius: 3, elevation: 1 },
  rangeBtnText: { fontSize: 12, fontWeight: '700', color: '#9CA3AF' },
  rangeBtnTextActive: { color: '#2563EB' },
});
