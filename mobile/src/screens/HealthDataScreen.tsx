import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useBottomTabBarHeight } from '@react-navigation/bottom-tabs';
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
import Sparkline from '../components/Sparkline';
import SegmentedControl from '../components/SegmentedControl';
import Card from '../components/Card';
import LiveStatus from '../components/LiveStatus';
import { LoadingState, EmptyState, ErrorState } from '../components/ScreenStates';
import {
  restingHeartRateStatus, stepsStatus, sleepStatus, stressStatus, spo2Status, respirationStatus, bmiStatus,
} from '../utils/metricRanges';
import { shortDate, relativeSync, latestMeasured } from '../utils/timeline';
import { colors, spacing, pastel, type } from '../theme';

const DEFAULT_USER = 'user_demo_001';
const RANGE_OPTIONS = ['7D', '14D', '30D'] as const;
const RANGE_DAYS: Record<(typeof RANGE_OPTIONS)[number], number> = { '7D': 7, '14D': 14, '30D': 30 };

const CORE_METRICS = [
  { key: 'heart_rate', label: 'Heart Rate', icon: 'heart' as const, unit: 'bpm', color: '220, 38, 38', tone: pastel.heartRate },
  { key: 'steps', label: 'Steps', icon: 'walk' as const, unit: 'steps', color: '37, 99, 235', tone: pastel.steps },
  { key: 'sleep', label: 'Sleep', icon: 'moon' as const, unit: 'hrs', color: '124, 58, 237', tone: pastel.sleep },
  { key: 'stress_level', label: 'Stress', icon: 'pulse' as const, unit: '/10', color: '217, 119, 6', tone: pastel.stress },
] as const;
type CoreKey = (typeof CORE_METRICS)[number]['key'];

