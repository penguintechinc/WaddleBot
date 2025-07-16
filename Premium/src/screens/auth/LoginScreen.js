import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Image,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { COLORS, SIZES, FONTS, SHADOWS } from '../../constants/theme';
import { authService } from '../../services/authService';

const LoginScreen = ({ navigation }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    setLoading(true);
    try {
      const response = await authService.login(email, password);
      
      if (response.success) {
        // Check premium status
        const premiumStatus = await authService.verifyPremium();
        if (premiumStatus.isPremium) {
          navigation.replace('Dashboard');
        } else {
          navigation.replace('PremiumGate');
        }
      } else {
        Alert.alert('Login Failed', response.message || 'Invalid credentials');
      }
    } catch (error) {
      Alert.alert('Error', 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <View style={styles.header}>
          <View style={styles.logoContainer}>
            <View style={styles.logo}>
              <Text style={styles.logoText}>WB</Text>
            </View>
            <Text style={styles.appName}>WaddleBot</Text>
            <Text style={styles.premiumBadge}>PREMIUM</Text>
          </View>
          <Text style={styles.subtitle}>Community Manager Portal</Text>
        </View>

        <View style={styles.form}>
          <View style={styles.inputContainer}>
            <Text style={styles.inputLabel}>Email</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter your email"
              placeholderTextColor={COLORS.TEXT_MUTED}
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.inputLabel}>Password</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter your password"
              placeholderTextColor={COLORS.TEXT_MUTED}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          <TouchableOpacity
            style={[styles.loginButton, loading && styles.loginButtonDisabled]}
            onPress={handleLogin}
            disabled={loading}
          >
            <LinearGradient
              colors={[COLORS.SECONDARY, COLORS.ACCENT_DARK_YELLOW]}
              style={styles.loginButtonGradient}
            >
              <Text style={styles.loginButtonText}>
                {loading ? 'Signing In...' : 'Sign In'}
              </Text>
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity style={styles.forgotPassword}>
            <Text style={styles.forgotPasswordText}>Forgot Password?</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Premium features require an active subscription
          </Text>
          <TouchableOpacity style={styles.upgradeButton}>
            <Text style={styles.upgradeButtonText}>Upgrade to Premium</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
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
    marginBottom: SIZES.SPACING_MEDIUM,
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
  subtitle: {
    fontSize: SIZES.FONT_LARGE,
    color: COLORS.TEXT_SECONDARY,
    textAlign: 'center',
  },
  form: {
    marginBottom: SIZES.SPACING_XXLARGE,
  },
  inputContainer: {
    marginBottom: SIZES.SPACING_LARGE,
  },
  inputLabel: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_SMALL,
  },
  input: {
    height: SIZES.INPUT_HEIGHT,
    backgroundColor: COLORS.INPUT_BACKGROUND,
    borderWidth: 1,
    borderColor: COLORS.INPUT_BORDER,
    borderRadius: SIZES.BUTTON_RADIUS,
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
  },
  loginButton: {
    height: SIZES.BUTTON_HEIGHT,
    borderRadius: SIZES.BUTTON_RADIUS,
    marginBottom: SIZES.SPACING_MEDIUM,
    ...SHADOWS.LIGHT,
  },
  loginButtonDisabled: {
    opacity: 0.7,
  },
  loginButtonGradient: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  loginButtonText: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  forgotPassword: {
    alignItems: 'center',
  },
  forgotPasswordText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
  },
  footer: {
    alignItems: 'center',
  },
  footerText: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_MUTED,
    textAlign: 'center',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  upgradeButton: {
    paddingHorizontal: SIZES.SPACING_LARGE,
    paddingVertical: SIZES.SPACING_SMALL,
    borderWidth: 1,
    borderColor: COLORS.SECONDARY,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  upgradeButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.SECONDARY,
  },
});

export default LoginScreen;