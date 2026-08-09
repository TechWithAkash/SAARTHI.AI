import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, Image, Dimensions, TouchableOpacity } from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useBottomTabBarHeight } from '@react-navigation/bottom-tabs';
import {
  fetchRiskScore, fetchRiskHistory, fetchGarminStatus, fetchHealthTimeline,
  isFieldMeasured, type RiskResponse, type GarminStatus, type HealthDay,
} from '../services/api';
import RiskRing from '../components/RiskRing';
import MetricCard from '../components/MetricCard';
import Card from '../components/Card';
import LiveStatus from '../components/LiveStatus';
import { LoadingState, EmptyState } from '../components/ScreenStates';
import { getRiskColors, getScoreColor } from '../utils/riskColors';
import { restingHeartRateStatus, stepsStatus } from '../utils/metricRanges';
import { relativeSync, latestMeasured, shortDate } from '../utils/timeline';
import { colors, spacing, radius, pastel, type } from '../theme';

const screenWidth = Dimensions.get('window').width;
const DEFAULT_USER = 'user_demo_001';

export default function DashboardScreen() {
  const navigation = useNavigation<any>();
  const tabBarHeight = useBottomTabBarHeight();
  const [loading, setLoading] = useState(true);
  const [risk, setRisk] = useState<RiskResponse | null>(null);
  const [history, setHistory] = useState<number[]>([]);
  const [hasData, setHasData] = useState(true);
  const [garminStatus, setGarminStatus] = useState<GarminStatus | null>(null);
  const [days, setDays] = useState<HealthDay[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [riskData, s, timeline] = await Promise.all([
        fetchRiskScore(DEFAULT_USER),
        fetchGarminStatus(DEFAULT_USER).catch(() => null),
        fetchHealthTimeline(DEFAULT_USER, 7).catch(() => null),
      ]);
      setRisk(riskData);
      setHasData(true);
      setGarminStatus(s);
      if (timeline) setDays(timeline.days);

      const historyData = await fetchRiskHistory(DEFAULT_USER);
      if (historyData && historyData.length > 0) {
        setHistory(historyData.slice(0, 6).reverse().map((d: any) => d.risk_score));
      }
    } catch (e: any) {
      if (e.response && e.response.status === 404) {
        setHasData(false);
      } else {
        console.error('Fetch error:', e.message);
      }
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadData();
    }, [])
  );

  const colorsFor = getRiskColors(risk?.risk_category);
  const stepsReading = latestMeasured(days, (d) => d.steps, (d) => isFieldMeasured(d, 'steps'));
  const hrReading = latestMeasured(days, (d) => d.heart_rate, (d) => isFieldMeasured(d, 'heart_rate'));

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[styles.content, { paddingBottom: tabBarHeight + 20 }]}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={loadData} tintColor={colors.primary} />}
    >
      <View style={styles.header}>
        <View style={styles.brandRow}>
          <Image source={require('../../assets/logo.png')} style={styles.avatar} />
          <View>
            <Text style={styles.welcome}>Welcome back</Text>
            {/* No login system exists — there's no app-side profile name to
                show. The Garmin account itself has a real one (display_name,
                already flowing through /garmin/status), so that's used
                instead of a fabricated username or the brand name standing
                in for a person. */}
            <Text style={styles.brandText} numberOfLines={1}>
              {garminStatus?.last_sync?.display_name ?? (
                <>SAARTHI<Text style={styles.brandAccent}>.AI</Text></>
              )}
            </Text>
          </View>
        </View>
        <LiveStatus live={!!garminStatus?.tokens_cached} label={relativeSync(garminStatus?.last_sync?.last_synced_at)} />
      </View>

      <Text style={styles.headline}>How's Your Health Today?</Text>

      {loading && !risk ? (
        <LoadingState label="Loading your health twin…" />
      ) : !risk ? (
        <EmptyState
          title={!hasData ? 'No risk data yet' : 'Something went wrong'}
          subtitle={!hasData ? 'Sync Garmin data from the Sync tab to get started.' : 'Pull down to try again.'}
        />
      ) : (
        <>
          {/* ── Hero: soft pastel card, the "most important thing right now" ── */}
          <View style={[styles.heroCard, { backgroundColor: colors.primarySoft }]}>
            <View style={styles.heroTopRow}>
              <Text style={styles.heroEyebrow}>HEALTH EQUILIBRIUM</Text>
              <View style={styles.heroIconWrap}>
                <Ionicons name="sparkles" size={14} color={colors.primary} />
              </View>
            </View>

            {/* Same computation as web's Health Equilibrium card: 100 - risk_score.
                Identical underlying data to /risk, shown inverted as a positively-
                framed score so both platforms match — this was flagged as an
                inconsistency when mobile showed raw risk (14) and web showed the
                inverted figure (86); now both show the inverted one. */}
            <View style={styles.heroRow}>
              <View>
                <Text style={styles.score}>
                  {(100 - risk.risk_score).toFixed(0)}
                  <Text style={styles.scoreScale}>/100</Text>
                </Text>
                <View style={[styles.statusBadge, { backgroundColor: colorsFor.bg }]}>
                  <Text style={[styles.statusText, { color: colorsFor.text }]}>{risk.risk_category}</Text>
                </View>
              </View>

              {risk.top_risk_factors && risk.top_risk_factors.length > 0 && (
                <View style={styles.driversBlock}>
                  {risk.top_risk_factors.slice(0, 3).map((factor, i) => (
                    <View key={i} style={styles.driverChip}>
                      <Text style={styles.driverChipText} numberOfLines={1}>{factor.replace(/_/g, ' ')}</Text>
                    </View>
                  ))}
                </View>
              )}
            </View>

            {risk.model_saturated && (
              <View style={styles.cautionBanner}>
                <Ionicons name="alert-circle-outline" size={13} color={colors.warning} />
                <Text style={styles.cautionText}>Inputs are outside the model's normal range — treat this as low-confidence.</Text>
              </View>
            )}
          </View>

          {/* ── Vitals teaser — same pattern shown fully on the Vitals tab ── */}
          <Text style={styles.sectionTitle}>Your Vitals</Text>
          <View style={styles.vitalsRow}>
            <MetricCard
              icon="walk" label="Daily Steps"
              value={stepsReading ? Math.round(stepsReading.value).toLocaleString() : 0}
              notMeasured={!stepsReading}
              status={stepsReading ? stepsStatus(stepsReading.value) : 'neutral'}
              asOf={stepsReading && !stepsReading.isLatestDay ? shortDate(stepsReading.date) : undefined}
              pastel={pastel.steps}
            />
            <MetricCard
              icon="heart" label="Heart Rate" unit="bpm"
              value={hrReading ? Math.round(hrReading.value) : 0}
              notMeasured={!hrReading}
              status={hrReading ? restingHeartRateStatus(hrReading.value) : 'neutral'}
              asOf={hrReading && !hrReading.isLatestDay ? shortDate(hrReading.date) : undefined}
              pastel={pastel.heartRate}
            />
          </View>

          {(risk.diabetes_risk != null || risk.cvd_risk != null || risk.hypertension_risk != null) && (
            <Card style={styles.card} tight>
              <Text style={styles.cardLabel}>DISEASE RISK — AT A GLANCE</Text>
              <View style={styles.ringsRow}>
                <RiskRing label="Diabetes" value={risk.diabetes_risk} color={getScoreColor(risk.diabetes_risk)} />
                <RiskRing label="Cardiovascular" value={risk.cvd_risk} color={getScoreColor(risk.cvd_risk)} />
                <RiskRing label="Hypertension" value={risk.hypertension_risk} color={getScoreColor(risk.hypertension_risk)} />
              </View>
            </Card>
          )}

          {history.length > 0 && (
            <Card style={styles.card} tight>
              <Text style={styles.cardLabel}>RISK TRAJECTORY</Text>
              <LineChart
                data={{ labels: history.map((_, i) => `d-${history.length - i}`), datasets: [{ data: history }] }}
                width={screenWidth - 72}
                height={120}
                chartConfig={{
                  backgroundColor: colors.surface,
                  backgroundGradientFrom: colors.surface,
                  backgroundGradientTo: colors.surface,
                  decimalPlaces: 0,
                  color: (opacity = 1) => `rgba(37, 99, 235, ${opacity})`,
                  labelColor: (opacity = 1) => `rgba(148, 163, 184, ${opacity})`,
                  style: { borderRadius: 12 },
                  propsForDots: { r: '3', strokeWidth: '2', stroke: colors.primary },
                  propsForBackgroundLines: { stroke: colors.border },
                }}
                bezier
                style={styles.chart}
              />
            </Card>
          )}

          {/* ── Quick actions — icon-grid, matches every real destination in the app ── */}
          <Text style={styles.sectionTitle}>Explore</Text>
          <View style={styles.actionsGrid}>
            <TouchableOpacity style={styles.actionTile} onPress={() => navigation.navigate('HealthData')} activeOpacity={0.75}>
              <View style={[styles.actionIcon, { backgroundColor: colors.primarySoft }]}>
                <Ionicons name="analytics-outline" size={18} color={colors.primary} />
              </View>
              <Text style={styles.actionTileLabel}>Vitals</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.actionTile} onPress={() => navigation.navigate('Assistant')} activeOpacity={0.75}>
              <View style={[styles.actionIcon, { backgroundColor: colors.purpleSoft }]}>
                <Ionicons name="chatbubble-ellipses-outline" size={18} color={colors.purple} />
              </View>
              <Text style={styles.actionTileLabel}>Ask AI</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.actionTile} onPress={() => navigation.navigate('Sync')} activeOpacity={0.75}>
              <View style={[styles.actionIcon, { backgroundColor: colors.successSoft }]}>
                <Ionicons name="watch-outline" size={18} color={colors.success} />
              </View>
              <Text style={styles.actionTileLabel}>Sync</Text>
            </TouchableOpacity>
          </View>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, paddingTop: 54 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  avatar: { width: 38, height: 38, borderRadius: 19 },
  welcome: { fontSize: 11, color: colors.textTertiary, fontWeight: '600' },
  brandText: { fontSize: 15, fontWeight: '900', color: colors.textPrimary, letterSpacing: 0.3, marginTop: 1 },
  brandAccent: { color: colors.primary },
  headline: { fontSize: 25, fontWeight: '900', color: colors.textPrimary, lineHeight: 30, marginBottom: spacing.lg },

  heroCard: { borderRadius: radius.lg + 4, padding: spacing.lg, marginBottom: spacing.lg },
  heroTopRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  heroEyebrow: { fontSize: 10.5, fontWeight: '800', letterSpacing: 0.6, color: colors.primary, opacity: 0.75 },
  heroIconWrap: { width: 26, height: 26, borderRadius: 13, backgroundColor: 'rgba(255,255,255,0.65)', alignItems: 'center', justifyContent: 'center' },
  heroRow: { flexDirection: 'row', gap: spacing.lg },
  score: { fontSize: 44, fontWeight: '900', color: colors.textPrimary },
  scoreScale: { fontSize: 17, fontWeight: '700', color: 'rgba(15,23,42,0.3)' },
  statusBadge: { alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 10, marginTop: 6 },
  statusText: { fontWeight: '800', fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.3 },
  driversBlock: { flex: 1, justifyContent: 'center', gap: 6 },
  driverChip: { backgroundColor: 'rgba(255,255,255,0.65)', borderRadius: 8, paddingHorizontal: 9, paddingVertical: 6 },
  driverChipText: { fontSize: 10.5, fontWeight: '700', color: colors.textPrimary, textTransform: 'capitalize' },
  cautionBanner: { flexDirection: 'row', alignItems: 'flex-start', gap: 6, backgroundColor: 'rgba(255,255,255,0.65)', borderRadius: radius.sm, padding: 10, marginTop: 14 },
  cautionText: { flex: 1, fontSize: 11, color: '#92400E', lineHeight: 15 },

  sectionTitle: { fontSize: 15, fontWeight: '800', color: colors.textPrimary, marginBottom: 10 },
  vitalsRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.lg },
  card: { marginBottom: spacing.md },
  cardLabel: { ...type.eyebrow, marginBottom: 10 },
  ringsRow: { flexDirection: 'row', justifyContent: 'space-between' },
  chart: { borderRadius: 12, marginLeft: -16 },

  actionsGrid: { flexDirection: 'row', gap: spacing.sm },
  actionTile: { flex: 1, backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, paddingVertical: 16, alignItems: 'center', gap: 8 },
  actionIcon: { width: 36, height: 36, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  actionTileLabel: { fontSize: 11.5, fontWeight: '800', color: colors.textPrimary },
});
