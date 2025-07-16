import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_CONFIG, STORAGE_KEYS, ENDPOINTS } from '../constants/config';
import { apiClient } from './apiClient';

class AuthService {
  async login(email, password) {
    try {
      const response = await apiClient.post(ENDPOINTS.LOGIN, {
        email,
        password,
      });

      if (response.data.success) {
        const { token, refreshToken, user } = response.data;
        
        await AsyncStorage.setItem(STORAGE_KEYS.USER_TOKEN, token);
        await AsyncStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
        await AsyncStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(user));
        
        return { success: true, user };
      } else {
        return { success: false, message: response.data.message };
      }
    } catch (error) {
      console.error('Login error:', error);
      return { 
        success: false, 
        message: error.response?.data?.message || 'Login failed' 
      };
    }
  }

  async logout() {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      if (token) {
        await apiClient.post(ENDPOINTS.LOGOUT, {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      await AsyncStorage.multiRemove([
        STORAGE_KEYS.USER_TOKEN,
        STORAGE_KEYS.REFRESH_TOKEN,
        STORAGE_KEYS.USER_DATA,
        STORAGE_KEYS.PREMIUM_STATUS,
      ]);
    }
  }

  async refreshToken() {
    try {
      const refreshToken = await AsyncStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await apiClient.post(ENDPOINTS.REFRESH, {
        refreshToken,
      });

      if (response.data.success) {
        const { token, refreshToken: newRefreshToken } = response.data;
        
        await AsyncStorage.setItem(STORAGE_KEYS.USER_TOKEN, token);
        await AsyncStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, newRefreshToken);
        
        return { success: true, token };
      } else {
        throw new Error(response.data.message || 'Token refresh failed');
      }
    } catch (error) {
      console.error('Token refresh error:', error);
      await this.logout();
      throw error;
    }
  }

  async verifyPremium() {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      if (!token) {
        return { isPremium: false, message: 'Not authenticated' };
      }

      const response = await apiClient.get(ENDPOINTS.VERIFY_PREMIUM, {
        headers: { Authorization: `Bearer ${token}` }
      });

      const premiumStatus = {
        isPremium: response.data.isPremium,
        subscriptionType: response.data.subscriptionType,
        expiresAt: response.data.expiresAt,
        features: response.data.features,
      };

      await AsyncStorage.setItem(STORAGE_KEYS.PREMIUM_STATUS, JSON.stringify(premiumStatus));
      
      return premiumStatus;
    } catch (error) {
      console.error('Premium verification error:', error);
      return { 
        isPremium: false, 
        message: error.response?.data?.message || 'Premium verification failed' 
      };
    }
  }

  async getStoredToken() {
    try {
      return await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
    } catch (error) {
      console.error('Error getting stored token:', error);
      return null;
    }
  }

  async getStoredUser() {
    try {
      const userData = await AsyncStorage.getItem(STORAGE_KEYS.USER_DATA);
      return userData ? JSON.parse(userData) : null;
    } catch (error) {
      console.error('Error getting stored user:', error);
      return null;
    }
  }

  async getStoredPremiumStatus() {
    try {
      const premiumStatus = await AsyncStorage.getItem(STORAGE_KEYS.PREMIUM_STATUS);
      return premiumStatus ? JSON.parse(premiumStatus) : null;
    } catch (error) {
      console.error('Error getting stored premium status:', error);
      return null;
    }
  }

  async isAuthenticated() {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      return !!token;
    } catch (error) {
      console.error('Error checking authentication:', error);
      return false;
    }
  }

  async isPremiumUser() {
    try {
      const premiumStatus = await this.getStoredPremiumStatus();
      if (!premiumStatus) {
        return false;
      }

      if (premiumStatus.expiresAt) {
        const expirationDate = new Date(premiumStatus.expiresAt);
        const now = new Date();
        return now < expirationDate;
      }

      return premiumStatus.isPremium;
    } catch (error) {
      console.error('Error checking premium status:', error);
      return false;
    }
  }

  async getUserProfile() {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await apiClient.get(ENDPOINTS.USER_PROFILE, {
        headers: { Authorization: `Bearer ${token}` }
      });

      const user = response.data.user;
      await AsyncStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(user));
      
      return user;
    } catch (error) {
      console.error('Error getting user profile:', error);
      throw error;
    }
  }

  async updateUserProfile(profileData) {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await apiClient.put(ENDPOINTS.USER_PROFILE, profileData, {
        headers: { Authorization: `Bearer ${token}` }
      });

      const user = response.data.user;
      await AsyncStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(user));
      
      return user;
    } catch (error) {
      console.error('Error updating user profile:', error);
      throw error;
    }
  }

  async changePassword(currentPassword, newPassword) {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await apiClient.post(ENDPOINTS.CHANGE_PASSWORD, {
        currentPassword,
        newPassword,
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      return response.data;
    } catch (error) {
      console.error('Error changing password:', error);
      throw error;
    }
  }

  async deleteAccount() {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await apiClient.delete(ENDPOINTS.DELETE_ACCOUNT, {
        headers: { Authorization: `Bearer ${token}` }
      });

      await this.logout();
      
      return response.data;
    } catch (error) {
      console.error('Error deleting account:', error);
      throw error;
    }
  }

  async requestPasswordReset(email) {
    try {
      const response = await apiClient.post(ENDPOINTS.REQUEST_PASSWORD_RESET, {
        email,
      });

      return response.data;
    } catch (error) {
      console.error('Error requesting password reset:', error);
      throw error;
    }
  }

  async resetPassword(token, newPassword) {
    try {
      const response = await apiClient.post(ENDPOINTS.RESET_PASSWORD, {
        token,
        newPassword,
      });

      return response.data;
    } catch (error) {
      console.error('Error resetting password:', error);
      throw error;
    }
  }

  async enableTwoFactor() {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await apiClient.post(ENDPOINTS.ENABLE_TWO_FACTOR, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });

      return response.data;
    } catch (error) {
      console.error('Error enabling two-factor:', error);
      throw error;
    }
  }

  async disableTwoFactor(code) {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await apiClient.post(ENDPOINTS.DISABLE_TWO_FACTOR, {
        code,
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      return response.data;
    } catch (error) {
      console.error('Error disabling two-factor:', error);
      throw error;
    }
  }

  async verifyTwoFactor(code) {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await apiClient.post(ENDPOINTS.VERIFY_TWO_FACTOR, {
        code,
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      return response.data;
    } catch (error) {
      console.error('Error verifying two-factor:', error);
      throw error;
    }
  }
}

export const authService = new AuthService();