export default function HealthDataScreen() {
  const tabBarHeight = useBottomTabBarHeight();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [days, setDays] = useState<HealthDay[]>([]);
  const [status, setStatus] = useState<GarminStatus | null>(null);
  const [range, setRange] = useState<(typeof RANGE_OPTIONS)[number]>('14D');
  const [error, setError] = useState<string | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  const [selectedMetric, setSelectedMetric] = useState<CoreKey>('heart_rate');

  const load = useCallback(async (rangeDays: number) => {
    try {
      setError(null);
      const [timeline, s] = await Promise.all([
        fetchHealthTimeline(DEFAULT_USER, rangeDays),
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
      load(RANGE_DAYS[range]);
    }, [load, range])
  );

  const onRefresh = () => {
    setRefreshing(true);
    load(RANGE_DAYS[range]);
  };

  const latestDay = days.length > 0 ? days[days.length - 1] : null;

  const trendsByKey = useMemo(() => {
    const out: Record<CoreKey, { labels: string[]; data: number[] }> = {
      heart_rate: { labels: [], data: [] },
      steps: { labels: [], data: [] },
      sleep: { labels: [], data: [] },
      stress_level: { labels: [], data: [] },
    };
    for (const key of Object.keys(out) as CoreKey[]) {
      const points = days
        .filter((d) => isFieldMeasured(d, key))
        .map((d) => ({ label: shortDate(d.date), value: (d as any)[key] as number }));
      out[key] = { labels: points.map((p) => p.label), data: points.map((p) => p.value) };
    }
    return out;
  }, [days]);

  const coreReadings = useMemo(
    () =>
      CORE_METRICS.map((m) => ({
        ...m,
        reading: latestMeasured(days, (d) => (d as any)[m.key], (d) => isFieldMeasured(d, m.key)),
      })),
    [days]
  );

  const secondaryDefs = [
    { icon: 'body' as const, label: 'BMI', unit: undefined as string | undefined, color: '#0EA5E9',
      extract: (d: HealthDay) => d.bmi, measured: (d: HealthDay) => isFieldMeasured(d, 'bmi'),
      status: (v: number) => bmiStatus(v), round: 1 },
    { icon: 'analytics' as const, label: 'HRV (RMSSD)', unit: 'ms', color: '#16A34A',
      extract: (d: HealthDay) => d.extras.hrv_rmssd, measured: (d: HealthDay) => d.extras.hrv_rmssd != null,
      status: null, round: 0 },
    { icon: 'water' as const, label: 'Blood Oxygen', unit: '%', color: '#0EA5E9',
      extract: (d: HealthDay) => d.extras.spo2_avg, measured: (d: HealthDay) => d.extras.spo2_avg != null,
      status: (v: number) => spo2Status(v), round: 0 },
    { icon: 'cloud' as const, label: 'Respiration', unit: 'brpm', color: '#059669',
      extract: (d: HealthDay) => d.extras.respiration_avg, measured: (d: HealthDay) => d.extras.respiration_avg != null,
      status: (v: number) => respirationStatus(v), round: 0 },
    { icon: 'battery-charging' as const, label: 'Battery Charged', unit: 'pts', color: '#16A34A',
      extract: (d: HealthDay) => d.extras.body_battery_charged, measured: (d: HealthDay) => d.extras.body_battery_charged != null,
      status: null, round: 0 },
    { icon: 'battery-half' as const, label: 'Battery Drained', unit: 'pts', color: '#DC2626',
      extract: (d: HealthDay) => d.extras.body_battery_drained, measured: (d: HealthDay) => d.extras.body_battery_drained != null,
      status: null, round: 0 },
  ];

  const secondaryReadings = useMemo(
    () =>
      secondaryDefs
        .map((def) => ({ def, reading: latestMeasured(days, def.extract, def.measured) }))
        .filter((r) => r.reading != null),
    [days]
  );

  const activeMetricDef = CORE_METRICS.find((m) => m.key === selectedMetric)!;
  const activeTrend = trendsByKey[selectedMetric];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[styles.content, { paddingBottom: tabBarHeight + 20 }]}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
    >
      <View style={styles.header}>
        <Text style={styles.title}>Health Data</Text>
        <LiveStatus live={!!status?.tokens_cached} label={relativeSync(status?.last_sync?.last_synced_at)} />
      </View>

      {loading ? (
        <LoadingState label="Loading synced data…" />
      ) : error ? (
        <ErrorState message={error} />
      ) : !latestDay ? (
        <EmptyState title="No synced data yet" subtitle="Sync Garmin data from the Sync tab first." />
      ) : (
        <>
          {/* ── Raw Garmin data — most recent real reading per metric ──── */}
          <View style={styles.sectionHeaderOnly}>
            <SectionHeader icon="watch-outline" title="Your Vitals" subtitle="Most recent reading — each metric syncs on its own schedule" tint={colors.primary} />
          </View>
          <View style={styles.grid}>
            {coreReadings.map((m) => {
              const r = m.reading;
              const value =
                r == null ? 0 : m.key === 'steps' ? Math.round(r.value as number).toLocaleString() : (r.value as number).toFixed(m.key === 'heart_rate' ? 0 : 1);
              const statusFn = m.key === 'heart_rate' ? restingHeartRateStatus : m.key === 'steps' ? stepsStatus : m.key === 'sleep' ? sleepStatus : stressStatus;
              return (
                <MetricCard
                  key={m.key}
                  icon={m.icon}
                  label={m.label}
                  value={value}
                  unit={m.unit}
                  pastel={m.tone}
                  notMeasured={r == null}
                  status={r != null ? statusFn(r.value as number) : 'neutral'}
                  asOf={r && !r.isLatestDay ? shortDate(r.date) : undefined}
                />
              );
            })}
          </View>

          {secondaryReadings.length > 0 && (
            <Card style={[styles.card, { marginTop: spacing.md }]} tight>
              <TouchableOpacity style={styles.moreToggle} onPress={() => setMoreOpen((v) => !v)} activeOpacity={0.7}>
                <Text style={styles.moreToggleText}>
                  {moreOpen ? 'Hide' : 'Show'} {secondaryReadings.length} more metric{secondaryReadings.length > 1 ? 's' : ''}
                </Text>
                <Ionicons name={moreOpen ? 'chevron-up' : 'chevron-down'} size={14} color={colors.primary} />
              </TouchableOpacity>
              {moreOpen && (
                <View style={[styles.grid, { marginTop: spacing.sm }]}>
                  {secondaryReadings.map(({ def, reading }, i) => {
                    const v = reading!.value as number;
                    return (
                      <MetricCard
                        key={i}
                        icon={def.icon}
                        label={def.label}
                        value={def.round === 0 ? Math.round(v) : v.toFixed(def.round)}
                        unit={def.unit}
                        iconColor={def.color}
                        status={def.status ? def.status(v) : 'neutral'}
                        asOf={!reading!.isLatestDay ? shortDate(reading!.date) : undefined}
                        compact
                      />
                    );
                  })}
                </View>
              )}
            </Card>
          )}

          {/* ── Historical trends — overview always visible, one full chart on demand ── */}
          <Card style={[styles.card, { marginTop: spacing.lg }]}>
            <SectionHeader
              icon="trending-up-outline"
              title="Trends"
              subtitle="Gaps mean nothing was measured that day"
              tint={colors.purple}
              right={
                <SegmentedControl<(typeof RANGE_OPTIONS)[number]>
                  options={RANGE_OPTIONS}
                  value={range}
                  onChange={setRange}
                />
              }
            />

            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.sparkRow}>
              {CORE_METRICS.map((m) => {
                const t = trendsByKey[m.key];
                const latestVal = t.data.length > 0 ? t.data[t.data.length - 1] : null;
                const display = latestVal == null ? '—' : m.key === 'steps' ? Math.round(latestVal).toLocaleString() : latestVal.toFixed(m.key === 'heart_rate' ? 0 : 1);
                return (
                  <TouchableOpacity key={m.key} onPress={() => setSelectedMetric(m.key)} activeOpacity={0.75}>
                    <Sparkline
                      label={m.label}
                      value={`${display} ${display === '—' ? '' : m.unit}`}
                      data={t.data}
                      color={`rgb(${m.color})`}
                      active={selectedMetric === m.key}
                    />
                  </TouchableOpacity>
                );
              })}
            </ScrollView>

            <View style={styles.divider} />
            <TrendChart title={`${activeMetricDef.label} · ${range}`} labels={activeTrend.labels} data={activeTrend.data} color={activeMetricDef.color} unit={activeMetricDef.unit} widthOffset={72} />
          </Card>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, paddingTop: 54 },
  header: { marginBottom: spacing.lg, gap: 6 },
  title: { ...type.h1, fontSize: 22 },
  sectionHeaderOnly: { marginBottom: 2 },
  card: { marginBottom: spacing.md },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  moreToggle: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4, paddingVertical: 2 },
  moreToggleText: { fontSize: 12, fontWeight: '700', color: colors.primary },
  sparkRow: { gap: spacing.sm, paddingBottom: 4 },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: spacing.md },
});
