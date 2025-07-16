import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { COLORS, SIZES, FONTS, SHADOWS } from '../../constants/theme';
import { authService } from '../../services/authService';

const PremiumGateScreen = ({ navigation }) => {
  const [loading, setLoading] = useState(false);

  const handleUpgrade = () => {
    Alert.alert(
      'Upgrade to Premium',
      'You will be redirected to our premium subscription page.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Continue', onPress: () => {
          // Here you would typically open a web browser or in-app purchase
          console.log('Redirecting to premium upgrade...');
        }}
      ]
    );
  };

  const handleRetryPremiumCheck = async () => {
    setLoading(true);
    try {
      const premiumStatus = await authService.verifyPremium();
      if (premiumStatus.isPremium) {
        navigation.replace('Dashboard');
      } else {
        Alert.alert('Premium Required', 'Your account does not have an active premium subscription.');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to verify premium status. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await authService.logout();
      navigation.replace('Login');
    } catch (error) {
      navigation.replace('Login');
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContainer}>
      <View style={styles.header}>
        <View style={styles.logoContainer}>
          <View style={styles.logo}>
            <Text style={styles.logoText}>WB</Text>
          </View>
          <Text style={styles.appName}>WaddleBot</Text>
          <Text style={styles.premiumBadge}>PREMIUM</Text>
        </View>
      </View>

      <View style={styles.content}>
        <View style={styles.lockIcon}>
          <Text style={styles.lockIconText}>🔒</Text>
        </View>
        
        <Text style={styles.title}>Premium Access Required</Text>
        <Text style={styles.subtitle}>
          This mobile app is exclusively available to WaddleBot Premium subscribers.
        </Text>

        <View style={styles.featuresContainer}>
          <Text style={styles.featuresTitle}>Premium Features Include:</Text>
          
          <View style={styles.featuresList}>
            <View style={styles.featureItem}>
              <Text style={styles.featureIcon}>📱</Text>
              <Text style={styles.featureText}>Mobile Community Management</Text>
            </View>
            
            <View style={styles.featureItem}>
              <Text style={styles.featureIcon}>👥</Text>
              <Text style={styles.featureText}>Member Role Management</Text>
            </View>
            
            <View style={styles.featureItem}>
              <Text style={styles.featureIcon}>🔧</Text>
              <Text style={styles.featureText}>Module Installation & Control</Text>
            </View>
            
            <View style={styles.featureItem}>
              <Text style={styles.featureIcon}>📊</Text>
              <Text style={styles.featureText}>Advanced Analytics Dashboard</Text>
            </View>
            
            <View style={styles.featureItem}>
              <Text style={styles.featureIcon}>⚡</Text>
              <Text style={styles.featureText}>Real-time Notifications</Text>
            </View>
            
            <View style={styles.featureItem}>
              <Text style={styles.featureIcon}>🎯</Text>
              <Text style={styles.featureText}>Priority Support</Text>
            </View>
          </View>
        </View>

        <View style={styles.actions}>
          <TouchableOpacity
            style={styles.upgradeButton}
            onPress={handleUpgrade}
          >
            <LinearGradient
              colors={[COLORS.SECONDARY, COLORS.ACCENT_DARK_YELLOW]}
              style={styles.upgradeButtonGradient}
            >
              <Text style={styles.upgradeButtonText}>Upgrade to Premium</Text>
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.retryButton, loading && styles.retryButtonDisabled]}
            onPress={handleRetryPremiumCheck}
            disabled={loading}
          >
            <Text style={styles.retryButtonText}>
              {loading ? 'Checking...' : 'I Already Have Premium'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.logoutButton}
            onPress={handleLogout}
          >
            <Text style={styles.logoutButtonText}>Sign Out</Text>
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.BACKGROUND,
  },
  scrollContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: SIZES.SCREEN_MARGIN,
  },
  header: {
    alignItems: 'center',
    marginBottom: SIZES.SPACING_XXLARGE,
  },
  logoContainer: {
    alignItems: 'center',
  },
  logo: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.PRIMARY,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_SMALL,
    ...SHADOWS.MEDIUM,
  },
  logoText: {
    fontSize: SIZES.FONT_HERO,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_LIGHT,
  },
  appName: {
    fontSize: SIZES.FONT_HEADER,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  premiumBadge: {
    fontSize: SIZES.FONT_SMALL,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.PRIMARY,
    backgroundColor: COLORS.SECONDARY,
    paddingHorizontal: SIZES.SPACING_SMALL,
    paddingVertical: SIZES.SPACING_TINY,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  content: {
    alignItems: 'center',
  },
  lockIcon: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: COLORS.ACCENT_LIGHT_YELLOW,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_LARGE,
  },
  lockIconText: {
    fontSize: 30,
  },
  title: {
    fontSize: SIZES.FONT_HEADER,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    textAlign: 'center',
    marginBottom: SIZES.SPACING_SMALL,
  },
  subtitle: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    textAlign: 'center',
    marginBottom: SIZES.SPACING_XLARGE,
    lineHeight: 22,
  },
  featuresContainer: {
    width: '100%',
    marginBottom: SIZES.SPACING_XLARGE,
  },
  featuresTitle: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    textAlign: 'center',
    marginBottom: SIZES.SPACING_LARGE,
  },
  featuresList: {
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_LARGE,
    ...SHADOWS.LIGHT,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  featureIcon: {
    fontSize: 20,
    marginRight: SIZES.SPACING_MEDIUM,
    width: 30,
    textAlign: 'center',
  },
  featureText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    flex: 1,
  },
  actions: {
    width: '100%',
    alignItems: 'center',
  },
  upgradeButton: {
    width: '100%',
    height: SIZES.BUTTON_HEIGHT,
    borderRadius: SIZES.BUTTON_RADIUS,
    marginBottom: SIZES.SPACING_MEDIUM,
    ...SHADOWS.LIGHT,
  },
  upgradeButtonGradient: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  upgradeButtonText: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  retryButton: {
    width: '100%',
    height: SIZES.BUTTON_HEIGHT,
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderWidth: 1,
    borderColor: COLORS.BORDER,
    borderRadius: SIZES.BUTTON_RADIUS,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  retryButtonDisabled: {
    opacity: 0.7,
  },
  retryButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
  },
  logoutButton: {
    paddingHorizontal: SIZES.SPACING_LARGE,
    paddingVertical: SIZES.SPACING_SMALL,
  },
  logoutButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
  },
});

export default PremiumGateScreen;