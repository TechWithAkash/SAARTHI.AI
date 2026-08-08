import React from 'react';
import { StatusBar } from 'expo-status-bar';
import Navigation from './src/Navigation';
import { SafeAreaProvider } from 'react-native-safe-area-context';

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <Navigation />
    </SafeAreaProvider>
  );
}
