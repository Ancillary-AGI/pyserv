/**
 * Auth - Authentication System for Pyserv Client Framework
 * Provides comprehensive authentication management with token handling,
 * session management, and seamless integration with Pyserv backend
 */

export class Auth {
  constructor(config = {}) {
    this.config = {
      apiClient: config.apiClient,
      storageKey: config.storageKey || 'pyserv_auth',
      refreshThreshold: config.refreshThreshold || 300000, // 5 minutes
      autoRefresh: config.autoRefresh !== false,
      redirectOnAuth: config.redirectOnAuth !== false,
      loginRoute: config.loginRoute || '/login',
      dashboardRoute: config.dashboardRoute || '/dashboard',
      ...config
    };

    this.state = {
      isAuthenticated: false,
      user: null,
      token: null,
      refreshToken: null,
      expiresAt: null,
      loading: false,
      error: null
    };

    this.refreshTimer = null;
    this.listeners = new Set();

    // Initialize from storage
    this._loadFromStorage();

    // Start auto-refresh if enabled
    if (this.config.autoRefresh && this.state.isAuthenticated) {
      this._startRefreshTimer();
    }

    // Bind methods
    this.login = this.login.bind(this);
    this.logout = this.logout.bind(this);
    this.register = this.register.bind(this);
    this.refresh = this.refresh.bind(this);
    this.updateProfile = this.updateProfile.bind(this);
    this.changePassword = this.changePassword.bind(this);
    this.resetPassword = this.resetPassword.bind(this);
  }

  // Authentication state
  get isAuthenticated() {
    return this.state.isAuthenticated && this._isTokenValid();
  }

  get user() {
    return this.state.user;
  }

  get token() {
    return this.state.token;
  }

  get refreshToken() {
    return this.state.refreshToken;
  }

  get loading() {
    return this.state.loading;
  }

  get error() {
    return this.state.error;
  }

  // Authentication methods
  async login(credentials) {
    this._setLoading(true);
    this._setError(null);

    try {
      const response = await this.config.apiClient.login(credentials);

      if (response.data) {
        await this._handleLoginSuccess(response.data);
        return { success: true, user: this.state.user };
      } else {
        throw new Error('Invalid response format');
      }
    } catch (error) {
      const errorMessage = this._extractErrorMessage(error);
      this._setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      this._setLoading(false);
    }
  }

  async logout() {
    this._setLoading(true);

    try {
      // Call logout endpoint if available
      if (this.config.apiClient) {
        await this.config.apiClient.logout();
      }
    } catch (error) {
      console.warn('Logout API call failed:', error);
    } finally {
      await this._handleLogout();
      this._setLoading(false);
    }
  }

  async register(userData) {
    this._setLoading(true);
    this._setError(null);

    try {
      const response = await this.config.apiClient.register(userData);

      if (response.data) {
        // Auto-login after successful registration
        if (response.data.token) {
          await this._handleLoginSuccess(response.data);
        }

        return { success: true, user: this.state.user };
      } else {
        throw new Error('Invalid response format');
      }
    } catch (error) {
      const errorMessage = this._extractErrorMessage(error);
      this._setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      this._setLoading(false);
    }
  }

  async refresh() {
    if (!this.state.refreshToken) {
      throw new Error('No refresh token available');
    }

    this._setLoading(true);

    try {
      const response = await this.config.apiClient.refreshToken(this.state.refreshToken);

      if (response.data) {
        await this._handleLoginSuccess(response.data);
        return { success: true };
      } else {
        throw new Error('Invalid refresh response');
      }
    } catch (error) {
      await this._handleLogout();
      throw error;
    } finally {
      this._setLoading(false);
    }
  }

  async updateProfile(profileData) {
    if (!this.isAuthenticated) {
      throw new Error('Not authenticated');
    }

    this._setLoading(true);

    try {
      const response = await this.config.apiClient.updateProfile(profileData);

      if (response.data) {
        this._updateUser(response.data);
        return { success: true, user: this.state.user };
      } else {
        throw new Error('Invalid response format');
      }
    } catch (error) {
      const errorMessage = this._extractErrorMessage(error);
      this._setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      this._setLoading(false);
    }
  }

  async changePassword(passwordData) {
    if (!this.isAuthenticated) {
      throw new Error('Not authenticated');
    }

    this._setLoading(true);

    try {
      const response = await this.config.apiClient.changePassword(passwordData);

      return { success: true };
    } catch (error) {
      const errorMessage = this._extractErrorMessage(error);
      this._setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      this._setLoading(false);
    }
  }

  async resetPassword(email) {
    this._setLoading(true);

    try {
      const response = await this.config.apiClient.resetPassword(email);

      return { success: true };
    } catch (error) {
      const errorMessage = this._extractErrorMessage(error);
      this._setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      this._setLoading(false);
    }
  }

