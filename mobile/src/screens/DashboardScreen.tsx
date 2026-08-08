import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, Image } from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { Dimensions } from 'react-native';
import { fetchRiskScore, fetchRiskHistory } from '../services/api';
import { useFocusEffect } from '@react-navigation/native';

const screenWidth = Dimensions.get('window').width;
const DEFAULT_USER = 'user_demo_001';

export default function DashboardScreen() {
  const [loading, setLoading] = useState(true);
  const [risk, setRisk] = useState<{ score: number; category: string; factors: string[] } | null>(null);
  const [history, setHistory] = useState<number[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const riskData = await fetchRiskScore(DEFAULT_USER);
      setRisk({
        score: riskData.risk_score,
        category: riskData.risk_category,
        factors: riskData.top_risk_factors || [],
      });

      const historyData = await fetchRiskHistory(DEFAULT_USER);
      if (historyData && historyData.length > 0) {
         // Keep last 6 for mobile chart legibility
         setHistory(historyData.slice(0, 6).reverse().map((d: any) => d.risk_score));
      }
    } catch (e: any) {
      if (e.response && e.response.status === 404) {
        console.log('No risk data exists yet. Empty state rendered.');
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

  return (
    <ScrollView 
      style={styles.container} 
      refreshControl={<RefreshControl refreshing={loading} onRefresh={loadData} tintColor="#16A34A" />}
    >
      <View style={styles.header}>
        <View style={styles.logoRow}>
          <Image source={require('../../assets/logo.png')} style={styles.logo} />
          <Text style={styles.logoText}>SAARTHI<Text style={styles.logoAccent}>.AI</Text></Text>
        </View>
        <Text style={styles.badge}>SAARTHI HEALTH GUIDE</Text>
        <Text style={styles.title}>Personalized <Text style={styles.highlight}>Foresight</Text></Text>
      </View>

      {risk ? (
        <View style={styles.card}>
          <Text style={styles.scoreTitle}>CURRENT RISK SCORE</Text>
          <Text style={styles.score}>{risk.score.toFixed(0)}<Text style={styles.scoreScale}>/100</Text></Text>
          <View style={styles.statusBadge}>
            <Text style={styles.statusText}>{risk.category}</Text>
          </View>

          <View style={styles.factorsList}>
            <Text style={styles.factorsTitle}>TOP RISK DRIVERS:</Text>
            {risk.factors.map((factor, i) => (
              <Text key={i} style={styles.factorItem}>• {factor}</Text>
            ))}
          </View>
        </View>
      ) : (
        <Text style={styles.infoText}>{loading ? 'Loading Twin...' : 'No risk data available. Sync Apple Health first.'}</Text>
      )}

      {history.length > 0 && (
        <View style={styles.chartContainer}>
          <Text style={styles.chartTitle}>RISK TRAJECTORY</Text>
          <LineChart
            data={{
              labels: history.map((_, i) => `d-${history.length - i}`),
              datasets: [{ data: history }]
            }}
            width={screenWidth - 40}
            height={220}
            chartConfig={{
              backgroundColor: '#ffffff',
              backgroundGradientFrom: '#ffffff',
              backgroundGradientTo: '#ffffff',
              decimalPlaces: 0,
              color: (opacity = 1) => `rgba(34, 197, 94, ${opacity})`,
              labelColor: (opacity = 1) => `rgba(156, 163, 175, ${opacity})`,
              style: { borderRadius: 16 },
              propsForDots: { r: '4', strokeWidth: '2', stroke: '#16A34A' }
            }}
            bezier
            style={styles.chart}
          />
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
  logoAccent: { color: '#4F46E5' },
  badge: { fontSize: 10, fontWeight: 'bold', color: '#16A34A', backgroundColor: '#ECFDF5', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20, overflow: 'hidden', marginBottom: 10 },
  title: { fontSize: 28, fontWeight: '900', color: '#111827' },
  highlight: { color: '#22C55E' },
  card: { backgroundColor: '#ffffff', borderRadius: 24, padding: 24, shadowColor: '#000', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.05, shadowRadius: 20, elevation: 5, marginBottom: 20 },
  scoreTitle: { fontSize: 12, fontWeight: '800', color: '#9CA3AF', letterSpacing: 1, marginBottom: 8 },
  score: { fontSize: 64, fontWeight: '900', color: '#111827', marginBottom: 10 },
  scoreScale: { fontSize: 24, fontWeight: '700', color: '#D1D5DB' },
  statusBadge: { alignSelf: 'flex-start', backgroundColor: '#FEF2F2', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12, marginBottom: 20 },
  statusText: { color: '#DC2626', fontWeight: 'bold', fontSize: 14, textTransform: 'uppercase' },
  factorsList: { borderTopWidth: 1, borderTopColor: '#F3F4F6', paddingTop: 16 },
  factorsTitle: { fontSize: 11, fontWeight: 'bold', color: '#6B7280', marginBottom: 8 },
  factorItem: { fontSize: 14, color: '#374151', marginBottom: 4 },
  chartContainer: { backgroundColor: '#ffffff', borderRadius: 24, padding: 20, paddingBottom: 0, shadowColor: '#000', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.05, shadowRadius: 20, elevation: 5, marginBottom: 40 },
  chartTitle: { fontSize: 12, fontWeight: '800', color: '#9CA3AF', letterSpacing: 1, marginBottom: 10 },
  chart: { marginVertical: 8, borderRadius: 16, alignSelf: 'center' },
  infoText: { textAlign: 'center', color: '#6B7280', marginVertical: 20 }
});
