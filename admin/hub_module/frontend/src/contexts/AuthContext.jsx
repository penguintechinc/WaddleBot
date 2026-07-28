import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import {
  isDesktopMode,
  desktopLogin,
  desktopLogout,
  desktopGetToken,
  desktopGetCurrentUser,
} from '../services/desktopAdapter';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check for existing session on mount
  useEffect(() => {
    const checkSession = async () => {
      try {
        if (isDesktopMode()) {
          // Desktop: check token in keychain
          const token = await desktopGetToken();
          if (token) {
            await fetchCurrentUser();
          } else {
            setLoading(false);
          }
        } else {
          // Browser: check token in localStorage
          const token = localStorage.getItem('token');
          if (token) {
            fetchCurrentUser();
          } else {
            setLoading(false);
          }
        }
      } catch (err) {
        console.error('Session check failed:', err);
        setLoading(false);
      }
    };
    checkSession();
  }, []);

  const fetchCurrentUser = async () => {
    try {
      if (isDesktopMode()) {
        // Desktop: use Tauri to fetch current user
        const user = await desktopGetCurrentUser();
        if (user) {
          setUser(user);
        } else {
          // TODO: Clear token from keychain if /auth/me fails (M3)
        }
      } else {
        // Browser: use axios
        const response = await api.get('/api/v1/auth/me');
        if (response.data.success && response.data.user) {
          setUser(response.data.user);
        } else {
          localStorage.removeItem('token');
        }
      }
    } catch (err) {
      console.error('Failed to fetch user:', err);
      if (!isDesktopMode()) {
        localStorage.removeItem('token');
      }
    } finally {
      setLoading(false);
    }
  };

  const loginWithOAuth = useCallback(async (platform) => {
    try {
      const response = await api.get(`/api/v1/auth/oauth/${platform}`);
      if (response.data.authorizeUrl) {
        window.location.href = response.data.authorizeUrl;
      }
    } catch (err) {
      setError(err.response?.data?.error || 'OAuth login failed');
      throw err;
    }
  }, []);

  const login = useCallback(async (email, password) => {
    try {
      setError(null);

      if (isDesktopMode()) {
        // Desktop: use Tauri login command
        const response = await desktopLogin(email, password);
        if (response.success) {
          // Token is stored in keychain; fetch full user data
          const user = await desktopGetCurrentUser();
          if (user) {
            setUser(user);
          }
          return { success: true, user: response.user };
        }
        throw new Error('Login failed');
      } else {
        // Browser: use axios
        const response = await api.post('/api/v1/auth/login', { email, password });
        if (response.data.success) {
          localStorage.setItem('token', response.data.token);
          setUser(response.data.user);
          return response.data;
        }
        // Handle requires verification response (403 with requiresVerification)
        if (response.data.requiresVerification) {
          const error = new Error(response.data.message || 'Email verification required');
          error.requiresVerification = true;
          throw error;
        }
      }
    } catch (err) {
      // Check for verification required in error response
      if (err.response?.data?.requiresVerification) {
        const error = new Error(err.response.data.message || 'Email verification required');
        error.requiresVerification = true;
        throw error;
      }
      const message = err.response?.data?.error?.message || err.response?.data?.error || err.response?.data?.message || err.message || 'Login failed';
      setError(message);
      throw new Error(message);
    }
  }, []);

  const register = useCallback(async (email, password, username) => {
    try {
      setError(null);
      const response = await api.post('/api/v1/auth/register', { email, password, username });
      if (response.data.success) {
        // Handle email verification required case
        if (response.data.requiresVerification) {
          return { requiresVerification: true, message: response.data.message };
        }
        localStorage.setItem('token', response.data.token);
        setUser(response.data.user);
        return response.data;
      }
    } catch (err) {
      const message = err.response?.data?.error?.message || err.response?.data?.error || err.response?.data?.message || 'Registration failed';
      setError(message);
      throw new Error(message);
    }
  }, []);

  // Legacy admin login (backwards compatibility)
  const loginWithAdmin = useCallback(async (username, password) => {
    try {
      setError(null);
      const response = await api.post('/api/v1/auth/admin', { username, password });
      if (response.data.success) {
        localStorage.setItem('token', response.data.token);
        setUser(response.data.user);
        return response.data;
      }
    } catch (err) {
      const message = err.response?.data?.error?.message || err.response?.data?.error || 'Login failed';
      setError(message);
      throw new Error(message);
    }
  }, []);

  const loginWithTempPassword = useCallback(async (identifier, password) => {
    try {
      setError(null);
      const response = await api.post('/api/v1/auth/temp-password', { identifier, password });
      if (response.data.success) {
        localStorage.setItem('token', response.data.token);
        await fetchCurrentUser();
        return response.data;
      }
    } catch (err) {
      const message = err.response?.data?.error?.message || err.response?.data?.error || 'Login failed';
      setError(message);
      throw new Error(message);
    }
  }, []);

  const handleOAuthCallback = useCallback(async (token) => {
    if (token) {
      if (isDesktopMode()) {
        // TODO: Desktop OAuth callback → store token in keychain + fetch user (M2)
        console.warn('[AuthContext] OAuth callback in desktop mode not yet implemented');
        // For now, redirect to login with error
        window.location.href = '/login?error=oauth_not_implemented';
      } else {
        localStorage.setItem('token', token);
        await fetchCurrentUser();
      }
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      if (isDesktopMode()) {
        // Desktop: use Tauri logout command (clears keychain)
        await desktopLogout();
      } else {
        // Browser: use axios
        await api.post('/api/v1/auth/logout');
      }
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      if (!isDesktopMode()) {
        localStorage.removeItem('token');
      }
      setUser(null);
    }
  }, []);

  const refreshToken = useCallback(async () => {
    try {
      const response = await api.post('/api/v1/auth/refresh');
      if (response.data.success) {
        localStorage.setItem('token', response.data.token);
      }
    } catch (err) {
      console.error('Token refresh failed:', err);
      logout();
    }
  }, [logout]);

  const value = {
    user,
    loading,
    error,
    login,
    register,
    loginWithOAuth,
    loginWithAdmin,
    loginWithTempPassword,
    handleOAuthCallback,
    logout,
    refreshToken,
    isAuthenticated: !!user,
    // Role checks - use roles array directly
    hasRole: (role) => user?.roles?.includes(role),
    isAdmin: user?.roles?.includes('admin'),
    isSuperAdmin: user?.roles?.includes('super_admin'),
    isPlatformAdmin: user?.roles?.includes('platform-admin'),
    isVendor: user?.roles?.includes('vendor'),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
