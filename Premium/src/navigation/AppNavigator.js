import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createDrawerNavigator } from '@react-navigation/drawer';
import Icon from 'react-native-vector-icons/MaterialIcons';

import { COLORS, SIZES } from '../constants/theme';
import { SCREEN_NAMES } from '../constants/config';

// Auth Screens
import LoginScreen from '../screens/auth/LoginScreen';
import PremiumGateScreen from '../screens/auth/PremiumGateScreen';

// Main Screens
import DashboardScreen from '../screens/dashboard/DashboardScreen';
import MembersScreen from '../screens/members/MembersScreen';
import MemberDetailScreen from '../screens/members/MemberDetailScreen';
import ModulesScreen from '../screens/modules/ModulesScreen';
import ModuleDetailScreen from '../screens/modules/ModuleDetailScreen';
import SettingsScreen from '../screens/settings/SettingsScreen';
import ProfileScreen from '../screens/profile/ProfileScreen';
import AnalyticsScreen from '../screens/analytics/AnalyticsScreen';
import CommunitiesScreen from '../screens/communities/CommunitiesScreen';
import CommunityDetailScreen from '../screens/communities/CommunityDetailScreen';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();
const Drawer = createDrawerNavigator();

// Auth Stack Navigator
const AuthStack = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        cardStyle: { backgroundColor: COLORS.BACKGROUND },
      }}
    >
      <Stack.Screen 
        name={SCREEN_NAMES.LOGIN} 
        component={LoginScreen} 
      />
      <Stack.Screen 
        name={SCREEN_NAMES.PREMIUM_GATE} 
        component={PremiumGateScreen} 
      />
    </Stack.Navigator>
  );
};

// Dashboard Stack Navigator
const DashboardStack = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: COLORS.CARD_BACKGROUND,
          elevation: 0,
          shadowOpacity: 0,
          borderBottomWidth: 1,
          borderBottomColor: COLORS.BORDER,
        },
        headerTitleStyle: {
          fontSize: SIZES.FONT_LARGE,
          fontWeight: '600',
          color: COLORS.TEXT_PRIMARY,
        },
        headerTintColor: COLORS.TEXT_PRIMARY,
        cardStyle: { backgroundColor: COLORS.BACKGROUND },
      }}
    >
      <Stack.Screen 
        name={SCREEN_NAMES.DASHBOARD} 
        component={DashboardScreen}
        options={{ title: 'Dashboard' }}
      />
      <Stack.Screen 
        name={SCREEN_NAMES.COMMUNITY_DETAIL} 
        component={CommunityDetailScreen}
        options={{ title: 'Community Details' }}
      />
    </Stack.Navigator>
  );
};

// Communities Stack Navigator
const CommunitiesStack = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: COLORS.CARD_BACKGROUND,
          elevation: 0,
          shadowOpacity: 0,
          borderBottomWidth: 1,
          borderBottomColor: COLORS.BORDER,
        },
        headerTitleStyle: {
          fontSize: SIZES.FONT_LARGE,
          fontWeight: '600',
          color: COLORS.TEXT_PRIMARY,
        },
        headerTintColor: COLORS.TEXT_PRIMARY,
        cardStyle: { backgroundColor: COLORS.BACKGROUND },
      }}
    >
      <Stack.Screen 
        name={SCREEN_NAMES.COMMUNITIES} 
        component={CommunitiesScreen}
        options={{ title: 'Communities' }}
      />
      <Stack.Screen 
        name={SCREEN_NAMES.COMMUNITY_DETAIL} 
        component={CommunityDetailScreen}
        options={{ title: 'Community Details' }}
      />
    </Stack.Navigator>
  );
};

// Members Stack Navigator
const MembersStack = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: COLORS.CARD_BACKGROUND,
          elevation: 0,
          shadowOpacity: 0,
          borderBottomWidth: 1,
          borderBottomColor: COLORS.BORDER,
        },
        headerTitleStyle: {
          fontSize: SIZES.FONT_LARGE,
          fontWeight: '600',
          color: COLORS.TEXT_PRIMARY,
        },
        headerTintColor: COLORS.TEXT_PRIMARY,
        cardStyle: { backgroundColor: COLORS.BACKGROUND },
      }}
    >
      <Stack.Screen 
        name={SCREEN_NAMES.MEMBERS} 
        component={MembersScreen}
        options={{ title: 'Members' }}
      />
      <Stack.Screen 
        name={SCREEN_NAMES.MEMBER_DETAIL} 
        component={MemberDetailScreen}
        options={{ title: 'Member Details' }}
      />
    </Stack.Navigator>
  );
};

// Modules Stack Navigator
const ModulesStack = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: COLORS.CARD_BACKGROUND,
          elevation: 0,
          shadowOpacity: 0,
          borderBottomWidth: 1,
          borderBottomColor: COLORS.BORDER,
        },
        headerTitleStyle: {
          fontSize: SIZES.FONT_LARGE,
          fontWeight: '600',
          color: COLORS.TEXT_PRIMARY,
        },
        headerTintColor: COLORS.TEXT_PRIMARY,
        cardStyle: { backgroundColor: COLORS.BACKGROUND },
      }}
    >
      <Stack.Screen 
        name={SCREEN_NAMES.MODULES} 
        component={ModulesScreen}
        options={{ title: 'Modules' }}
      />
      <Stack.Screen 
        name={SCREEN_NAMES.MODULE_DETAIL} 
        component={ModuleDetailScreen}
        options={{ title: 'Module Details' }}
      />
    </Stack.Navigator>
  );
};

