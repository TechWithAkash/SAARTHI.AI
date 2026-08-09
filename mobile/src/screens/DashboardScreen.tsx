import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, Image, Dimensions, TouchableOpacity } from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { fetchRiskScore, fetchRiskHistory, fetchGarminStatus, type RiskResponse, type GarminStatus } from '../services/api';
import RiskRing from '../components/RiskRing';
import SectionHeader from '../components/SectionHeader';
import { getRiskColors, getScoreColor } from '../utils/riskColors';

const screenWidth = Dimensions.get('window').width;
const DEFAULT_USER = 'user_demo_001';

export default function DashboardScreen() {
  const navigation = useNavigation<any>();
  const [loading, setLoading] = useState(true);
  const [risk, setRisk] = useState<RiskResponse | null>(null);
  const [history, setHistory] = useState<number[]>([]);
  const [hasData, setHasData] = useState(true);
  const [garminStatus, setGarminStatus] = useState<GarminStatus | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [riskData, s] = await Promise.all([
        fetchRiskScore(DEFAULT_USER),
        fetchGarminStatus(DEFAULT_USER).catch(() => null),
      ]);
      setRisk(riskData);
      setHasData(true);
      setGarminStatus(s);

      const historyData = await fetchRiskHistory(DEFAULT_USER);
      if (historyData && historyData.length > 0) {
        // Keep last 6 for mobile chart legibility
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

  const colors = getRiskColors(risk?.risk_category);
  const lastSyncLabel = garminStatus?.last_sync?.last_synced_at
    ? new Date(garminStatus.last_sync.last_synced_at).toLocaleString(undefined, {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    : null;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={loadData} tintColor="#2563EB" />}
    >
      <View style={styles.header}>
        <View style={styles.logoRow}>
          <Image source={require('../../assets/logo.png')} style={styles.logo} />
          <Text style={styles.logoText}>SAARTHI<Text style={styles.logoAccent}>.AI</Text></Text>
        </View>
        <Text style={styles.badge}>SAARTHI HEALTH GUIDE</Text>
        <Text style={styles.title}>Personalized <Text style={styles.highlight}>Foresight</Text></Text>
        {lastSyncLabel && (
          <View style={styles.syncRow}>
            <View style={[styles.liveDot, { backgroundColor: garminStatus?.tokens_cached ? '#16A34A' : '#D97706' }]} />
            <Text style={styles.syncText}>Live from Garmin · updated {lastSyncLabel}</Text>
          </View>
        )}
      </View>

      {risk ? (
        <>
          <View style={styles.card}>
            <SectionHeader icon="sparkles-outline" title="AI Risk Assessment" subtitle="Generated from your synced health data" tint="#2563EB" />
            <Text style={styles.score}>{risk.risk_score.toFixed(0)}<Text style={styles.scoreScale}>/100</Text></Text>
            <View style={[styles.statusBadge, { backgroundColor: colors.bg }]}>
              <Text style={[styles.statusText, { color: colors.text }]}>{risk.risk_category}</Text>
            </View>

            {risk.model_saturated && (
              <View style={styles.cautionBanner}>
                <Ionicons name="alert-circle-outline" size={16} color="#B45309" />
                <Text style={styles.cautionText}>
                  Inputs are outside the model's normal range — treat this score as low-confidence.
                </Text>
              </View>
            )}

            {risk.top_risk_factors && risk.top_risk_factors.length > 0 && (
              <View style={styles.factorsList}>
                <Text style={styles.factorsTitle}>TOP RISK DRIVERS</Text>
                {risk.top_risk_factors.map((factor, i) => (
                  <Text key={i} style={styles.factorItem}>• {factor.replace(/_/g, ' ')}</Text>
                ))}
              </View>
            )}
          </View>

          {(risk.diabetes_risk != null || risk.cvd_risk != null || risk.hypertension_risk != null) && (
            <View style={styles.card}>
              <SectionHeader icon="body-outline" title="At A Glance" subtitle="Disease-specific risk, same model" tint="#7C3AED" />
              <View style={styles.ringsRow}>
                <RiskRing label="Diabetes" value={risk.diabetes_risk} color={getScoreColor(risk.diabetes_risk)} />
                <RiskRing label="Cardiovascular" value={risk.cvd_risk} color={getScoreColor(risk.cvd_risk)} />
                <RiskRing label="Hypertension" value={risk.hypertension_risk} color={getScoreColor(risk.hypertension_risk)} />
              </View>
            </View>
          )}

          {history.length > 0 && (
            <View style={styles.card}>
              <SectionHeader icon="trending-up-outline" title="Risk Trajectory" subtitle="Composite score, most recent readings" tint="#16A34A" />
              <LineChart
                data={{
                  labels: history.map((_, i) => `d-${history.length - i}`),
                  datasets: [{ data: history }],
                }}
                width={screenWidth - 72}
                height={180}
                chartConfig={{
                  backgroundColor: '#ffffff',
                  backgroundGradientFrom: '#ffffff',
                  backgroundGradientTo: '#ffffff',
                  decimalPlaces: 0,
                  color: (opacity = 1) => `rgba(37, 99, 235, ${opacity})`,
                  labelColor: (opacity = 1) => `rgba(156, 163, 175, ${opacity})`,
                  style: { borderRadius: 16 },
                  propsForDots: { r: '4', strokeWidth: '2', stroke: '#2563EB' },
                  propsForBackgroundLines: { stroke: '#F1F5F9' },
                }}
                bezier
                style={styles.chart}
              />
            </View>
          )}

          <View style={styles.navCardsRow}>
            <TouchableOpacity style={styles.navCard} onPress={() => navigation.navigate('HealthData')} activeOpacity={0.85}>
              <Ionicons name="analytics-outline" size={20} color="#2563EB" />
              <Text style={styles.navCardTitle}>Raw Health Data</Text>
              <Text style={styles.navCardSub}>Steps, HR, sleep & trends</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.navCard} onPress={() => navigation.navigate('Assistant')} activeOpacity={0.85}>
              <Ionicons name="chatbubble-ellipses-outline" size={20} color="#7C3AED" />
              <Text style={styles.navCardTitle}>Ask the AI</Text>
              <Text style={styles.navCardSub}>About your risk & trends</Text>
            </TouchableOpacity>
          </View>
        </>
      ) : (
        <View style={styles.emptyState}>
          <Ionicons name="watch-outline" size={32} color="#CBD5E1" />
          <Text style={styles.infoText}>
            {loading ? 'Loading your health twin…' : !hasData ? 'No risk data yet — sync Garmin data first.' : 'Something went wrong loading your data.'}
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb', padding: 20 },
  header: { marginTop: 40, marginBottom: 20, alignItems: 'center' },
  logoRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 14 },
  logo: { width: 36, height: 36, borderRadius: 10 },
  logoText: { fontSize: 20, fontWeight: '900', color: '#111827', letterSpacing: 2 },
  logoAccent: { color: '#2563EB' },
  badge: { fontSize: 10, fontWeight: 'bold', color: '#16A34A', backgroundColor: '#ECFDF5', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20, overflow: 'hidden', marginBottom: 10 },
  title: { fontSize: 28, fontWeight: '900', color: '#111827' },
  highlight: { color: '#22C55E' },
  syncRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 10 },
  liveDot: { width: 6, height: 6, borderRadius: 3 },
  syncText: { fontSize: 11, color: '#9CA3AF', fontWeight: '600' },
  card: { backgroundColor: '#ffffff', borderRadius: 24, padding: 24, shadowColor: '#000', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.05, shadowRadius: 20, elevation: 5, marginBottom: 16 },
  score: { fontSize: 64, fontWeight: '900', color: '#111827', marginBottom: 10 },
  scoreScale: { fontSize: 24, fontWeight: '700', color: '#D1D5DB' },
  statusBadge: { alignSelf: 'flex-start', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12, marginBottom: 16 },
  statusText: { fontWeight: 'bold', fontSize: 14, textTransform: 'uppercase' },
  cautionBanner: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, backgroundColor: '#FFFBEB', borderRadius: 12, padding: 12, marginBottom: 16 },
  cautionText: { flex: 1, fontSize: 12, color: '#92400E', lineHeight: 17 },
  factorsList: { borderTopWidth: 1, borderTopColor: '#F3F4F6', paddingTop: 16 },
  factorsTitle: { fontSize: 11, fontWeight: 'bold', color: '#6B7280', marginBottom: 8 },
  factorItem: { fontSize: 14, color: '#374151', marginBottom: 4, textTransform: 'capitalize' },
  ringsRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 6 },
  chart: { borderRadius: 16, marginLeft: -16 },
  navCardsRow: { flexDirection: 'row', gap: 12, marginBottom: 40 },
  navCard: { flex: 1, backgroundColor: '#ffffff', borderRadius: 20, padding: 16, gap: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.04, shadowRadius: 10, elevation: 2 },
  navCardTitle: { fontSize: 13, fontWeight: '800', color: '#111827', marginTop: 6 },
  navCardSub: { fontSize: 11, color: '#9CA3AF' },
  emptyState: { backgroundColor: '#ffffff', borderRadius: 24, padding: 32, alignItems: 'center', gap: 10, marginBottom: 16 },
  infoText: { textAlign: 'center', color: '#6B7280', fontSize: 13 },
});
