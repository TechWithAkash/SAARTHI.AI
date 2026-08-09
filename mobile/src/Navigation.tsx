import React from 'react';
import { View, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';

import DashboardScreen from './screens/DashboardScreen';
import HealthDataScreen from './screens/HealthDataScreen';
import AssistantScreen from './screens/AssistantScreen';
import SyncScreen from './screens/SyncScreen';
import { colors } from './theme';

const Tab = createBottomTabNavigator();

// A fixed-size chip around just the icon, not react-navigation's
// tabBarActiveBackgroundColor (which fills the tab item's *entire* allocated
// width — a quarter of the bar — which is what read as "stretched"). This
// stays the same compact size regardless of the bar's width, and uses a
// light tint instead of a solid fill for the active state.
function TabIcon({ name, focused, color }: { name: keyof typeof Ionicons.glyphMap; focused: boolean; color: string }) {
  return (
    <View style={[styles.iconSlot, focused && styles.iconSlotActive]}>
      <Ionicons name={name} size={19} color={color} />
    </View>
  );
}

export default function Navigation() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        id={undefined}
        screenOptions={{
          headerShown: false,
          tabBarShowLabel: true,
          tabBarActiveTintColor: colors.primary,
          tabBarInactiveTintColor: colors.textTertiary,
          tabBarLabelStyle: { fontSize: 10.5, fontWeight: '800', marginTop: 3 },
          tabBarItemStyle: { paddingTop: 6 },
          // Floating pill matching the app's own theme — white surface,
          // hairline border, a neutral shadow — with real gaps from both
          // screen edges so it reads as centered, not edge-to-edge.
          tabBarStyle: {
            position: 'absolute',
            left: 6,
            right: 6,
            bottom: 16,
            height: 62,
            borderRadius: 26,
            backgroundColor: colors.surface,
            borderWidth: 1,
            borderColor: colors.border,
            shadowColor: '#0F172A',
            shadowOffset: { width: 0, height: 6 },
            shadowOpacity: 0.1,
            shadowRadius: 12,
            elevation: 6,
          },
        }}
      >
        <Tab.Screen
          name="Dashboard"
          component={DashboardScreen}
          options={{
            title: 'Home',
            tabBarIcon: ({ color, focused }) => <TabIcon name={focused ? 'home' : 'home-outline'} focused={focused} color={color} />,
          }}
        />
        <Tab.Screen
          name="HealthData"
          component={HealthDataScreen}
          options={{
            title: 'Vitals',
            tabBarIcon: ({ color, focused }) => <TabIcon name={focused ? 'analytics' : 'analytics-outline'} focused={focused} color={color} />,
          }}
        />
        <Tab.Screen
          name="Assistant"
          component={AssistantScreen}
          options={{
            title: 'Assistant',
            tabBarIcon: ({ color, focused }) => (
              <TabIcon name={focused ? 'chatbubble-ellipses' : 'chatbubble-ellipses-outline'} focused={focused} color={color} />
            ),
          }}
        />
        <Tab.Screen
          name="Sync"
          component={SyncScreen}
          options={{
            title: 'Sync',
            tabBarIcon: ({ color, focused }) => <TabIcon name={focused ? 'watch' : 'watch-outline'} focused={focused} color={color} />,
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  iconSlot: { width: 38, height: 30, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  iconSlotActive: { backgroundColor: colors.primarySoft },
});