  // Internal methods
  async _handleLoginSuccess(authData) {
    // Extract authentication data
    const token = authData.token || authData.access;
    const refreshToken = authData.refreshToken || authData.refresh;
    const user = authData.user || authData;
    const expiresAt = this._calculateExpirationTime(authData.expiresIn);

    // Update state
    this.state = {
      ...this.state,
      isAuthenticated: true,
      token,
      refreshToken,
      user,
      expiresAt,
      error: null
    };

    // Save to storage
    this._saveToStorage();

    // Start refresh timer
    if (this.config.autoRefresh) {
      this._startRefreshTimer();
    }

    // Set API client token
    if (this.config.apiClient) {
      this.config.apiClient.setAuthToken(token);
    }

    // Emit login event
    this.emit('auth:login', { user, token });

    // Redirect if enabled
    if (this.config.redirectOnAuth) {
      this._redirectToDashboard();
    }
  }

  async _handleLogout() {
    // Clear state
    this.state = {
      isAuthenticated: false,
      user: null,
      token: null,
      refreshToken: null,
      expiresAt: null,
      loading: false,
      error: null
    };

    // Clear storage
    this._clearStorage();

    // Clear API client token
    if (this.config.apiClient) {
      this.config.apiClient.removeAuthToken();
    }

    // Stop refresh timer
    this._stopRefreshTimer();

    // Emit logout event
    this.emit('auth:logout', {});

    // Redirect to login if enabled
    if (this.config.redirectOnAuth) {
      this._redirectToLogin();
    }
  }

  _updateUser(userData) {
    this.state.user = { ...this.state.user, ...userData };
    this._saveToStorage();
    this.emit('auth:user-updated', { user: this.state.user });
  }

  _startRefreshTimer() {
    this._stopRefreshTimer();

    if (!this.state.expiresAt) return;

    const refreshTime = Math.max(
      this.state.expiresAt - Date.now() - this.config.refreshThreshold,
      60000 // Minimum 1 minute
    );

    if (refreshTime > 0) {
      this.refreshTimer = setTimeout(async () => {
        try {
          await this.refresh();
        } catch (error) {
          console.warn('Auto-refresh failed:', error);
          // Could emit an event or redirect to login
        }
      }, refreshTime);
    }
  }

  _stopRefreshTimer() {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  _calculateExpirationTime(expiresIn) {
    if (typeof expiresIn === 'number') {
      return Date.now() + (expiresIn * 1000);
    }
    return null;
  }

  _isTokenValid() {
    if (!this.state.token) return false;
    if (!this.state.expiresAt) return true; // Assume valid if no expiration
    return Date.now() < this.state.expiresAt;
  }

  _extractErrorMessage(error) {
    if (typeof error === 'string') {
      return error;
    }

    if (error.response?.data?.message) {
      return error.response.data.message;
    }

    if (error.response?.data?.error) {
      return error.response.data.error;
    }

    if (error.message) {
      return error.message;
    }

    return 'An unknown error occurred';
  }

  // Storage methods
  _saveToStorage() {
    try {
      const authData = {
        token: this.state.token,
        refreshToken: this.state.refreshToken,
        user: this.state.user,
        expiresAt: this.state.expiresAt
      };
      localStorage.setItem(this.config.storageKey, JSON.stringify(authData));
    } catch (error) {
      console.error('Failed to save auth data:', error);
    }
  }

  _loadFromStorage() {
    try {
      const stored = localStorage.getItem(this.config.storageKey);
      if (stored) {
        const authData = JSON.parse(stored);

        this.state = {
          ...this.state,
          token: authData.token,
          refreshToken: authData.refreshToken,
          user: authData.user,
          expiresAt: authData.expiresAt,
          isAuthenticated: this._isTokenValid()
        };

        // Set API client token
        if (this.config.apiClient && this.state.token) {
          this.config.apiClient.setAuthToken(this.state.token);
        }
      }
    } catch (error) {
      console.error('Failed to load auth data:', error);
      this._clearStorage();
    }
  }

  _clearStorage() {
    try {
      localStorage.removeItem(this.config.storageKey);
    } catch (error) {
      console.error('Failed to clear auth data:', error);
    }
  }

  // State management
  _setLoading(loading) {
    this.state.loading = loading;
    this.emit('auth:loading-changed', { loading });
  }

  _setError(error) {
    this.state.error = error;
    this.emit('auth:error-changed', { error });
  }

  // Navigation helpers
  _redirectToLogin() {
    if (typeof window !== 'undefined' && window.location) {
      window.location.href = this.config.loginRoute;
    }
  }

  _redirectToDashboard() {
    if (typeof window !== 'undefined' && window.location) {
      window.location.href = this.config.dashboardRoute;
    }
  }

  // Event system
  emit(event, data) {
    if (this.config.debug) {
      console.log(`[Auth] Event: ${event}`, data);
    }

    this.listeners.forEach(listener => {
      try {
        listener(event, data);
      } catch (error) {
        console.error('Auth listener error:', error);
      }
    });
  }

  on(event, handler) {
    this.listeners.add(handler);

    return () => {
      this.listeners.delete(handler);
    };
  }

  off(handler) {
    this.listeners.delete(handler);
  }

  // Utility methods
  hasRole(role) {
    if (!this.state.user) return false;
    const userRoles = this.state.user.roles || [];
    return userRoles.includes(role);
  }

  hasPermission(permission) {
    if (!this.state.user) return false;
    const userPermissions = this.state.user.permissions || [];
    return userPermissions.includes(permission);
  }

  getUserProperty(path, defaultValue = null) {
    if (!this.state.user) return defaultValue;
    return this._getNestedValue(this.state.user, path) || defaultValue;
  }

  _getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  }