// Analytics Stack Navigator
const AnalyticsStack = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: COLORS.CARD_BACKGROUND,
          elevation: 0,
          shadowOpacity: 0,
          borderBottomWidth: 1,
          borderBottomColor: COLORS.BORDER,
        },
        headerTitleStyle: {
          fontSize: SIZES.FONT_LARGE,
          fontWeight: '600',
          color: COLORS.TEXT_PRIMARY,
        },
        headerTintColor: COLORS.TEXT_PRIMARY,
        cardStyle: { backgroundColor: COLORS.BACKGROUND },
      }}
    >
      <Stack.Screen 
        name={SCREEN_NAMES.ANALYTICS} 
        component={AnalyticsScreen}
        options={{ title: 'Analytics' }}
      />
    </Stack.Navigator>
  );
};

// Settings Stack Navigator
const SettingsStack = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: COLORS.CARD_BACKGROUND,
          elevation: 0,
          shadowOpacity: 0,
          borderBottomWidth: 1,
          borderBottomColor: COLORS.BORDER,
        },
        headerTitleStyle: {
          fontSize: SIZES.FONT_LARGE,
          fontWeight: '600',
          color: COLORS.TEXT_PRIMARY,
        },
        headerTintColor: COLORS.TEXT_PRIMARY,
        cardStyle: { backgroundColor: COLORS.BACKGROUND },
      }}
    >
      <Stack.Screen 
        name={SCREEN_NAMES.SETTINGS} 
        component={SettingsScreen}
        options={{ title: 'Settings' }}
      />
      <Stack.Screen 
        name={SCREEN_NAMES.PROFILE} 
        component={ProfileScreen}
        options={{ title: 'Profile' }}
      />
    </Stack.Navigator>
  );
};

// Bottom Tab Navigator
const MainTabs = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          switch (route.name) {
            case 'DashboardTab':
              iconName = 'dashboard';
              break;
            case 'CommunitiesTab':
              iconName = 'groups';
              break;
            case 'MembersTab':
              iconName = 'people';
              break;
            case 'ModulesTab':
              iconName = 'extension';
              break;
            case 'AnalyticsTab':
              iconName = 'analytics';
              break;
            default:
              iconName = 'dashboard';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: COLORS.SECONDARY,
        tabBarInactiveTintColor: COLORS.TEXT_SECONDARY,
        tabBarStyle: {
          backgroundColor: COLORS.CARD_BACKGROUND,
          borderTopColor: COLORS.BORDER,
          borderTopWidth: 1,
          paddingBottom: 5,
          paddingTop: 5,
          height: 60,
        },
        tabBarLabelStyle: {
          fontSize: SIZES.FONT_SMALL,
          fontWeight: '500',
        },
      })}
    >
      <Tab.Screen 
        name="DashboardTab" 
        component={DashboardStack}
        options={{ tabBarLabel: 'Dashboard' }}
      />
      <Tab.Screen 
        name="CommunitiesTab" 
        component={CommunitiesStack}
        options={{ tabBarLabel: 'Communities' }}
      />
      <Tab.Screen 
        name="MembersTab" 
        component={MembersStack}
        options={{ tabBarLabel: 'Members' }}
      />
      <Tab.Screen 
        name="ModulesTab" 
        component={ModulesStack}
        options={{ tabBarLabel: 'Modules' }}
      />
      <Tab.Screen 
        name="AnalyticsTab" 
        component={AnalyticsStack}
        options={{ tabBarLabel: 'Analytics' }}
      />
    </Tab.Navigator>
  );
};

// Drawer Navigator
const DrawerNavigator = () => {
  return (
    <Drawer.Navigator
      screenOptions={{
        headerShown: false,
        drawerStyle: {
          backgroundColor: COLORS.CARD_BACKGROUND,
          width: 280,
        },
        drawerContentStyle: {
          backgroundColor: COLORS.CARD_BACKGROUND,
        },
        drawerActiveTintColor: COLORS.SECONDARY,
        drawerInactiveTintColor: COLORS.TEXT_SECONDARY,
        drawerLabelStyle: {
          fontSize: SIZES.FONT_MEDIUM,
          fontWeight: '500',
        },
      }}
    >
      <Drawer.Screen 
        name="MainTabs" 
        component={MainTabs}
        options={{
          drawerLabel: 'Dashboard',
          drawerIcon: ({ color, size }) => (
            <Icon name="dashboard" size={size} color={color} />
          ),
        }}
      />
      <Drawer.Screen 
        name="SettingsDrawer" 
        component={SettingsStack}
        options={{
          drawerLabel: 'Settings',
          drawerIcon: ({ color, size }) => (
            <Icon name="settings" size={size} color={color} />
          ),
        }}
      />
    </Drawer.Navigator>
  );
};

// Root Navigator
const RootNavigator = ({ isAuthenticated, isPremium }) => {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!isAuthenticated ? (
        <Stack.Screen name="Auth" component={AuthStack} />
      ) : !isPremium ? (
        <Stack.Screen name="PremiumGate" component={PremiumGateScreen} />
      ) : (
        <Stack.Screen name="Main" component={DrawerNavigator} />
      )}
    </Stack.Navigator>
  );
};

// App Navigator Component
const AppNavigator = ({ isAuthenticated = false, isPremium = false }) => {
  return (
    <NavigationContainer>
      <RootNavigator 
        isAuthenticated={isAuthenticated} 
        isPremium={isPremium} 
      />
    </NavigationContainer>
  );
};

export default AppNavigator;