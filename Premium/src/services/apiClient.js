import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_CONFIG, STORAGE_KEYS } from '../constants/config';

class ApiClient {
  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.PORTAL_API_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  setupInterceptors() {
    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      async (config) => {
        const token = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle token refresh
    this.client.interceptors.response.use(
      (response) => {
        return response;
      },
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const refreshToken = await AsyncStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
            if (refreshToken) {
              const response = await axios.post(
                `${API_CONFIG.PORTAL_API_URL}/auth/refresh`,
                { refreshToken }
              );

              const { token } = response.data;
              await AsyncStorage.setItem(STORAGE_KEYS.USER_TOKEN, token);

              originalRequest.headers.Authorization = `Bearer ${token}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            console.error('Token refresh failed:', refreshError);
            await this.clearAuthData();
            // Redirect to login screen would happen here
            // This could be handled by a navigation service
          }
        }

        return Promise.reject(error);
      }
    );
  }

  async clearAuthData() {
    await AsyncStorage.multiRemove([
      STORAGE_KEYS.USER_TOKEN,
      STORAGE_KEYS.REFRESH_TOKEN,
      STORAGE_KEYS.USER_DATA,
      STORAGE_KEYS.PREMIUM_STATUS,
    ]);
  }

  // HTTP Methods
  async get(url, config = {}) {
    return this.client.get(url, config);
  }

  async post(url, data = {}, config = {}) {
    return this.client.post(url, data, config);
  }

  async put(url, data = {}, config = {}) {
    return this.client.put(url, data, config);
  }

  async patch(url, data = {}, config = {}) {
    return this.client.patch(url, data, config);
  }

  async delete(url, config = {}) {
    return this.client.delete(url, config);
  }

  // Specialized methods for different API endpoints
  createRouterClient() {
    return axios.create({
      baseURL: API_CONFIG.ROUTER_API_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
  }

  createMarketplaceClient() {
    return axios.create({
      baseURL: API_CONFIG.MARKETPLACE_API_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
  }

  // Upload methods for file handling
  async uploadFile(url, file, config = {}) {
    const formData = new FormData();
    formData.append('file', {
      uri: file.uri,
      type: file.type,
      name: file.name,
    });

    return this.client.post(url, formData, {
      ...config,
      headers: {
        ...config.headers,
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  async uploadAvatar(file) {
    return this.uploadFile('/user/avatar', file);
  }

  async uploadCommunityImage(communityId, file) {
    return this.uploadFile(`/communities/${communityId}/image`, file);
  }

  // Retry mechanism for failed requests
  async retryRequest(requestFn, maxRetries = API_CONFIG.RETRY_ATTEMPTS) {
    let lastError;

    for (let i = 0; i < maxRetries; i++) {
      try {
        return await requestFn();
      } catch (error) {
        lastError = error;
        
        if (i < maxRetries - 1) {
          const delay = API_CONFIG.RETRY_DELAY * Math.pow(2, i); // Exponential backoff
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError;
  }

  // Health check
  async healthCheck() {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }

  // Network status checking
  async checkNetworkConnectivity() {
    try {
      await this.client.get('/health', { timeout: 5000 });
      return true;
    } catch (error) {
      return false;
    }
  }

  // Request cancellation
  createCancelToken() {
    return axios.CancelToken.source();
  }

  isRequestCancelled(error) {
    return axios.isCancel(error);
  }

  // Error handling utilities
  getErrorMessage(error) {
    if (error.response) {
      return error.response.data?.message || 'Server error occurred';
    } else if (error.request) {
      return 'Network error occurred';
    } else {
      return error.message || 'Unknown error occurred';
    }
  }

  isNetworkError(error) {
    return !error.response && error.request;
  }

  isServerError(error) {
    return error.response && error.response.status >= 500;
  }

  isClientError(error) {
    return error.response && error.response.status >= 400 && error.response.status < 500;
  }

  // Request logging (for debugging)
  enableRequestLogging() {
    this.client.interceptors.request.use(
      (config) => {
        console.log('API Request:', {
          method: config.method.toUpperCase(),
          url: config.url,
          data: config.data,
        });
        return config;
      }
    );

    this.client.interceptors.response.use(
      (response) => {
        console.log('API Response:', {
          status: response.status,
          url: response.config.url,
          data: response.data,
        });
        return response;
      },
      (error) => {
        console.log('API Error:', {
          status: error.response?.status,
          url: error.config?.url,
          message: this.getErrorMessage(error),
        });
        return Promise.reject(error);
      }
    );
  }
}

export const apiClient = new ApiClient();