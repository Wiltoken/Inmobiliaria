import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api, userApi } from './api';

const AuthContext = createContext(null);

const STORAGE_KEY = 'inmobiliaria_auth';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load user from storage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const { user: storedUser } = JSON.parse(stored);
        setUser(storedUser);
      } catch (e) {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
    setIsLoading(false);
  }, []);

  // Fetch full user profile
  const fetchProfile = useCallback(async () => {
    try {
      const response = await userApi.me();
      const updatedUser = { ...user, ...response.data };
      setUser(updatedUser);
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ user: updatedUser }));
      return updatedUser;
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      throw error;
    }
  }, [user]);

  const login = useCallback((token, refreshToken, userData) => {
    const userWithToken = { ...userData, token, refreshToken };
    setUser(userWithToken);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      user: userWithToken,
      accessToken: token,
      refreshToken: refreshToken,
    }));
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
    delete api.defaults.headers.common.Authorization;
  }, []);

  const updateUser = useCallback((updates) => {
    const updatedUser = { ...user, ...updates };
    setUser(updatedUser);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      user: updatedUser,
      accessToken: user.token,
      refreshToken: user.refreshToken,
    }));
  }, [user]);

  const value = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout,
    updateUser,
    fetchProfile,
    hasRole: (role) => user?.roles?.some(r => r.name === role),
    isBuyer: () => user?.roles?.some(r => r.name === 'buyer'),
    isSeller: () => user?.roles?.some(r => r.name === 'seller'),
    isAgent: () => user?.roles?.some(r => r.name === 'agent'),
    isAdmin: () => user?.roles?.some(r => r.name === 'admin' || r.name === 'super_admin'),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Helper functions for token management (called by api.js)
export function getAccessToken() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      return parsed.accessToken || parsed.user?.token;
    } catch {
      return null;
    }
  }
  return null;
}

export function getRefreshToken() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      return parsed.refreshToken || parsed.user?.refreshToken;
    } catch {
      return null;
    }
  }
  return null;
}

export function setAuth(accessToken, refreshToken) {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      const updated = {
        ...parsed,
        accessToken,
        refreshToken,
        user: { ...parsed.user, token: accessToken, refreshToken },
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch {
      // Ignore
    }
  }
  api.defaults.headers.common.Authorization = `Bearer ${accessToken}`;
}

export function clearAuth() {
  localStorage.removeItem(STORAGE_KEY);
  delete api.defaults.headers.common.Authorization;
}