  // Token management
  getTokenInfo() {
    if (!this.state.token) return null;

    try {
      const payload = this.state.token.split('.')[1];
      const decoded = JSON.parse(atob(payload));
      return {
        exp: decoded.exp,
        iat: decoded.iat,
        user_id: decoded.user_id,
        username: decoded.username,
        roles: decoded.roles || [],
        permissions: decoded.permissions || []
      };
    } catch (error) {
      console.error('Failed to decode token:', error);
      return null;
    }
  }

  isTokenExpired() {
    const tokenInfo = this.getTokenInfo();
    if (!tokenInfo || !tokenInfo.exp) return true;
    return Date.now() >= (tokenInfo.exp * 1000);
  }

  // Session management
  extendSession() {
    if (this.isAuthenticated && this.config.autoRefresh) {
      this._startRefreshTimer();
    }
  }

  invalidateSession() {
    this._handleLogout();
  }

  // Debug utilities
  getDebugInfo() {
    return {
      isAuthenticated: this.isAuthenticated,
      hasToken: !!this.state.token,
      hasRefreshToken: !!this.state.refreshToken,
      tokenExpiresAt: this.state.expiresAt,
      userId: this.state.user?.id,
      userRoles: this.state.user?.roles || [],
      listenerCount: this.listeners.size,
      refreshTimerActive: !!this.refreshTimer
    };
  }

  // Cleanup
  destroy() {
    this._stopRefreshTimer();
    this.listeners.clear();

    // Clear sensitive data
    this.state = {
      isAuthenticated: false,
      user: null,
      token: null,
      refreshToken: null,
      expiresAt: null,
      loading: false,
      error: null
    };

    this._clearStorage();
  }
}

// Authentication guards
export const createAuthGuard = (auth) => {
  return (to, from, next) => {
    if (to.meta?.requiresAuth && !auth.isAuthenticated) {
      return auth.config.loginRoute;
    }
    return true;
  };
};

export const createRoleGuard = (auth, requiredRole) => {
  return (to, from, next) => {
    if (to.meta?.requiresRole && !auth.hasRole(requiredRole)) {
      return '/unauthorized';
    }
    return true;
  };
};

export const createPermissionGuard = (auth, requiredPermission) => {
  return (to, from, next) => {
    if (to.meta?.requiresPermission && !auth.hasPermission(requiredPermission)) {
      return '/forbidden';
    }
    return true;
  };
};

// Authentication utilities
export function useAuth() {
  return window.__PYSERV_AUTH__;
}

export function useUser() {
  const auth = useAuth();
  return auth ? auth.user : null;
}

export function useIsAuthenticated() {
  const auth = useAuth();
  return auth ? auth.isAuthenticated : false;
}

// Global auth instance
let globalAuth = null;

export function setGlobalAuth(auth) {
  globalAuth = auth;
  window.__PYSERV_AUTH__ = auth;
}

export function getGlobalAuth() {
  return globalAuth;
}

// Authentication decorators
export function requireAuth(target, propertyKey, descriptor) {
  const method = descriptor.value;

  descriptor.value = function(...args) {
    const auth = getGlobalAuth();
    if (!auth || !auth.isAuthenticated) {
      throw new Error('Authentication required');
    }
    return method.apply(this, args);
  };

  return descriptor;
}

export function requireRole(role) {
  return function(target, propertyKey, descriptor) {
    const method = descriptor.value;

    descriptor.value = function(...args) {
      const auth = getGlobalAuth();
      if (!auth || !auth.hasRole(role)) {
        throw new Error(`Role '${role}' required`);
      }
      return method.apply(this, args);
    };

    return descriptor;
  };
}

export function requirePermission(permission) {
  return function(target, propertyKey, descriptor) {
    const method = descriptor.value;

    descriptor.value = function(...args) {
      const auth = getGlobalAuth();
      if (!auth || !auth.hasPermission(permission)) {
        throw new Error(`Permission '${permission}' required`);
      }
      return method.apply(this, args);
    };

    return descriptor;
  };
}
