import React, { useState } from 'react';
import { View, Text, TouchableOpacity, Switch, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { initHealthKit, fetchHealthDataSnapshot } from '../services/healthKitCore';
import { deriveStressLevel, deriveDietScore } from '../services/derivationEngine';
import { submitHealthData } from '../services/api';

const DEFAULT_USER = 'user_demo_001';

export default function SyncScreen() {
  const [syncing, setSyncing] = useState(false);
  const [bgSyncMode, setBgSyncMode] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  const addLog = (msg: string) => {
    setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev]);
  };

  const handleSync = async () => {
    setSyncing(true);
    addLog('Requesting HealthKit permissions...');
    
    try {
      await initHealthKit();
      addLog('Extracting 24hr vitals...');
      
      const rawData = await fetchHealthDataSnapshot();
      addLog(`HealthKit: HR ${rawData.heartRate}, Steps ${rawData.steps}, Sleep ${rawData.sleep}h`);

      // Log weight and height used for BMI
      if (rawData.weightKg && rawData.heightM) {
        addLog(`Body: Weight ${rawData.weightKg}kg, Height ${rawData.heightM}m → BMI ${rawData.bmi}`);
      } else {
        addLog(`BMI: ${rawData.bmi} (from HealthKit stored value)`);
      }
      
      // Foolproof Derivations
      const derivedStress = deriveStressLevel(rawData.heartRate, rawData.sleep);
      const derivedDiet = deriveDietScore(rawData.bmi, rawData.steps);
      addLog(`Derived: Stress ${derivedStress}/10, Diet ${derivedDiet}/10`);

      const payload = {
        user_id: DEFAULT_USER,
        heart_rate: rawData.heartRate,
        sleep: rawData.sleep,
        steps: rawData.steps,
        bmi: rawData.bmi,
        stress_level: derivedStress,
        diet_score: derivedDiet,
      };

      addLog('Transmitting to SAARTHI.AI (Ngrok)...');
      await submitHealthData(payload);
      addLog('SUCCESS: Saarthi memory updated.');
    } catch (e: any) {
      addLog(`ERROR: ${e.message || 'Verification failed'}`);
      console.error(e);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Data Sync</Text>
        <Text style={styles.subtitle}>Securely bridge Apple Health with Aura</Text>
      </View>

      <View style={styles.card}>
        <View style={styles.row}>
          <View>
            <Text style={styles.cardTitle}>Background Sync</Text>
            <Text style={styles.cardDesc}>Automatically pushes hourly data to backend</Text>
          </View>
          <Switch 
            value={bgSyncMode} 
            onValueChange={(val) => {
              setBgSyncMode(val);
              addLog(val ? 'Background Sync enabled' : 'Background Sync disabled');
            }} 
            trackColor={{ false: "#E5E7EB", true: "#22C55E" }}
          />
        </View>
      </View>

      <TouchableOpacity 
        style={styles.syncButton} 
        onPress={handleSync} 
        disabled={syncing}
      >
        {syncing ? (
          <ActivityIndicator color="#ffffff" />
        ) : (
          <Text style={styles.syncButtonText}>SYNC HEALTHKIT TO AURA</Text>
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
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { fontSize: 16, fontWeight: 'bold', color: '#111827' },
  cardDesc: { fontSize: 12, color: '#6B7280', marginTop: 2, maxWidth: 200 },
  syncButton: { backgroundColor: '#111827', borderRadius: 100, paddingVertical: 18, alignItems: 'center', shadowColor: '#111827', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.2, shadowRadius: 15, elevation: 5, marginBottom: 30 },
  syncButtonText: { color: '#ffffff', fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  terminalContainer: { flex: 1, backgroundColor: '#1F2937', borderRadius: 16, padding: 16, overflow: 'hidden' },
  terminalTitle: { color: '#9CA3AF', fontSize: 10, fontWeight: '900', letterSpacing: 2, marginBottom: 12 },
  terminal: { flex: 1 },
  logText: { color: '#86EFAC', fontFamily: 'Menlo', fontSize: 11, marginBottom: 6 },
  logTextIdle: { color: '#4B5563', fontFamily: 'Menlo', fontSize: 11, fontStyle: 'italic' }
});
