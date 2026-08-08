import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';

import DashboardScreen from './screens/DashboardScreen';
import SyncScreen from './screens/SyncScreen';

const Tab = createBottomTabNavigator();

export default function Navigation() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        id={undefined}
        screenOptions={{
          tabBarActiveTintColor: '#2563EB',
          tabBarInactiveTintColor: '#9CA3AF',
          headerShown: false,
          tabBarShowLabel: true,
          tabBarLabelStyle: { fontSize: 11, fontWeight: '700', marginTop: -2 },
          tabBarStyle: {
            backgroundColor: '#ffffff',
            borderTopColor: '#F1F5F9',
            borderTopWidth: 1,
            elevation: 0,
            shadowOpacity: 0,
            height: 62,
            paddingTop: 8,
            paddingBottom: 8,
          },
        }}
      >
        <Tab.Screen
          name="Dashboard"
          component={DashboardScreen}
          options={{
            title: 'Insights',
            tabBarIcon: ({ color, size, focused }) => (
              <Ionicons name={focused ? 'pulse' : 'pulse-outline'} size={size} color={color} />
            ),
          }}
        />
        <Tab.Screen
          name="Sync"
          component={SyncScreen}
          options={{
            title: 'Garmin Sync',
            tabBarIcon: ({ color, size, focused }) => (
              <Ionicons name={focused ? 'watch' : 'watch-outline'} size={size} color={color} />
            ),
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
