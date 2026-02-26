import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

// Threshold in milliseconds before user data is considered stale
const USER_STALE_THRESHOLD_MS = 30 * 1000; // 30 seconds

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const lastFetchedAt = useRef(null);

  // Check for existing session on mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await api.get('/api/v1/auth/me');
      if (response.data.success && response.data.user) {
        setUser(response.data.user);
        lastFetchedAt.current = Date.now();
      } else {
        localStorage.removeItem('token');
      }
    } catch (err) {
      console.error('Failed to fetch user:', err);
      // Only clear token on auth errors (401/403). Transient errors like
      // 429 rate limiting or network failures should not log the user out.
      const status = err.response?.status;
      if (status === 401 || status === 403) {
        localStorage.removeItem('token');
      }
    } finally {
      setLoading(false);
    }
  };

  /**
   * Re-fetch current user data from the server.
   * Skips if data was fetched within the staleness threshold
   * unless force=true is passed.
   */
  const refreshUser = useCallback(async (force = false) => {
    const token = localStorage.getItem('token');
    if (!token) return;

    const now = Date.now();
    if (!force && lastFetchedAt.current && (now - lastFetchedAt.current) < USER_STALE_THRESHOLD_MS) {
      return; // Data is still fresh
    }

    await fetchCurrentUser();
  }, []);

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
      localStorage.setItem('token', token);
      await fetchCurrentUser();
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/api/v1/auth/logout');
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      localStorage.removeItem('token');
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
    refreshUser,
    isAuthenticated: !!user,
    // Role checks - use roles array directly
    hasRole: (role) => user?.roles?.includes(role),
    isAdmin: user?.roles?.includes('admin'),
    isSuperAdmin: user?.roles?.includes('super_admin'),
    isPlatformAdmin: user?.roles?.includes('platform-admin'),
    isVendor: user?.roles?.includes('vendor'),
    isAnalyticsConsumer: user?.isAnalyticsConsumer || false,
    // Community-level admin check (for any community, or a specific one)
    isCommunityAdmin: (communityId) => {
      const adminRoles = ['community-owner', 'community-admin', 'moderator'];
      if (communityId) {
        return user?.communities?.some(c => c.id === Number(communityId) && adminRoles.includes(c.role));
      }
      return user?.communities?.some(c => adminRoles.includes(c.role));
    },
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
