/**
 * WaddleBot Premium Mobile App
 * Community Manager Portal
 */

import React, { useState, useEffect } from 'react';
import {
  StatusBar,
  StyleSheet,
  View,
} from 'react-native';
import Toast from 'react-native-toast-message';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import AppNavigator from './src/navigation/AppNavigator';
import { authService } from './src/services/authService';
import { COLORS } from './src/constants/theme';

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isPremium, setIsPremium] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const authenticated = await authService.isAuthenticated();
      setIsAuthenticated(authenticated);

      if (authenticated) {
        const premium = await authService.isPremiumUser();
        setIsPremium(premium);

        // Verify premium status with server
        if (premium) {
          const premiumStatus = await authService.verifyPremium();
          setIsPremium(premiumStatus.isPremium);
        }
      }
    } catch (error) {
      console.error('Error checking auth status:', error);
      // On error, assume not authenticated
      setIsAuthenticated(false);
      setIsPremium(false);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <StatusBar 
          barStyle="dark-content" 
          backgroundColor={COLORS.BACKGROUND} 
        />
        {/* Add a loading spinner here if needed */}
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={styles.container}>
      <SafeAreaProvider>
        <StatusBar 
          barStyle="dark-content" 
          backgroundColor={COLORS.BACKGROUND} 
        />
        <AppNavigator 
          isAuthenticated={isAuthenticated}
          isPremium={isPremium}
        />
        <Toast />
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.BACKGROUND,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.BACKGROUND,
  },
});

export default App;