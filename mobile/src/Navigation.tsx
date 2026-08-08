import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

import DashboardScreen from './screens/DashboardScreen';
import SyncScreen from './screens/SyncScreen';

const Tab = createBottomTabNavigator();

export default function Navigation() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={{
          tabBarActiveTintColor: '#16A34A',
          tabBarInactiveTintColor: '#A1A1AA',
          headerShown: false,
          tabBarStyle: {
            backgroundColor: '#ffffff',
            borderTopColor: '#f4f4f5',
            elevation: 0,
            shadowOpacity: 0,
          },
        }}
      >
        <Tab.Screen 
          name="Dashboard" 
          component={DashboardScreen} 
          options={{ title: 'SAARTHI.AI Insights' }} 
        />
        <Tab.Screen 
          name="Sync" 
          component={SyncScreen} 
          options={{ title: 'Apple Health Sync' }} 
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
